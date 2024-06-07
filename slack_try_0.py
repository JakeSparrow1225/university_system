from slack_sdk import WebClient
from firebase_admin import firestore
import firebase_admin
from firebase_admin import credentials
import schedule
import time
from datetime import datetime
from datetime import datetime 
# import shutil
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

# ChatGPT関連

def call_chatgpt(prompt, policy_options):
    """
    ChatGPT APIを呼び出して、指定されたプロンプトに対する回答を取得する。
    prompt: プロンプトのテキスト
    policy_options: 政策オプションのリスト
    """
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",  # または使用可能な最新のモデルを指定
        messages=[{"role": "system", "content": "テキストファイルを分析した際に、議論の状況を改善する場合、最適だと考えられる方針はpolicy_optionsの中のどれかを選択してください。以下のテキストに基づいてください。"},{"role": "user", "content": prompt}],  # 例としてプロンプトを`messages`に組み込む
        temperature=0.7,
        max_tokens=150,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )
    # チャットモデルの応答からテキストを取得し、整形して返す
    return response['choices'][0]['message']['content'].strip()

def calculate_similarity(text1, text2):
    nlp = spacy.load("ja_core_news_md")  # 日本語モデルをロード
    doc1 = nlp(text1)
    doc2 = nlp(text2)
    similarity = doc1.similarity(doc2)
    return similarity

def dynamic_threshold_similarity(texts, base_text, initial_threshold=0.3, adjustment_factor=0.05):
    """
    動的閾値を用いて、基準テキストとの類似度に基づきテキストを選択する。
    texts: 比較対象のテキストのリスト
    base_text: 基準となるテキスト
    initial_threshold: 初期閾値
    adjustment_factor: 閾値の調整係数
    """
    selected_texts = []
    for text in texts:
        similarity = calculate_similarity(base_text, text)
        if similarity > initial_threshold:
            selected_texts.append(text)
            # 閾値を動的に調整
            initial_threshold += adjustment_factor
    return selected_texts

def suggest_improvements(choices, policy_options):
    top_choices = sorted(choices, key=lambda x: x['score'], reverse=True)[:3]  # スコア上位3つの選択肢を取得

    best_policy_options = []
    for choice in top_choices:
        text = choice['text']
        # ChatGPTプロンプトを作成
        prompt = f"テキストファイルを分析した際に、議論の状況を改善する場合、最適だと考えられる方針はpolicy_optionsの中のどれかを選択してください。以下のテキストに基づいてください:\n\n{text}"
        # ChatGPT APIを呼び出し
        chatgpt_response = call_chatgpt(prompt, policy_options)
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
        # APIの応答から最適な政策オプションを見つける
        for option in policy_options:
            if option['policy'] in chatgpt_response:
                best_policy_options.append(option)
                break

    return best_policy_options

# Slackにメッセージを投稿する関数
def post_to_slack(message, channel_id, token):
    url = "https://slack.com/api/chat.postMessage"
    headers = {"Authorization": "Bearer " + token}
    data = {
        'channel': channel_id,
        'text': message
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code != 200:
        print(f"Slackへの投稿に失敗しました。ステータスコード: {response.status_code}")

def ensure_file_exists(file_path):
    # ファイルが存在しない場合は作成する
    try:
        open(file_path, 'r').close()
    except FileNotFoundError:
        open(file_path, 'w').close()

def analyze_discussion():

    # 出力ファイルが存在することを保証
    ensure_file_exists(OUTPUT_FILE_PATH)
    # テキストファイルの内容を読み込む
    with open(OUTPUT_FILE_PATH, 'r') as file:
        discussion_text = file.read()

    # 方針とメッセージのペアを用意する
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

    choices = [
        {'score': 0.9, 'text': 'テキスト1'},
        {'score': 0.8, 'text': 'テキスト2'},
        {'score': 0.7, 'text': 'テキスト3'},
        # 他の選択肢を追加
    ]

    improvement_suggestion = suggest_improvements(choices, policy_options)

    # Slackへの投稿
    if improvement_suggestion:  # improvement_suggestionが空でないことを確認
        first_suggestion = improvement_suggestion[0]  # 最初の提案を取得
        message = f"最適な方針: {first_suggestion['policy']}\nメッセージ: {first_suggestion['message']}"
        post_to_slack(message, CHANNEL_ID, TOKEN)
    else:
        print("改善提案が見つかりませんでした。")
    
    return discussion_text

# 初回の分析を実行
analyze_discussion()

# 定期的に分析を実行する関数
def run_analysis():
    # OUTPUT_FILE_PATH = "discussion_output.txt"
    # テキストファイルの内容を確認する
    with open(OUTPUT_FILE_PATH, 'r') as file:
        current_text = file.read()

    # analyze_discussion関数からの戻り値を使用して比較
    new_text = analyze_discussion()  # analyze_discussion関数を1回だけ呼び出す
    if new_text != analyze_discussion.previous_text:
        analyze_discussion.previous_text = new_text  # 前回のテキストを更新

# 初期化
analyze_discussion.previous_text = ''

# 分析を30秒ごとに実行するスケジュールを設定
schedule.every(30).seconds.do(run_analysis)

# 無限ループでスケジュールを実行し続ける
while True:
    schedule.run_pending()
    time.sleep(1)
