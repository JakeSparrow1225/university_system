# https://gri.jp/media/entry/7678 サイト
from slack_sdk import WebClient

#slackのbotを作成して，チャンネルに追加する．
#その際に得られるトークンとチャンネルＩＤを書いてる
SLACK_ACCESS_TOKEN = ''
CHANNEL_ID = ''

#Slack APIにアクセスするためのWebClientオブジェクトを作成
#clientオブジェクトを使用して，SlackAPIのconversations.historyメソッドを呼び出し
client = WebClient(SLACK_ACCESS_TOKEN)

#responseにはAPIの応答が格納される
response = client.conversations_history(channel=CHANNEL_ID)

messages = response.get('messages')

for message in messages:
    channel = message.get('channel')
    user = message.get('user')
    text = message.get('text')
    print(f"チャンネル: {channel}, ユーザ名: {user}, 発言内容: {text}")