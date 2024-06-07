from slack_sdk import WebClient
from firebase_admin import firestore
import firebase_admin
from firebase_admin import credentials
import schedule
import time
from datetime import datetime
import shutil
import openai

SLACK_ACCESS_TOKEN = ''
CHANNEL_ID = ''
FIREBASE_CREDENTIALS_PATH = 'C'
# File path for the output text file
OUTPUT_FILE_PATH = ''  

# OpenAI APIキー
#chatGPT_version==pip install openai==0.28
openai.api_key = ''



# Firestoreの初期化
cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

# 最初に全てのメッセージを収集する関数
def collect_all_messages():
    client = WebClient(SLACK_ACCESS_TOKEN)
    response = client.conversations_history(channel=CHANNEL_ID)
    messages = response.get('messages')

    with open(OUTPUT_FILE_PATH, 'w') as file:
        for message in reversed(messages):  # メッセージのリストを逆順に処理する
            channel = message.get('channel')
            user = message.get('user')
            text = message.get('text')
            timestamp = message.get('timestamp')

            if timestamp is None:
                timestamp = datetime.now().timestamp()

            # Firestoreにメッセージを保存
            doc_ref = db.collection('messages').document()
            doc_ref.set({
                'channel': channel,
                'user': user,
                'text': text,
                'timestamp': timestamp
            })

            # メッセージをテキストファイルに書き込む
            file.write(f"チャンネル: {channel}, ユーザ名: {user}, 発言内容: {text}\n")
# 最初に全てのメッセージを収集
collect_all_messages()

# 以下省略

# 定期的に最新のメッセージのみを収集してテキストファイルに書き込む関数
def get_latest_messages():
    global last_timestamp  # 前回の収集結果を更新するためにglobal宣言

    client = WebClient(SLACK_ACCESS_TOKEN)
    response = client.conversations_history(channel=CHANNEL_ID, oldest=last_timestamp)
    messages = response.get('messages')

    new_messages = []  # 新しく収集したメッセージを保持するリスト

    with open(OUTPUT_FILE_PATH, 'a') as file:
        for message in messages:
            timestamp = message.get('timestamp')
            if timestamp != last_timestamp:
                new_messages.append(message)
                last_timestamp = timestamp

        for message in new_messages:
            channel = message.get('channel')
            user = message.get('user')
            text = message.get('text')
            timestamp = message.get('timestamp')

            # Firestoreにメッセージを保存
            doc_ref = db.collection('messages').document()
            doc_ref.set({
                'channel': channel,
                'user': user,
                'text': text,
                'timestamp': timestamp
            })

            # メッセージをテキストファイルに書き込む
            file.write(f"発言内容: {text}\n")

    # 最後のメッセージのタイムスタンプを更新
    last_timestamp = datetime.now().timestamp()

# 初期値として最新のメッセージを設定
last_timestamp = datetime.now().timestamp()

# テキストファイルの内容を確認する関数
def check_output_file():
    with open(OUTPUT_FILE_PATH, 'r') as file:
        contents = file.read()
        #print(contents)

# テキストファイルをダウンロードする関数
def download_output_file(destination_path):
    shutil.copy2(OUTPUT_FILE_PATH, destination_path)

# 30秒ごとにget_latest_messages関数を実行するスケジュールを設定
schedule.every(30).seconds.do(get_latest_messages)




#ChatGPT関連
# アドバイスの例とそれに対応するメッセージを辞書として定義
advice_examples = {
    "もっと具体的な事例やデータを挙げると説得力が増します。": "具体例を探してみましょう！",
    "相手の意見に対して敬意を持ちつつ、自分の意見を述べましょう。": "相手の意見を尊重しながら、自分の意見をしっかりと伝えましょう。",
    "論点を絞って、主張を明確にしましょう。": "頑張りましょう！",
    # 他のアドバイスの例とメッセージを追加...
}

# テキストファイルの内容を読み込む
with open(OUTPUT_FILE_PATH, 'r') as file:
    discussion_text = file.read()


# ChatGPT APIにリクエストを送信してアドバイスを取得
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",  # 使用するモデルを指定
    messages=[
        {"role": "system", "content": "You are Kevin, a helpful Python programming assistant."},
        {"role": "user", "content": discussion_text}
    ],
    max_tokens=100,  # APIから受け取るトークンの最大数（任意の値に設定）
    n=1,  # モデルから生成する回答の数（任意の値に設定）
    stop=None,  # APIの応答を停止するトークンを指定（任意の値に設定）
    temperature=0.6,  # 出力の多様性を制御する温度パラメータ（任意の値に設定）
    top_p=0.9,  # 出力の多様性を制御するトップpパラメータ（任意の値に設定）
    frequency_penalty=0.0,  # 頻度ペナルティパラメータ（任意の値に設定）
    presence_penalty=0.0,  # 存在ペナルティパラメータ（任意の値に設定）
    api_key=openai.api_key  # APIキーを指定
)

# APIからの応答から最適なアドバイスを取得
best_advice = response.choices[0].message.content.strip()

# 最適なアドバイスに応じたメッセージを取得
advice_message = advice_examples.get(best_advice, "理解できませんでした。")

# 最適なアドバイスとメッセージを表示
print("提案されたアドバイス:")
print(best_advice)
print("メッセージ:")
print(advice_message)


# 無限ループでスケジュールを実行し続けるから
#これより下にコードを書かない
while True:
    schedule.run_pending()
    time.sleep(1)
    
