from slack_sdk import WebClient
from firebase_admin import firestore
import firebase_admin
from firebase_admin import credentials
import schedule
import time
from datetime import datetime
import shutil
import openai
import requests

#Slackのbot「1641」のトークン
SLACK_ACCESS_TOKEN = ''
#Slackのbot「1144」のトークン
TOKEN = ''
#使ってるSlackのチャンネルID
CHANNEL_ID = ''
#Firebaseのパス
FIREBASE_CREDENTIALS_PATH = ''
#テキストファイルの出力先のパス
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
            file.write(f"ユーザ名: {user}, 発言内容: {text}\n")

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

# ChatGPT関連
def calculate_similarity(text1, text2):
    # テキストの類似度を計算する処理を実装する
    similarity = 0.75  # 仮の類似度値を設定

    return similarity

def suggest_improvements(choices, policy_options):
    best_choice = None
    best_score = -1

    for choice in choices:
        score = choice['score']
        text = choice['text']

        # 生成されたテキストのスコアが最も高いものを選択
        if score > best_score:
            best_score = score
            best_choice = text

    # 最適な方針を選択する
    best_policy_option = None
    highest_similarity = -1

    for option in policy_options:
        similarity = calculate_similarity(best_choice, option['policy'])
        if similarity > highest_similarity:
            highest_similarity = similarity
            best_policy_option = option

    return best_policy_option

def analyze_discussion():
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
    url = "https://slack.com/api/chat.postMessage"
    headers = {"Authorization": "Bearer " + TOKEN}
    data = {
        'channel': CHANNEL_ID,
        'text': f"最適な方針: {improvement_suggestion['policy']}\nメッセージ: {improvement_suggestion['message']}"
    }
    r = requests.post(url, headers=headers, data=data)
    #print("return ", r.json())

# 初回の分析を実行
analyze_discussion()

# 定期的に分析を実行する関数
def run_analysis():
    # テキストファイルの内容を確認する
    with open(OUTPUT_FILE_PATH, 'r') as file:
        current_text = file.read()

    # テキストが変更されていれば分析を実行
    if current_text != analyze_discussion.previous_text:
        analyze_discussion()

    # 現在のテキストを保存
    analyze_discussion.previous_text = current_text

# 初期化
analyze_discussion.previous_text = ''

# 分析を30秒ごとに実行するスケジュールを設定
schedule.every(30).seconds.do(run_analysis)

# 無限ループでスケジュールを実行し続ける
while True:
    schedule.run_pending()
    time.sleep(1)
