from flask import Flask, request, abort
import os
import json
from datetime import datetime, timedelta
import re
import pytz  # 新增：處理時區
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

# LINE Bot 設定 - 請替換成你的 Token 和 Secret
ACCESS_TOKEN = 'IOjd7xRA4ZwlMNxS6H57U1KixD3RtvE3d4P4iAeVYdSbTMANZmKIooyvK98EEUgds3M/nkOubYsJNTNu5Z8rnEbULqAGyicU/bN5nh4OZVqeDmIE/2K5RNvlXsrCKqtjJ1yBJ6FRmmQW5LNxc6NdggdB04t89/1O/w1cDnyilFU='
CHANNEL_SECRET = '69258da7d559a4ef4709a9ba6dcbb1b1'

configuration = Configuration(access_token=ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 設定台灣時區
TAIWAN_TZ = pytz.timezone('Asia/Taipei')

def get_taiwan_time():
    """取得台灣當前時間"""
    return datetime.now(TAIWAN_TZ)

# 簡單的記憶體儲存（重啟後會清空）
user_notes = {}

def parse_date(date_str):
    """解析日期字串"""
    try:
        # 處理不同的日期格式
        date_formats = ['%Y-%m-%d', '%m-%d', '%Y/%m/%d', '%m/%d']
        
        for fmt in date_formats:
            try:
                if fmt in ['%m-%d', '%m/%d']:
                    # 如果只有月日，加上今年
                    date_obj = datetime.strptime(date_str, fmt)
                    current_year = get_taiwan_time().year  # 使用台灣時間的年份
                    return date_obj.replace(year=current_year).strftime('%Y-%m-%d')
                else:
                    return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
                
        # 處理相對日期
        today = get_taiwan_time()  # 使用台灣時間
        if '今天' in date_str or '今日' in date_str:
            return today.strftime('%Y-%m-%d')
        elif '明天' in date_str or '明日' in date_str:
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif '後天' in date_str:
            return (today + timedelta(days=2)).strftime('%Y-%m-%d')
        elif '大後天' in date_str:
            return (today + timedelta(days=3)).strftime('%Y-%m-%d')
        
        return None
    except:
        return None

class SimpleNoteManager:
    def add_note(self, user_id, note_text, deadline=None):
        """新增記事"""
        if user_id not in user_notes:
            user_notes[user_id] = []
        
        note = {
            'id': len(user_notes[user_id]) + 1,
            'text': note_text,
            'deadline': deadline,
            'time': get_taiwan_time().strftime('%Y-%m-%d %H:%M')  # 使用台灣時間
        }
        user_notes[user_id].append(note)
        return note['id']
    
    def get_notes(self, user_id):
        """取得所有記事（按截止日期排序）"""
        notes = user_notes.get(user_id, [])
        # 按截止日期排序：有截止日期的在前面，然後按日期排序
        def sort_key(note):
            if note['deadline']:
                return (0, note['deadline'])  # 有截止日期的優先
            else:
                return (1, note['time'])  # 沒有截止日期的按建立時間排序
        
        return sorted(notes, key=sort_key)
    
    def delete_note(self, user_id, note_id):
        """刪除記事"""
        if user_id not in user_notes:
            return False
        
        notes = user_notes[user_id]
        for i, note in enumerate(notes):
            if note['id'] == note_id:
                del notes[i]
                return True
        return False
    
    def clear_all_notes(self, user_id):
        """清空所有記事"""
        if user_id in user_notes:
            user_notes[user_id] = []
            return True
        return False

# 建立記事管理器
note_manager = SimpleNoteManager()

def format_deadline_status(deadline):
    """格式化截止日期狀態"""
    if not deadline:
        return ""
    
    try:
        deadline_date = datetime.strptime(deadline, '%Y-%m-%d')
        today = get_taiwan_time()  # 使用台灣時間
        days_diff = (deadline_date.date() - today.date()).days
        
        if days_diff < 0:
            return f"⚠️ 已過期 ({deadline}) 🔴"
        elif days_diff == 0:
            return f"⏰ 今天到期！🟠"
        elif days_diff == 1:
            return f"⏰ 明天到期 🟡"
        elif days_diff <= 3:
            return f"⏰ {days_diff}天後到期 🟢"
        else:
            return f"⏰ {deadline} ({days_diff}天後)"
    except:
        return f"⏰ {deadline}"

def handle_user_message(message, user_id):
    """處理使用者訊息"""
    message = message.strip()
    
    # 新增記事（支援截止日期）
    if message.startswith('記 ') or message.startswith('新增 '):
        note_content = message[2:].strip()
        
        if not note_content:
            return "❌ 請輸入記事內容！\n範例: 記 買牛奶\n範例: 記 開會 明天"
        
        # 解析截止日期
        deadline = None
        date_pattern = r'(\d{4}-\d{2}-\d{2}|\d{1,2}-\d{1,2}|\d{4}/\d{1,2}/\d{1,2}|\d{1,2}/\d{1,2}|今天|明天|後天|大後天|今日|明日)'
        date_match = re.search(date_pattern, note_content)
        
        if date_match:
            date_str = date_match.group(1)
            deadline = parse_date(date_str)
            note_content = re.sub(date_pattern, '', note_content).strip()
        
        if not note_content:
            return "❌ 請輸入記事內容！\n範例: 記 買牛奶 明天"
        
        note_id = note_manager.add_note(user_id, note_content, deadline)
        
        response = f"✅ 記事已儲存！\n📝 內容: {note_content}\n🆔 編號: {note_id}\n⏰ 建立時間: {get_taiwan_time().strftime('%H:%M')}"  # 使用台灣時間
        if deadline:
            response += f"\n📅 截止日期: {deadline}"
            response += f"\n{format_deadline_status(deadline)}"
        
        return response
    
    # 查看記事
    elif any(word in message for word in ['查看', '記事', '列表', 'list']):
        notes = note_manager.get_notes(user_id)
        if not notes:
            return "📝 目前沒有記事\n輸入「記 內容」來新增第一則記事！\n\n💡 支援截止日期:\n• 記 買牛奶 明天\n• 記 開會 2024-07-25\n• 記 繳費 12-31"
        
        result = "📋 你的記事清單:\n" + "="*20 + "\n"
        for note in notes:
            result += f"\n🆔 [{note['id']}] {note['text']}\n"
            result += f"📅 建立: {note['time']}\n"
            
            if note['deadline']:
                result += f"{format_deadline_status(note['deadline'])}\n"
            else:
                result += "📌 無截止日期\n"
        
        result += f"\n💡 刪除記事: 刪除 [編號]"
        return result
    
    # 查看今日到期的記事
    elif any(word in message for word in ['今日', '今天', '到期', 'today']):
        notes = note_manager.get_notes(user_id)
        today = get_taiwan_time().strftime('%Y-%m-%d')  # 使用台灣時間
        today_notes = [note for note in notes if note['deadline'] == today]
        
        if not today_notes:
            return f"📅 今日 ({today}) 沒有到期的記事！\n\n💪 輕鬆的一天～"
        
        result = f"📅 今日到期記事 ({today}):\n" + "="*20 + "\n"
        for note in today_notes:
            result += f"\n🔥 [{note['id']}] {note['text']}\n"
            result += f"⏰ 今天到期！🟠\n"
        
        return result
    
    # 刪除記事
    elif message.startswith('刪除 '):
        try:
            note_id = int(message[3:].strip())
            if note_manager.delete_note(user_id, note_id):
                return f"🗑️ 已刪除記事 {note_id}"
            else:
                return f"❌ 找不到編號 {note_id} 的記事"
        except ValueError:
            return "❌ 請輸入正確格式: 刪除 [編號]\n範例: 刪除 1"
    
    # 清空所有記事
    elif any(word in message for word in ['清空', '全部刪除', 'clear']):
        if note_manager.clear_all_notes(user_id):
            return "🗑️ 已清空所有記事！"
        else:
            return "📝 目前沒有記事可清空"
    
    # 使用說明
    elif any(word in message for word in ['幫助', 'help', '說明', '功能']):
        return """📱 記事機器人使用說明:

📝 新增記事:
• 記 [內容]
• 記 [內容] [日期]
• 新增 [內容] [日期]

📋 查看記事:
• 查看 - 所有記事
• 記事 - 所有記事  
• 今日 - 今天到期的記事

🗑️ 刪除記事:
• 刪除 [編號]
• 清空 (刪除全部)

📅 日期格式:
• 今天、明天、後天
• 12-31、2024-12-31
• 12/31、2024/12/31

💡 範例:
• 記 買菜 明天
• 記 開會 2024-07-25
• 記 繳電費 12-31
• 查看
• 今日
• 刪除 1"""
    
    # 問候語
    elif any(word in message for word in ['你好', 'hello', 'hi', '嗨']):
        return "👋 哈囉！我是記事機器人！\n\n📝 快速開始:\n• 記 內容 - 新增記事\n• 記 內容 日期 - 新增有截止日期的記事\n• 查看 - 看所有記事\n• 今日 - 看今天到期的記事\n• 幫助 - 完整功能說明"
    
    # 預設回應
    else:
        return f"🤔 不太懂「{message}」的意思\n\n💡 試試這些:\n• 記 今天要做的事 明天\n• 查看\n• 今日\n• 幫助"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@app.route("/", methods=['GET'])
def home():
    return "記事機器人運行中 🤖"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id
    
    # 處理訊息並取得回應
    reply_text = handle_user_message(user_message, user_id)
    
    # 回覆訊息
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)