from slack_sdk import WebClient
import schedule
import time

SLACK_ACCESS_TOKEN = ''
CHANNEL_ID = ''

def get_messages():
    client = WebClient(SLACK_ACCESS_TOKEN)
    response = client.conversations_history(channel=CHANNEL_ID)
    messages = response.get('messages')

    for message in messages:
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