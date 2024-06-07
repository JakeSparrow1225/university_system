from slack_sdk import WebClient
from firebase_admin import firestore
import firebase_admin
from firebase_admin import credentials
import schedule
import time
from datetime import datetime

SLACK_ACCESS_TOKEN = ''
CHANNEL_ID = ''
FIREBASE_CREDENTIALS_PATH = ''

# Firestoreの初期化
cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

# 最初に全てのメッセージを収集する関数
def collect_all_messages():
    client = WebClient(SLACK_ACCESS_TOKEN)
    response = client.conversations_history(channel=CHANNEL_ID)
    messages = response.get('messages')

    for message in messages:
        channel = message.get('channel')
        user = message.get('user')
        text = message.get('text')
        timestamp = message.get('ts')  # メッセージのタイムスタンプを使用

        print(f"チャンネル: {channel}, ユーザ名: {user}, 発言内容: {text}")

        # Firestoreにメッセージを保存
        doc_ref = db.collection('messages').document()
        doc_ref.set({
            'channel': channel,
            'user': user,
            'text': text,
            'timestamp': timestamp
        })

# 最初に全てのメッセージを収集
collect_all_messages()

# 定期的に最新のメッセージのみを収集する関数
def get_latest_messages():
    global last_timestamp  # 前回の収集結果を更新するためにglobal宣言

    client = WebClient(SLACK_ACCESS_TOKEN)
    response = client.conversations_history(channel=CHANNEL_ID, oldest=last_timestamp)
    messages = response.get('messages')

    new_messages = []  # 新しく収集したメッセージを保持するリスト

    for message in messages:
        timestamp = message.get('ts')
        if timestamp != last_timestamp:
            new_messages.append(message)
            last_timestamp = timestamp

    for message in new_messages:
        channel = message.get('channel')
        user = message.get('user')
        text = message.get('text')
        timestamp = message.get('ts')  # メッセージのタイムスタンプを使用

        print(f"チャンネル: {channel}, ユーザ名: {user}, 発言内容: {text}")

        # Firestoreにメッセージを保存
        doc_ref = db.collection('messages').document()
        doc_ref.set({
            'channel': channel,
            'user': user,
            'text': text,
            'timestamp': timestamp
        })

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
