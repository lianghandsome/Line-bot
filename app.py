from flask import Flask, request, abort
import os
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
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

app = Flask(__name__)

configuration = Configuration(access_token='IOjd7xRA4ZwlMNxS6H57U1KixD3RtvE3d4P4iAeVYdSbTMANZmKIooyvK98EEUgds3M/nkOubYsJNTNu5Z8rnEbULqAGyicU/bN5nh4OZVqeDmIE/2K5RNvlXsrCKqtjJ1yBJ6FRmmQW5LNxc6NdggdB04t89/1O/w1cDnyilFU=')

handler = WebhookHandler('69258da7d559a4ef4709a9ba6dcbb1b1')

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# 智能回應函數
def get_smart_reply(user_message):
    """根據用戶訊息產生智能回應"""
    message = user_message.lower()  # 轉換為小寫方便比對
    
    # 問候語
    if any(word in message for word in ['你好', 'hello', 'hi', '嗨']):
        return "你好！我是你的 LINE Bot 助手 😊"
    
    # 詢問時間
    elif any(word in message for word in ['時間', 'time', '現在幾點']):
        from datetime import datetime
        now = datetime.now()
        return f"現在時間是：{now.strftime('%Y-%m-%d %H:%M:%S')}"
    
    # 天氣相關
    elif any(word in message for word in ['天氣', 'weather']):
        return "我目前還不能查詢天氣，但建議你可以看看氣象 APP 喔！☀️"
    
    # 笑話
    elif any(word in message for word in ['笑話', 'joke', '說笑話']):
        jokes = [
            "為什麼程式設計師喜歡黑咖啡？因為他們不想 debug 牛奶！😂",
            "什麼是程式設計師最怕的事？客戶說：「這個功能很簡單，應該很快就能做好吧？」",
            "為什麼 Python 這麼受歡迎？因為它很好養！🐍"
        ]
        import random
        return random.choice(jokes)
    
    # 幫助
    elif any(word in message for word in ['幫助', 'help', '功能']):
        return """我可以幫你做這些事：
🔹 打招呼：說「你好」
🔹 查時間：問「現在幾點」
🔹 說笑話：說「說笑話」
🔹 聊天：隨便聊聊我都會回應！
        
還想要什麼功能嗎？"""
    
    # 愛心或感謝
    elif any(word in message for word in ['謝謝', 'thank', '愛你', '❤️', '♥️']):
        return "不客氣！很開心能幫到你 ❤️"
    
    # 數學計算（簡單的）
    elif '+' in message or '-' in message or '*' in message or '/' in message:
        try:
            # 簡單的數學運算（注意：實際應用中需要更安全的處理）
            result = eval(message.replace('×', '*').replace('÷', '/'))
            return f"計算結果：{result}"
        except:
            return "抱歉，我無法計算這個數學問題 🤔"
    
    # 預設回應
    else:
        responses = [
            f"你說：「{user_message}」，這很有趣！",
            "我了解你的想法！還有什麼想聊的嗎？",
            "嗯嗯，繼續說下去！我在聽 👂",
            f"關於「{user_message}」，我覺得很棒呢！",
            "哈哈，你真有趣！還有其他想問的嗎？"
        ]
        import random
        return random.choice(responses)

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    # 取得用戶傳送的訊息
    user_message = event.message.text
    
    # 產生智能回應
    reply_text = get_smart_reply(user_message)
    
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
    app.run(host='0.0.0.0', port=port)