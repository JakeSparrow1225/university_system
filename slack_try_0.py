from slack_sdk import WebClient
import schedule
import time

SLACK_ACCESS_TOKEN = ''
CHANNEL_ID = ''

# 前回の収集結果を保持する変数
last_messages = []

def get_messages():
    global last_messages  # 前回の収集結果を更新するためにglobal宣言

    client = WebClient(SLACK_ACCESS_TOKEN)
    response = client.conversations_history(channel=CHANNEL_ID)
    messages = response.get('messages')

    new_messages = []  # 新しく収集したメッセージを保持するリスト

    for message in messages:
        if message not in last_messages:
            new_messages.append(message)
            last_messages.append(message)

    for message in new_messages:
        channel = message.get('channel')
        user = message.get('user')
        text = message.get('text')
        print(f"チャンネル: {channel}, ユーザ名: {user}, 発言内容: {text}")

# 30秒ごとにget_messages関数を実行するスケジュールを設定
schedule.every(30).seconds.do(get_messages)

# 無限ループでスケジュールを実行し続ける
while True:
    schedule.run_pending()
    time.sleep(1)
