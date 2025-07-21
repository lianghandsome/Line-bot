from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from db import init_db, add_record, get_weekly_records

app = Flask(__name__)

# 替換為你自己的 LINE Channel Secret 和 Access Token
line_bot_api = LineBotApi("YOUR_CHANNEL_ACCESS_TOKEN")
handler = WebhookHandler("YOUR_CHANNEL_SECRET")

init_db()  # 初始化資料庫

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if text.startswith("記帳 "):
        try:
            _, item, amount = text.split(" ")
            amount = int(amount)
            add_record(user_id, item, amount)
            reply = f"已記帳：{item} {amount}元"
        except:
            reply = "格式錯誤，請使用：記帳 品項 金額（如：記帳 早餐 60）"

    elif text == "查看":
        records = get_weekly_records(user_id)
        if records:
            lines = [f"{r['item']} {r['amount']}元 ({r['timestamp'].strftime('%Y-%m-%d')})" for r in records]
            reply = "\n".join(lines)
        else:
            reply = "這週尚無記帳紀錄。"

    else:
        reply = "請輸入「記帳 品項 金額」或「查看」來使用記帳功能。"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    app.run()
