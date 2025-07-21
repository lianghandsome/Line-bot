from flask import Flask, request, abort
import os
import json
from datetime import datetime
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

# 簡單的記憶體儲存（重啟後會清空）
user_notes = {}

class SimpleNoteManager:
    def add_note(self, user_id, note_text):
        """新增記事"""
        if user_id not in user_notes:
            user_notes[user_id] = []
        
        note = {
            'id': len(user_notes[user_id]) + 1,
            'text': note_text,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        user_notes[user_id].append(note)
        return note['id']
    
    def get_notes(self, user_id):
        """取得所有記事"""
        return user_notes.get(user_id, [])
    
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

def handle_user_message(message, user_id):
    """處理使用者訊息"""
    message = message.strip()
    
    # 新增記事
    if message.startswith('記 ') or message.startswith('新增 '):
        note_text = message[2:].strip()
        if note_text:
            note_id = note_manager.add_note(user_id, note_text)
            return f"✅ 記事已儲存！\n📝 內容: {note_text}\n🆔 編號: {note_id}\n⏰ 時間: {datetime.now().strftime('%H:%M')}"
        else:
            return "❌ 請輸入記事內容！\n範例: 記 買牛奶"
    
    # 查看記事
    elif any(word in message for word in ['查看', '記事', '列表', 'list']):
        notes = note_manager.get_notes(user_id)
        if not notes:
            return "📝 目前沒有記事\n輸入「記 內容」來新增第一則記事！"
        
        result = "📋 你的記事清單:\n" + "="*20 + "\n"
        for note in notes:
            result += f"\n🆔 [{note['id']}] {note['text']}\n"
            result += f"⏰ {note['time']}\n"
        
        result += f"\n💡 刪除記事: 刪除 [編號]"
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
• 新增 [內容]

📋 查看記事:
• 查看
• 記事
• 列表

🗑️ 刪除記事:
• 刪除 [編號]
• 清空 (刪除全部)

💡 範例:
• 記 明天要買菜
• 記 下午3點開會
• 查看
• 刪除 1"""
    
    # 問候語
    elif any(word in message for word in ['你好', 'hello', 'hi', '嗨']):
        return "👋 哈囉！我是記事機器人！\n\n📝 快速開始:\n• 輸入「記 內容」新增記事\n• 輸入「查看」看所有記事\n• 輸入「幫助」看完整功能"
    
    # 預設回應
    else:
        return f"🤔 不太懂「{message}」的意思\n\n💡 試試這些:\n• 記 今天要做的事\n• 查看\n• 幫助"

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