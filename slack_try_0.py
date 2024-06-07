from slack_sdk import WebClient
from firebase_admin import firestore
import firebase_admin
from firebase_admin import credentials
import schedule
import time
from datetime import datetime
from datetime import datetime 
import openai
import requests
import spacy
from settings import SLACK_ACCESS_TOKEN,TOKEN,CHANNEL_ID,FIREBASE_CREDENTIALS_PATH,OUTPUT_FILE_PATH,OPENAI_API_KEY

#chatGPT_version==pip install openai==0.28
openai.api_key = OPENAI_API_KEY

# Firestoreの初期化
cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

# 最初に実行する関数は、実際にはメッセージを収集しない
def setup_initial_timestamp():
    global last_timestamp  # 最後のメッセージのタイムスタンプを保持するグローバル変数
    # 現在時刻のタイムスタンプをセットアップ
    # last_timestamp = datetime.now().timestamp()
# 初期セットアップとして、現在のタイムスタンプを更新
setup_initial_timestamp()

def ensure_file_exists(file_path):
    #指定されたパスにファイルが存在することを保証する。存在しない場合は新たに作成する。
    try:
        # ファイルが存在するか確認し、存在しない場合は作成する
        with open(file_path, 'x') as file:
            pass  # ファイルの作成に成功した場合、ここでは何もしない
    except FileExistsError:
        pass  # ファイルが既に存在する場合、何もしない


def get_latest_messages():
    global last_timestamp  # 前回の収集結果を更新するためにglobal宣言

    client = WebClient(SLACK_ACCESS_TOKEN)
    response = client.conversations_history(channel=CHANNEL_ID, oldest=last_timestamp)
    messages = response.get('messages')

    if not messages:  # 新しいメッセージがない場合は関数を終了
        return

    messages.reverse()  # メッセージリストを逆順にする

    new_last_timestamp = last_timestamp  # 新しい最後のタイムスタンプを一時的に保持

    IGNORE_USER_ID = ''  # 無視したいユーザーのID

    with open(OUTPUT_FILE_PATH, 'a') as file:
        for message in messages:
            user = message.get('user')
            
            # 特定のユーザーのメッセージを無視
            if user == IGNORE_USER_ID:
                continue

            timestamp = float(message.get('ts'))  # Slackからのタイムスタンプは文字列形式で、'ts'キーに格納されている
            text = message.get('text')

            # メッセージをテキストファイルに書き込む
            file.write(f"ユーザ名: {user}, 発言内容: {text}\n")
    
            # ここでFirebaseにも保存
            doc_ref = db.collection('messages').document()
            doc_ref.set({
                'user': user,
                'text': text,
                'timestamp': firestore.SERVER_TIMESTAMP  # Firestoreが提供するサーバータイムスタンプ
            })

            # 新しい最後のタイムスタンプを更新
            if timestamp > new_last_timestamp:
                new_last_timestamp = timestamp

    # 全ての新しいメッセージを処理した後、最後のタイムスタンプを更新
    last_timestamp = new_last_timestamp

# 初期値として最新のメッセージを設定
last_timestamp = datetime.now().timestamp()

# 30秒ごとにget_latest_messages関数を実行するスケジュールを設定
schedule.every(30).seconds.do(get_latest_messages)

policy_options = [
    {
        'policy': '発言量が少ない参加者への発言を喚起する',
        'message': 'プログラムの作成でつまづいている人はいますか？'
    },
    {
        'policy': '一人が発言し続けないように発言者の固定化を防ぐ',
        'message': '各自がそれぞれ作成したコードを一度共有しましょう'
    },
    {
        'policy': 'メンバー間で問題点の共有を行い，議論を活発にする',
        'message': 'この問題を構成しているアルゴリズムを共有しましょう'
    },
    # 他の方針とメッセージを追加
]

def analyze_discussion_and_decide_policy():
    # テキストデータを読み込む
    with open(OUTPUT_FILE_PATH, 'r') as file:
        discussion_text = file.read()

    # ChatGPT APIを使用して議論を分析
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",  # 適切なモデルを指定
        messages=[
            {"role": "system", "content": "以下の議論を分析して、改善するための最適な方針を提案してください。"},
            {"role": "user", "content": discussion_text},
            {"role": "system", "content": "次の方針のうち、どれが最適でしょうか？\n" + "\n".join([option['policy'] for option in policy_options])}
        ],
        temperature=0.7,
        max_tokens=150
    )

    # APIからの応答を解析して、提案された方針を識別
    suggested_policy_text = response.choices[0].message['content'].strip()

    # 提案された方針に最も近いメッセージを選択
    selected_policy_message = None
    max_similarity = -0.5
    for option in policy_options:
        similarity = sum(word in suggested_policy_text for word in option['policy'].split())
        if similarity > max_similarity:
            selected_policy_message = option['message']
            max_similarity = similarity

    if selected_policy_message:
        # 提案された方針に基づくメッセージをターミナルに出力
        print(f"提案された方針に基づくメッセージ: {selected_policy_message}")
    else:
        # 提案された方針がpolicy_optionsの中に見つからない場合、これは起こりえないはずですが、念のための処置です。
        print("提案された方針に一致するオプションが見つかりませんでした。")

# 分析をスケジュールするための関数を追加
schedule.every(30).seconds.do(analyze_discussion_and_decide_policy)  

# スケジューラーを起動するための無限ループ
while True:
    schedule.run_pending()
    time.sleep(1)
