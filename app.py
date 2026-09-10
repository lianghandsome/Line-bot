"""LINE 記帳機器人 — Flask webhook + LINE Messaging API v3。"""
import os

from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET
from util import taiwan_now

app = Flask(__name__)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    app.logger.warning("尚未設定 LINE_CHANNEL_ACCESS_TOKEN / LINE_CHANNEL_SECRET")


def handle_user_message(message, user_id):
    return f"你說的是：{message.strip()}"


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@app.route("/", methods=["GET"])
def home():
    return (
        "<h1>💰 記帳機器人運行中</h1>"
        f"<p>伺服器時間：{taiwan_now().strftime('%Y-%m-%d %H:%M:%S')}（台灣）</p>"
    )


@handler.add(MessageEvent, message=TextMessageContent)
def on_message(event):
    reply_text = handle_user_message(event.message.text, event.source.user_id)
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)],
            )
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
