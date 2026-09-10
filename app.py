"""LINE 記帳機器人 — Flask webhook + LINE Messaging API v3。

使用方式（傳訊息給 bot）：
    支出 150 餐飲 午餐            記一筆支出
    收入 5000 薪水 月薪           記一筆收入
    +50 咖啡                     支出簡寫
    -3000 兼職                   收入簡寫
    帳單 / 本週帳單 / 今天帳單     查看記錄
    統計 / 本月統計              收支統計
    刪除 3                       刪除編號 3 的記錄
"""
import os
import re

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


# --------------------------------------------------------------------------- #
# 解析輸入
# --------------------------------------------------------------------------- #
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


def parse_days(message):
    """從訊息裡判斷要查幾天：今天=0、本週=7、本月=30、'N天'=N、其他=None(全部)。"""
    if "今天" in message or "今日" in message:
        return 0
    if "本週" in message or "這週" in message:
        return 7
    if "本月" in message or "這月" in message:
        return 30
    m = re.search(r"(\d+)\s*天", message)
    if m:
        return int(m.group(1))
    return None


def format_amount(amount):
    return f"${amount:,.0f}"


# --------------------------------------------------------------------------- #
# 產生各種回覆文字
# --------------------------------------------------------------------------- #
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


def reply_list(user_id, message):
    days = parse_days(message)
    if days == 0:
        records = db.get_records_on(user_id, today_str())
        title = f"📊 今日帳單（{today_str()}）"
    elif days is None:
        records = db.get_records(user_id)
        title = "📊 所有記錄"
    else:
        records = db.get_records(user_id, days)
        title = f"📊 近 {days} 天記錄"

    if not records:
        return f"{title}\n目前沒有記錄\n\n💡 試試：支出 100 餐飲 午餐"

    lines = [title, "=" * 22]
    for r in records[:10]:
        sign = "+" if r["type"] == "income" else "-"
        emoji = "💰" if r["type"] == "income" else "💸"
        lines.append(
            f"\n{emoji} [{r['seq']}] {sign}{format_amount(r['amount'])}\n"
            f"🏷️ {r['category']}｜📝 {r['description']}\n"
            f"📅 {r['record_date']}"
        )
    if len(records) > 10:
        lines.append(f"\n… 還有 {len(records) - 10} 筆")
    lines.append("\n\n💡 刪除：刪除 [編號]｜統計：統計")
    return "\n".join(lines)


def reply_summary(user_id, message):
    days = parse_days(message)
    s = db.get_summary(user_id, days)
    if s["record_count"] == 0:
        return "📊 目前沒有記錄可統計\n\n開始記帳吧！"

    period = "今日" if days == 0 else (f"近 {days} 天" if days else "全部")
    lines = [
        f"📊 {period}統計",
        "=" * 20,
        f"💰 總收入：{format_amount(s['total_income'])}",
        f"💸 總支出：{format_amount(s['total_expense'])}",
        f"💵 淨收支：{format_amount(s['balance'])}",
        f"📝 筆數：{s['record_count']}",
    ]
    if s["categories"]:
        lines.append("\n🏷️ 分類統計：")
        for cat, amounts in s["categories"].items():
            if amounts["expense"]:
                lines.append(f"• {cat}：-{format_amount(amounts['expense'])}")
            if amounts["income"]:
                lines.append(f"• {cat}：+{format_amount(amounts['income'])}")
    if s["balance"] < 0:
        lines.append("\n⚠️ 支出大於收入，注意控制開銷！")
    else:
        lines.append("\n✅ 收支狀況良好！")
    return "\n".join(lines)


def reply_delete(user_id, message):
    try:
        seq = int(message[2:].strip())
    except ValueError:
        return "❌ 格式：刪除 [編號]，例如「刪除 3」"
    if db.delete_record(user_id, seq):
        return f"🗑️ 已刪除編號 {seq} 的記錄"
    return f"❌ 找不到編號 {seq} 的記錄"


HELP_TEXT = """💰 記帳機器人使用說明

📝 記帳：
• 支出 [金額] [分類] [說明]
• 收入 [金額] [分類] [說明]
• +[金額] [分類]（支出簡寫）
• -[金額] [分類]（收入簡寫）

📊 查看：帳單 / 今天帳單 / 本週帳單、統計 / 本月統計
🗑️ 刪除：刪除 [編號]

範例：
• 支出 150 餐飲 午餐
• 收入 5000 薪水 月薪
• 本月統計"""


def handle_user_message(message, user_id):
    message = message.strip()

    parsed = parse_accounting_input(message)
    if parsed:
        return reply_add(user_id, parsed)

    if message.startswith("刪除"):
        return reply_delete(user_id, message)
    if any(w in message for w in ("帳單", "記錄", "查看", "清單", "list")):
        return reply_list(user_id, message)
    if any(w in message for w in ("統計", "總結", "分析", "summary")):
        return reply_summary(user_id, message)
    if any(w in message for w in ("幫助", "說明", "help", "功能", "?", "？")):
        return HELP_TEXT

    return (
        f"🤔 看不懂「{message}」\n\n"
        "試試：\n• 支出 100 餐飲 午餐\n• 帳單\n• 統計\n• 幫助"
    )


# --------------------------------------------------------------------------- #
# 路由
# --------------------------------------------------------------------------- #
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
        f"<p>總記錄數：{db.count_all_records()} 筆</p>"
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
