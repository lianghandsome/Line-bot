from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import json
import os
from datetime import datetime

app = Flask(__name__)

# LINE Bot 設定 (需要替換成你的實際值)
LINE_CHANNEL_ACCESS_TOKEN = 'IOjd7xRA4ZwlMNxS6H57U1KixD3RtvE3d4P4iAeVYdSbTMANZmKIooyvK98EEUgds3M/nkOubYsJNTNu5Z8rnEbULqAGyicU/bN5nh4OZVqeDmIE/2K5RNvlXsrCKqtjJ1yBJ6FRmmQW5LNxc6NdggdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '69258da7d559a4ef4709a9ba6dcbb1b1'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 簡單的記事存儲 (使用檔案存儲，實際應用建議使用資料庫)
NOTES_FILE = 'notes.json'

def load_notes():
    """載入記事資料"""
    try:
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except:
        return {}

def save_notes(notes):
    """儲存記事資料"""
    try:
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def get_user_notes(user_id):
    """取得用戶的記事"""
    notes = load_notes()
    return notes.get(user_id, [])

def add_note(user_id, note_content):
    """新增記事"""
    notes = load_notes()
    if user_id not in notes:
        notes[user_id] = []
    
    new_note = {
        'id': len(notes[user_id]) + 1,
        'content': note_content,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    notes[user_id].append(new_note)
    return save_notes(notes)

def delete_note(user_id, note_id):
    """刪除記事"""
    notes = load_notes()
    if user_id in notes:
        notes[user_id] = [note for note in notes[user_id] if note['id'] != note_id]
        return save_notes(notes)
    return False

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()
    
    # 處理不同的指令
    if text == '記事' or text == '查看記事' or text == '顯示記事':
        # 顯示所有記事
        user_notes = get_user_notes(user_id)
        
        if not user_notes:
            reply_text = "📝 目前沒有任何記事\n\n使用方式：\n• 直接輸入文字來新增記事\n• 輸入「記事」查看所有記事\n• 輸入「刪除 1」刪除第1筆記事\n• 輸入「說明」查看完整說明"
        else:
            reply_text = "📝 你的記事清單：\n\n"
            for note in user_notes:
                reply_text += f"#{note['id']} {note['content']}\n"
                reply_text += f"時間：{note['created_at']}\n\n"
    
    elif text.startswith('刪除 '):
        # 刪除記事
        try:
            note_id = int(text.split(' ', 1)[1])
            if delete_note(user_id, note_id):
                reply_text = f"✅ 已刪除記事 #{note_id}"
            else:
                reply_text = f"❌ 找不到記事 #{note_id}"
        except (ValueError, IndexError):
            reply_text = "❌ 請輸入正確的記事編號\n例如：刪除 1"
    
    elif text == '說明' or text == 'help' or text == '幫助':
        # 顯示使用說明
        reply_text = """📖 LINE Bot 記事本使用說明

🔹 新增記事：
直接輸入任何文字即可新增記事

🔹 查看記事：
輸入「記事」或「查看記事」

🔹 刪除記事：
輸入「刪除 編號」
例如：刪除 1

🔹 查看說明：
輸入「說明」

💡 小提示：每筆記事都會自動記錄建立時間"""
    
    elif text == '清空' or text == '清空記事':
        # 清空所有記事 (隱藏功能)
        notes = load_notes()
        if user_id in notes:
            notes[user_id] = []
            save_notes(notes)
        reply_text = "🗑️ 已清空所有記事"
    
    else:
        # 新增記事
        if len(text) > 200:
            reply_text = "❌ 記事內容過長，請限制在200字以內"
        else:
            if add_note(user_id, text):
                user_notes = get_user_notes(user_id)
                note_count = len(user_notes)
                reply_text = f"✅ 記事已新增 (#{note_count})\n\n內容：{text}\n\n輸入「記事」查看所有記事"
            else:
                reply_text = "❌ 記事新增失敗，請稍後再試"
    
    # 回覆訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    # 在生產環境中，建議使用 WSGI 服務器如 gunicorn
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))