"""LINE 記帳機器人 — Flask webhook + LINE Messaging API v3。

使用方式（傳訊息給 bot）：
    支出 150 餐飲 午餐            記一筆支出
    收入 5000 薪水 月薪           記一筆收入
    +50 咖啡                     支出簡寫
    -3000 兼職                   收入簡寫
"""
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

import db
from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET
from util import taiwan_now, today_str

app = Flask(__name__)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

db.init_db()

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    app.logger.warning("尚未設定 LINE_CHANNEL_ACCESS_TOKEN / LINE_CHANNEL_SECRET")

EXPENSE_KEYWORDS = {"支出", "花費", "支", "expense", "exp"}
INCOME_KEYWORDS = {"收入", "賺", "收", "income", "inc"}


def parse_accounting_input(message):
    """解析記帳輸入，成功回傳 dict，否則回傳 None。"""
    message = message.strip()
    if message.startswith("+"):
        message = "支出 " + message[1:]
    elif message.startswith("-"):
        message = "收入 " + message[1:]

    parts = message.split()
    if len(parts) < 3:
        return None

    if parts[0] in EXPENSE_KEYWORDS:
        record_type = "expense"
    elif parts[0] in INCOME_KEYWORDS:
        record_type = "income"
    else:
        return None

    try:
        amount = float(parts[1])
    except ValueError:
        return None
    if amount <= 0:
        return None

    category = parts[2]
    description = " ".join(parts[3:]) if len(parts) > 3 else category

    return {
        "type": record_type,
        "amount": amount,
        "category": category,
        "description": description,
        "date": None,
    }


def format_amount(amount):
    return f"${amount:,.0f}"


def reply_add(user_id, parsed):
    seq = db.add_record(
        user_id,
        parsed["type"],
        parsed["amount"],
        parsed["category"],
        parsed["description"],
        parsed["date"],
    )
    emoji = "💰" if parsed["type"] == "income" else "💸"
    type_text = "收入" if parsed["type"] == "income" else "支出"
    return (
        f"{emoji} {type_text}已記錄！\n"
        f"🆔 編號：{seq}\n"
        f"💵 金額：{format_amount(parsed['amount'])}\n"
        f"🏷️ 分類：{parsed['category']}\n"
        f"📝 說明：{parsed['description']}\n"
        f"📅 日期：{parsed['date'] or today_str()}"
    )


def handle_user_message(message, user_id):
    message = message.strip()

    parsed = parse_accounting_input(message)
    if parsed:
        return reply_add(user_id, parsed)

    return (
        f"🤔 看不懂「{message}」\n\n"
        "試試：\n• 支出 100 餐飲 午餐\n• 收入 5000 薪水"
    )


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
