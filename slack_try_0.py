from slack_sdk import WebClient
from firebase_admin import firestore
import firebase_admin
from firebase_admin import credentials
import schedule
import time
from datetime import datetime
import shutil

SLACK_ACCESS_TOKEN = ''
CHANNEL_ID = ''
FIREBASE_CREDENTIALS_PATH = ''

OUTPUT_FILE_PATH = ''  # File path for the output text file

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
        for message in messages:
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
            file.write(f"チャンネル: {channel}, ユーザ名: {user}, 発言内容: {text}\n")

    # 最後のメッセージのタイムスタンプを更新
    last_timestamp = datetime.now().timestamp()

# 初期値として最新のメッセージを設定
last_timestamp = datetime.now().timestamp()

# 30秒ごとにget_latest_messages関数を実行するスケジュールを設定
schedule.every(30).seconds.do(get_latest_messages)

# 無限ループでスケジュールを実行し続ける
while True:
    schedule.run_pending()
    time.sleep(1)

# テキストファイルの内容を確認する関数
def check_output_file():
    with open(OUTPUT_FILE_PATH, 'r') as file:
        contents = file.read()
        print(contents)

# テキストファイルの内容を確認
check_output_file()

# テキストファイルをダウンロードする関数
def download_output_file(destination_path):
    shutil.copy2(OUTPUT_FILE_PATH, destination_path)

# テキストファイルをダウンロードする
download_output_file('')
