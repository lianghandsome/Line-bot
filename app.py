from flask import Flask, request, abort
import os
import json
from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo
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
TAIWAN_TZ = ZoneInfo('Asia/Taipei')

# 資料檔案路徑
DATA_FILE = 'accounting_data.json'

def get_taiwan_time():
    """取得台灣當前時間"""
    return datetime.now(TAIWAN_TZ)

def load_accounting_data():
    """從檔案載入記帳資料"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"載入資料時發生錯誤: {e}")
        return {}

def save_accounting_data(accounting_data):
    """將記帳資料儲存到檔案"""
    try:
        os.makedirs(os.path.dirname(DATA_FILE) if os.path.dirname(DATA_FILE) else '.', exist_ok=True)
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(accounting_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"儲存資料時發生錯誤: {e}")
        return False

# 載入現有資料
accounting_data = load_accounting_data()

def parse_date(date_str):
    """解析日期字串"""
    try:
        date_formats = ['%Y-%m-%d', '%m-%d', '%Y/%m/%d', '%m/%d']
        
        for fmt in date_formats:
            try:
                if fmt in ['%m-%d', '%m/%d']:
                    date_obj = datetime.strptime(date_str, fmt)
                    current_year = get_taiwan_time().year
                    return date_obj.replace(year=current_year).strftime('%Y-%m-%d')
                else:
                    return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
                
        # 處理相對日期
        today = get_taiwan_time()
        if '今天' in date_str or '今日' in date_str:
            return today.strftime('%Y-%m-%d')
        elif '明天' in date_str or '明日' in date_str:
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif '昨天' in date_str:
            return (today - timedelta(days=1)).strftime('%Y-%m-%d')
        elif '前天' in date_str:
            return (today - timedelta(days=2)).strftime('%Y-%m-%d')
        
        return None
    except:
        return None

class AccountingManager:
    def add_record(self, user_id, amount, category, description, record_type, date=None):
        """新增記帳記錄"""
        if user_id not in accounting_data:
            accounting_data[user_id] = []
        
        # 找出新的 ID
        existing_ids = [record['id'] for record in accounting_data[user_id]]
        new_id = max(existing_ids, default=0) + 1
        
        record = {
            'id': new_id,
            'type': record_type,  # 'income' 或 'expense'
            'amount': amount,
            'category': category,
            'description': description,
            'date': date or get_taiwan_time().strftime('%Y-%m-%d'),
            'time': get_taiwan_time().strftime('%H:%M'),
            'timestamp': get_taiwan_time().timestamp()
        }
        
        accounting_data[user_id].append(record)
        
        if save_accounting_data(accounting_data):
            return new_id
        else:
            accounting_data[user_id].pop()
            return None
    
    def get_records(self, user_id, days=None):
        """取得記帳記錄"""
        records = accounting_data.get(user_id, [])
        
        if days:
            cutoff_date = (get_taiwan_time() - timedelta(days=days)).strftime('%Y-%m-%d')
            records = [r for r in records if r['date'] >= cutoff_date]
        
        return sorted(records, key=lambda x: (x['date'], x['timestamp']), reverse=True)
    
    def delete_record(self, user_id, record_id):
        """刪除記帳記錄"""
        if user_id not in accounting_data:
            return False
        
        records = accounting_data[user_id]
        for i, record in enumerate(records):
            if record['id'] == record_id:
                del records[i]
                save_accounting_data(accounting_data)
                return True
        return False
    
    def get_summary(self, user_id, days=None):
        """取得收支總結"""
        records = self.get_records(user_id, days)
        
        total_income = sum(r['amount'] for r in records if r['type'] == 'income')
        total_expense = sum(r['amount'] for r in records if r['type'] == 'expense')
        balance = total_income - total_expense
        
        # 分類統計
        categories = {}
        for record in records:
            cat = record['category']
            if cat not in categories:
                categories[cat] = {'income': 0, 'expense': 0}
            categories[cat][record['type']] += record['amount']
        
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': balance,
            'categories': categories,
            'record_count': len(records)
        }

# 建立記帳管理器
accounting_manager = AccountingManager()

# 常用分類
EXPENSE_CATEGORIES = ['餐飲', '交通', '購物', '娛樂', '醫療', '生活', '房租', '水電', '教育', '其他']
INCOME_CATEGORIES = ['薪水', '獎金', '投資', '兼職', '紅包', '其他']

def parse_accounting_input(message):
    """解析記帳輸入"""
    # 支援格式：
    # 支出 100 餐飲 午餐
    # 支出 100 餐飲 午餐 昨天
    # 收入 5000 薪水 月薪
    # +100 餐飲 午餐 (簡化支出)
    # -100 餐飲 午餐 (簡化收入)
    
    original_msg = message.strip()
    
    # 處理簡化格式
    if message.startswith('+'):
        message = f"支出 {message[1:]}"
    elif message.startswith('-'):
        message = f"收入 {message[1:]}"
    
    parts = message.split()
    if len(parts) < 3:
        return None
    
    # 判斷類型
    if parts[0] in ['支出', '花費', '支', 'expense', 'exp']:
        record_type = 'expense'
    elif parts[0] in ['收入', '賺', '收', 'income', 'inc']:
        record_type = 'income'
    else:
        return None
    
    try:
        amount = float(parts[1])
        if amount <= 0:
            return None
    except ValueError:
        return None
    
    category = parts[2] if len(parts) > 2 else '其他'
    
    # 描述和日期解析
    description_parts = []
    date = None
    
    for i in range(3, len(parts)):
        part = parts[i]
        parsed_date = parse_date(part)
        if parsed_date and not date:
            date = parsed_date
        else:
            description_parts.append(part)
    
    description = ' '.join(description_parts) if description_parts else category
    
    return {
        'type': record_type,
        'amount': amount,
        'category': category,
        'description': description,
        'date': date
    }

def format_amount(amount):
    """格式化金額顯示"""
    if amount >= 0:
        return f"${amount:,.0f}"
    else:
        return f"-${abs(amount):,.0f}"

def handle_user_message(message, user_id):
    """處理使用者訊息"""
    message = message.strip()
    
    # 記帳功能
    accounting_input = parse_accounting_input(message)
    if accounting_input:
        record_id = accounting_manager.add_record(
            user_id,
            accounting_input['amount'],
            accounting_input['category'],
            accounting_input['description'],
            accounting_input['type'],
            accounting_input['date']
        )
        
        if record_id is None:
            return "❌ 記帳失敗，請稍後再試"
        
        type_emoji = "💰" if accounting_input['type'] == 'income' else "💸"
        type_text = "收入" if accounting_input['type'] == 'income' else "支出"
        
        response = f"{type_emoji} {type_text}記錄已儲存！\n"
        response += f"🆔 編號: {record_id}\n"
        response += f"💵 金額: {format_amount(accounting_input['amount'])}\n"
        response += f"🏷️ 分類: {accounting_input['category']}\n"
        response += f"📝 說明: {accounting_input['description']}\n"
        response += f"📅 日期: {accounting_input['date'] or get_taiwan_time().strftime('%Y-%m-%d')}\n"
        response += f"⏰ 時間: {get_taiwan_time().strftime('%H:%M')}"
        
        return response
    
    # 查看記錄
    elif any(word in message for word in ['帳單', '記錄', '查看', '清單', 'list']):
        # 解析天數
        days = None
        if '今天' in message or '今日' in message:
            days = 0
        elif '昨天' in message:
            days = 1
        elif '本週' in message or '這週' in message:
            days = 7
        elif '本月' in message or '這月' in message:
            days = 30
        elif re.search(r'(\d+)天', message):
            match = re.search(r'(\d+)天', message)
            days = int(match.group(1))
        
        if days == 0:
            today = get_taiwan_time().strftime('%Y-%m-%d')
            records = [r for r in accounting_manager.get_records(user_id) if r['date'] == today]
            title = f"📊 今日帳單 ({today})"
        else:
            records = accounting_manager.get_records(user_id, days)
            if days:
                title = f"📊 近{days}天記錄"
            else:
                title = "📊 所有記錄"
        
        if not records:
            return f"📝 {title}\n目前沒有記錄\n\n💡 開始記帳:\n• 支出 100 餐飲 午餐\n• 收入 5000 薪水\n• +50 咖啡 (支出簡寫)\n• -3000 兼職 (收入簡寫)"
        
        result = f"{title}\n" + "="*25 + "\n"
        
        for record in records[:10]:  # 最多顯示10筆
            type_emoji = "💰" if record['type'] == 'income' else "💸"
            sign = "+" if record['type'] == 'income' else "-"
            
            result += f"\n{type_emoji} [{record['id']}] {sign}{format_amount(record['amount'])}\n"
            result += f"🏷️ {record['category']} | 📝 {record['description']}\n"
            result += f"📅 {record['date']} {record['time']}\n"
        
        if len(records) > 10:
            result += f"\n... 還有 {len(records) - 10} 筆記錄"
        
        result += f"\n\n💡 刪除: 刪除 [編號] | 統計: 統計"
        return result
    
    # 統計功能
    elif any(word in message for word in ['統計', '總結', '分析', 'summary', 'stat']):
        days = None
        if '今天' in message:
            days = 0
        elif '本週' in message or '這週' in message:
            days = 7
        elif '本月' in message or '這月' in message:
            days = 30
        elif re.search(r'(\d+)天', message):
            match = re.search(r'(\d+)天', message)
            days = int(match.group(1))
        
        summary = accounting_manager.get_summary(user_id, days)
        
        if summary['record_count'] == 0:
            return "📊 目前沒有記錄可統計\n\n開始記帳吧！"
        
        period_text = ""
        if days == 0:
            period_text = "今日"
        elif days:
            period_text = f"近{days}天"
        else:
            period_text = "全部"
        
        result = f"📊 {period_text}統計報告\n" + "="*20 + "\n"
        result += f"💰 總收入: {format_amount(summary['total_income'])}\n"
        result += f"💸 總支出: {format_amount(summary['total_expense'])}\n"
        result += f"💵 淨收益: {format_amount(summary['balance'])}\n"
        result += f"📝 記錄數: {summary['record_count']} 筆\n"
        
        if summary['categories']:
            result += f"\n🏷️ 分類統計:\n"
            for category, amounts in summary['categories'].items():
                if amounts['expense'] > 0:
                    result += f"• {category}: -{format_amount(amounts['expense'])}\n"
                if amounts['income'] > 0:
                    result += f"• {category}: +{format_amount(amounts['income'])}\n"
        
        # 消費建議
        if summary['balance'] < 0:
            result += f"\n⚠️ 支出大於收入，注意控制開銷！"
        elif summary['balance'] > 0:
            result += f"\n✅ 收支平衡良好！"
        
        return result
    
    # 刪除記錄
    elif message.startswith('刪除 '):
        try:
            record_id = int(message[3:].strip())
            if accounting_manager.delete_record(user_id, record_id):
                return f"🗑️ 已刪除記錄 {record_id}"
            else:
                return f"❌ 找不到編號 {record_id} 的記錄"
        except ValueError:
            return "❌ 請輸入正確格式: 刪除 [編號]\n範例: 刪除 1"
    
    # 分類參考
    elif any(word in message for word in ['分類', 'category', '類別']):
        result = "🏷️ 常用分類參考:\n\n"
        result += "💸 支出分類:\n"
        result += "• " + " | ".join(EXPENSE_CATEGORIES) + "\n\n"
        result += "💰 收入分類:\n"
        result += "• " + " | ".join(INCOME_CATEGORIES) + "\n\n"
        result += "💡 也可以自訂分類名稱！"
        return result
    
    # 系統狀態
    elif any(word in message for word in ['狀態', 'status', '檢查']):
        total_records = sum(len(records) for records in accounting_data.values())
        user_record_count = len(accounting_data.get(user_id, []))
        
        file_exists = os.path.exists(DATA_FILE)
        file_size = os.path.getsize(DATA_FILE) if file_exists else 0
        
        summary = accounting_manager.get_summary(user_id)
        
        result = f"📊 系統狀態:\n\n"
        result += f"📁 資料檔案: {'✅ 存在' if file_exists else '❌ 不存在'}\n"
        result += f"📏 檔案大小: {file_size} bytes\n"
        result += f"👤 你的記錄: {user_record_count} 筆\n"
        result += f"🌐 總記錄數: {total_records} 筆\n"
        result += f"💾 資料持久化: ✅ 啟用\n"
        
        if user_record_count > 0:
            result += f"\n💰 你的總收入: {format_amount(summary['total_income'])}\n"
            result += f"💸 你的總支出: {format_amount(summary['total_expense'])}\n"
            result += f"💵 你的淨收益: {format_amount(summary['balance'])}"
        
        return result
    
    # 使用說明
    elif any(word in message for word in ['幫助', 'help', '說明', '功能']):
        return """💰 記帳機器人使用說明:

📝 記帳格式:
• 支出 [金額] [分類] [說明] [日期]
• 收入 [金額] [分類] [說明] [日期]
• +[金額] [分類] [說明] (支出簡寫)
• -[金額] [分類] [說明] (收入簡寫)

📊 查看功能:
• 帳單 - 所有記錄
• 今天帳單 - 今日記錄
• 本週帳單 - 本週記錄
• 統計 - 收支統計
• 今天統計 - 今日統計

🗑️ 管理功能:
• 刪除 [編號] - 刪除記錄
• 分類 - 查看分類參考
• 狀態 - 系統狀態

📅 日期格式:
• 今天、昨天、前天
• 12-31、2024-12-31
• 12/31、2024/12/31

💡 範例:
• 支出 150 餐飲 午餐
• 收入 5000 薪水 月薪
• +50 咖啡 星巴克 昨天
• -3000 兼職 家教費
• 今天帳單
• 本月統計"""
    
    # 問候語
    elif any(word in message for word in ['你好', 'hello', 'hi', '嗨']):
        summary = accounting_manager.get_summary(user_id)
        greeting = "👋 哈囉！我是記帳機器人！\n\n"
        
        if summary['record_count'] > 0:
            greeting += f"💰 你目前的淨收益: {format_amount(summary['balance'])}\n"
            greeting += f"📝 共有 {summary['record_count']} 筆記錄\n\n"
        
        greeting += "💡 快速開始:\n"
        greeting += "• 支出 100 餐飲 午餐\n"
        greeting += "• 收入 5000 薪水\n"
        greeting += "• +50 咖啡 (支出簡寫)\n"
        greeting += "• 帳單 (查看記錄)\n"
        greeting += "• 統計 (收支分析)\n"
        greeting += "• 幫助 (完整說明)"
        
        return greeting
    
    # 預設回應
    else:
        return f"🤔 不太懂「{message}」的意思\n\n💡 試試這些:\n• 支出 100 餐飲 午餐\n• 收入 5000 薪水\n• +50 咖啡 (支出簡寫)\n• 帳單 (查看記錄)\n• 統計 (分析)\n• 幫助 (說明)"

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
    total_records = sum(len(records) for records in accounting_data.values())
    file_exists = os.path.exists(DATA_FILE)
    file_size = os.path.getsize(DATA_FILE) if file_exists else 0
    
    total_income = 0
    total_expense = 0
    for user_records in accounting_data.values():
        for record in user_records:
            if record['type'] == 'income':
                total_income += record['amount']
            else:
                total_expense += record['amount']
    
    return f"""
    <h1>💰 記帳機器人運行中 🤖</h1>
    <h3>系統狀態:</h3>
    <ul>
        <li>📁 資料檔案: {'✅ 存在' if file_exists else '❌ 不存在'}</li>
        <li>📏 檔案大小: {file_size} bytes</li>
        <li>📝 總記錄數: {total_records} 筆</li>
        <li>💰 總收入: {format_amount(total_income)}</li>
        <li>💸 總支出: {format_amount(total_expense)}</li>
        <li>💵 總淨收益: {format_amount(total_income - total_expense)}</li>
        <li>💾 資料持久化: ✅ 啟用</li>
        <li>⏰ 伺服器時間: {get_taiwan_time().strftime('%Y-%m-%d %H:%M:%S')} (台灣時間)</li>
    </ul>
    """

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