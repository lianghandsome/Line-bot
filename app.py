from flask import Flask, request, abort
import os
import json
from datetime import datetime, timedelta
import re
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    TemplateMessage,
    ButtonsTemplate,
    MessageAction
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

app = Flask(__name__)

configuration = Configuration(access_token='IOjd7xRA4ZwlMNxS6H57U1KixD3RtvE3d4P4iAeVYdSbTMANZmKIooyvK98EEUgds3M/nkOubYsJNTNu5Z8rnEbULqAGyicU/bN5nh4OZVqeDmIE/2K5RNvlXsrCKqtjJ1yBJ6FRmmQW5LNxc6NdggdB04t89/1O/w1cDnyilFU=')

handler = WebhookHandler('69258da7d559a4ef4709a9ba6dcbb1b1')

# 用字典儲存每個用戶的待辦事項 (實際應用中建議用資料庫)
user_todos = {}

class TodoManager:
    def __init__(self):
        self.todos = {}
    
    def add_todo(self, user_id, task, deadline=None, priority='一般'):
        if user_id not in self.todos:
            self.todos[user_id] = []
        
        todo_item = {
            'id': len(self.todos[user_id]) + 1,
            'task': task,
            'deadline': deadline,
            'priority': priority,
            'completed': False,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        
        self.todos[user_id].append(todo_item)
        return todo_item['id']
    
    def get_todos(self, user_id, show_completed=False):
        if user_id not in self.todos:
            return []
        
        todos = self.todos[user_id]
        if not show_completed:
            todos = [todo for todo in todos if not todo['completed']]
        
        return sorted(todos, key=lambda x: (x['completed'], x.get('deadline') or '9999-12-31'))
    
    def complete_todo(self, user_id, todo_id):
        if user_id in self.todos:
            for todo in self.todos[user_id]:
                if todo['id'] == todo_id:
                    todo['completed'] = True
                    return True
        return False
    
    def delete_todo(self, user_id, todo_id):
        if user_id in self.todos:
            self.todos[user_id] = [todo for todo in self.todos[user_id] if todo['id'] != todo_id]
            return True
        return False
    
    def get_today_todos(self, user_id):
        today = datetime.now().strftime('%Y-%m-%d')
        todos = self.get_todos(user_id)
        return [todo for todo in todos if todo.get('deadline', '').startswith(today)]
    
    def get_urgent_todos(self, user_id):
        todos = self.get_todos(user_id)
        return [todo for todo in todos if todo['priority'] == '緊急']

todo_manager = TodoManager()

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

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
                    current_year = datetime.now().year
                    return date_obj.replace(year=current_year).strftime('%Y-%m-%d')
                else:
                    return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
                
        # 處理相對日期
        today = datetime.now()
        if '今天' in date_str or '今日' in date_str:
            return today.strftime('%Y-%m-%d')
        elif '明天' in date_str or '明日' in date_str:
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif '後天' in date_str:
            return (today + timedelta(days=2)).strftime('%Y-%m-%d')
        
        return None
    except:
        return None

def create_todo_menu():
    """創建待辦事項選單"""
    return TemplateMessage(
        alt_text='待辦事項選單',
        template=ButtonsTemplate(
            title='📅 我的待辦事項助手',
            text='選擇你要進行的操作：',
            actions=[
                MessageAction(label='📋 查看待辦事項', text='查看待辦事項'),
                MessageAction(label='📝 新增待辦事項', text='如何新增待辦事項'),
                MessageAction(label='⏰ 今日待辦', text='今日待辦'),
                MessageAction(label='❗ 緊急事項', text='緊急事項')
            ]
        )
    )

def format_todo_list(todos, title="📋 你的待辦事項"):
    """格式化待辦事項列表"""
    if not todos:
        return f"{title}\n\n目前沒有待辦事項！\n輸入「新增 任務內容」來添加第一個任務 📝"
    
    result = f"{title}\n"
    result += "=" * 20 + "\n"
    
    for todo in todos:
        status = "✅" if todo['completed'] else "⭕"
        priority_emoji = {"緊急": "🔥", "重要": "⚡", "一般": "📌"}
        priority = priority_emoji.get(todo['priority'], "📌")
        
        result += f"\n{status} [{todo['id']}] {priority} {todo['task']}\n"
        
        if todo.get('deadline'):
            deadline_date = datetime.strptime(todo['deadline'], '%Y-%m-%d')
            today = datetime.now()
            days_diff = (deadline_date - today).days
            
            if days_diff < 0:
                result += f"   ⏰ 已過期 ({todo['deadline']}) ⚠️\n"
            elif days_diff == 0:
                result += f"   ⏰ 今天到期！\n"
            elif days_diff == 1:
                result += f"   ⏰ 明天到期\n"
            else:
                result += f"   ⏰ {todo['deadline']} ({days_diff}天後)\n"
        
        result += f"   📅 建立時間: {todo['created_at']}\n"
    
    result += f"\n💡 小提示：\n"
    result += f"• 輸入「完成 [編號]」標記完成\n"
    result += f"• 輸入「刪除 [編號]」刪除項目\n"
    result += f"• 輸入「新增 任務內容」添加新任務"
    
    return result

def get_smart_reply(user_message, user_id):
    """智能回應函數"""
    message = user_message.strip()
    
    # 待辦事項主選單
    if any(word in message for word in ['待辦', '行事曆', '任務', 'todo', '選單']):
        return create_todo_menu(), "template"
    
    # 新增待辦事項
    elif message.startswith('新增 ') or message.startswith('加入 ') or message.startswith('添加 '):
        task_content = message[3:].strip()  # 移除「新增 」
        
        # 解析優先級
        priority = '一般'
        if '緊急' in task_content or '急' in task_content:
            priority = '緊急'
            task_content = task_content.replace('緊急', '').replace('急', '').strip()
        elif '重要' in task_content:
            priority = '重要'
            task_content = task_content.replace('重要', '').strip()
        
        # 解析截止日期
        deadline = None
        date_pattern = r'(\d{4}-\d{2}-\d{2}|\d{1,2}-\d{1,2}|\d{4}/\d{1,2}/\d{1,2}|\d{1,2}/\d{1,2}|今天|明天|後天)'
        date_match = re.search(date_pattern, task_content)
        
        if date_match:
            date_str = date_match.group(1)
            deadline = parse_date(date_str)
            task_content = re.sub(date_pattern, '', task_content).strip()
        
        if not task_content:
            return "❌ 請輸入任務內容！\n\n範例：\n• 新增 買牛奶\n• 新增 開會 2024-07-25\n• 新增 緊急 繳電費 明天", "text"
        
        todo_id = todo_manager.add_todo(user_id, task_content, deadline, priority)
        
        response = f"✅ 成功新增待辦事項！\n\n"
        response += f"📌 任務: {task_content}\n"
        response += f"🏷️ 優先級: {priority}\n"
        if deadline:
            response += f"⏰ 截止日期: {deadline}\n"
        response += f"🆔 編號: {todo_id}\n\n"
        response += "輸入「查看待辦事項」來查看所有任務！"
        
        return response, "text"
    
    # 查看待辦事項
    elif any(word in message for word in ['查看待辦', '待辦事項', '任務列表', '查看任務']):
        todos = todo_manager.get_todos(user_id)
        return format_todo_list(todos), "text"
    
    # 今日待辦
    elif any(word in message for word in ['今日待辦', '今天的任務', '今天待辦']):
        today_todos = todo_manager.get_today_todos(user_id)
        return format_todo_list(today_todos, "⏰ 今日待辦事項"), "text"
    
    # 緊急事項
    elif any(word in message for word in ['緊急事項', '緊急任務', '急件']):
        urgent_todos = todo_manager.get_urgent_todos(user_id)
        return format_todo_list(urgent_todos, "🔥 緊急事項"), "text"
    
    # 完成任務
    elif message.startswith('完成 ') or message.startswith('做完 '):
        try:
            todo_id = int(message.split(' ')[1])
            if todo_manager.complete_todo(user_id, todo_id):
                return f"🎉 太棒了！任務 {todo_id} 已標記為完成！\n\n繼續保持，你做得很好！💪", "text"
            else:
                return f"❌ 找不到編號 {todo_id} 的任務。\n\n輸入「查看待辦事項」確認編號。", "text"
        except (IndexError, ValueError):
            return "❌ 請輸入正確格式：完成 [編號]\n\n例如：完成 1", "text"
    
    # 刪除任務
    elif message.startswith('刪除 ') or message.startswith('移除 '):
        try:
            todo_id = int(message.split(' ')[1])
            if todo_manager.delete_todo(user_id, todo_id):
                return f"🗑️ 已刪除任務 {todo_id}！", "text"
            else:
                return f"❌ 找不到編號 {todo_id} 的任務。", "text"
        except (IndexError, ValueError):
            return "❌ 請輸入正確格式：刪除 [編號]\n\n例如：刪除 1", "text"
    
    # 使用說明
    elif any(word in message for word in ['如何新增', '怎麼新增', '新增方法', '使用說明']):
        return """📝 新增待辦事項說明：

🔤 基本格式：
新增 任務內容

📅 含日期：
新增 任務內容 日期
• 新增 買牛奶 今天
• 新增 開會 2024-07-25  
• 新增 繳費 12-25

🏷️ 設定優先級：
• 新增 緊急 繳稅 明天
• 新增 重要 面試 2024-08-01

💡 更多範例：
• 新增 買菜
• 新增 看醫生 明天
• 新增 緊急 報告 後天
• 新增 重要 會議 8-15

試試看吧！""", "text"
    
    # 問候語
    elif any(word in message for word in ['你好', 'hello', 'hi', '嗨']):
        return "👋 哈囉！我是你的個人待辦事項助手！\n\n📋 我可以幫你：\n• 記錄要做的事情\n• 設定截止日期\n• 提醒緊急任務\n• 追蹤完成進度\n\n輸入「待辦」開始使用，或「使用說明」看教學！", "text"
    
    # 幫助
    elif any(word in message for word in ['幫助', 'help', '功能']):
        return """📱 待辦事項機器人功能：

📝 新增任務：
• 新增 [任務內容]
• 新增 [任務] [日期]
• 新增 緊急/重要 [任務]

📋 查看任務：
• 查看待辦事項 - 所有未完成
• 今日待辦 - 今天要做的
• 緊急事項 - 緊急任務

✅ 管理任務：
• 完成 [編號] - 標記完成
• 刪除 [編號] - 刪除任務

🎯 其他：
• 待辦 - 主選單
• 使用說明 - 詳細教學

現在就試試「新增 買晚餐」吧！""", "text"
    
    # 預設回應
    else:
        return f"🤔 我沒理解「{message}」的意思\n\n試試這些指令：\n• 「待辦」- 主選單\n• 「新增 任務內容」- 新增任務\n• 「查看待辦事項」- 查看任務\n• 「幫助」- 完整功能列表", "text"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id  # 取得用戶ID
    
    reply_content, reply_type = get_smart_reply(user_message, user_id)
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        if reply_type == "template":
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[reply_content]
                )
            )
        else:
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_content)]
                )
            )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)