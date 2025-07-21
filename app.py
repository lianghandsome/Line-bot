from flask import Flask, request, abort
import os
import random
from datetime import datetime
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
    AudioMessage,
    ImageMessage,
    StickerMessage,
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

# 音樂資料庫
MUSIC_DATABASE = {
    "流行": {
        "songs": [
            {"title": "告白氣球", "artist": "周杰倫", "youtube": "https://youtu.be/bu7nU9Mhpyo", "emoji": "🎈"},
            {"title": "說愛你", "artist": "蔡依林", "youtube": "https://youtu.be/OWIp0jSPMLU", "emoji": "💕"},
            {"title": "稻香", "artist": "周杰倫", "youtube": "https://youtu.be/WsS8w15XALA", "emoji": "🌾"},
            {"title": "小幸運", "artist": "田馥甄", "youtube": "https://youtu.be/8kLDEa_6GE8", "emoji": "🍀"},
        ]
    },
    "搖滾": {
        "songs": [
            {"title": "Born to Be Wild", "artist": "Steppenwolf", "youtube": "https://youtu.be/rMbATaj7Il8", "emoji": "🔥"},
            {"title": "Don't Stop Believin'", "artist": "Journey", "youtube": "https://youtu.be/1k8craCGpgs", "emoji": "⚡"},
            {"title": "We Will Rock You", "artist": "Queen", "youtube": "https://youtu.be/-tJYN-eG1zk", "emoji": "👑"},
        ]
    },
    "放鬆": {
        "songs": [
            {"title": "River Flows in You", "artist": "Yiruma", "youtube": "https://youtu.be/7maJOI3QMu0", "emoji": "🎹"},
            {"title": "Canon in D", "artist": "Pachelbel", "youtube": "https://youtu.be/NlprozGcs80", "emoji": "🎻"},
            {"title": "Clair de Lune", "artist": "Debussy", "youtube": "https://youtu.be/CvFH_6DNRCY", "emoji": "🌙"},
        ]
    },
    "電音": {
        "songs": [
            {"title": "Faded", "artist": "Alan Walker", "youtube": "https://youtu.be/60ItHLz5WEA", "emoji": "🎧"},
            {"title": "Titanium", "artist": "David Guetta", "youtube": "https://youtu.be/JRfuAukYTKg", "emoji": "💎"},
            {"title": "Animals", "artist": "Martin Garrix", "youtube": "https://youtu.be/gCYcHz2k5x0", "emoji": "🦁"},
        ]
    }
}

# 心情音樂推薦
MOOD_MUSIC = {
    "開心": ["流行", "電音"],
    "難過": ["放鬆", "流行"],
    "生氣": ["搖滾", "電音"],
    "放鬆": ["放鬆"],
    "興奮": ["搖滾", "電音"],
    "浪漫": ["流行", "放鬆"]
}

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

def get_random_song(genre=None):
    """隨機取得一首歌"""
    if genre and genre in MUSIC_DATABASE:
        songs = MUSIC_DATABASE[genre]["songs"]
    else:
        all_songs = []
        for genre_data in MUSIC_DATABASE.values():
            all_songs.extend(genre_data["songs"])
        songs = all_songs
    
    return random.choice(songs)

def get_music_by_mood(mood):
    """根據心情推薦音樂"""
    if mood in MOOD_MUSIC:
        recommended_genres = MOOD_MUSIC[mood]
        chosen_genre = random.choice(recommended_genres)
        return get_random_song(chosen_genre), chosen_genre
    else:
        return get_random_song(), "隨機"

def create_music_buttons():
    """創建音樂類型選擇按鈕"""
    return TemplateMessage(
        alt_text='選擇音樂類型',
        template=ButtonsTemplate(
            title='🎵 選擇你想聽的音樂類型',
            text='點擊下方按鈕來探索不同類型的音樂！',
            actions=[
                MessageAction(label='🎤 流行音樂', text='推薦流行音樂'),
                MessageAction(label='🎸 搖滾音樂', text='推薦搖滾音樂'),
                MessageAction(label='🎹 放鬆音樂', text='推薦放鬆音樂'),
                MessageAction(label='🎧 電音', text='推薦電音')
            ]
        )
    )

def get_smart_reply(user_message):
    """智能回應函數"""
    message = user_message.lower()
    
    # 音樂相關功能
    if any(word in message for word in ['音樂', 'music', '歌', '聽歌']):
        return create_music_buttons(), "template"
    
    elif any(word in message for word in ['推薦流行', '流行音樂']):
        song = get_random_song("流行")
        return f"🎤 推薦流行歌曲：\n\n{song['emoji']} 《{song['title']}》\n🎤 {song['artist']}\n\n🎵 YouTube: {song['youtube']}\n\n想聽更多嗎？輸入「音樂」來選擇其他類型！", "text"
    
    elif any(word in message for word in ['推薦搖滾', '搖滾音樂']):
        song = get_random_song("搖滾")
        return f"🎸 推薦搖滾歌曲：\n\n{song['emoji']} 《{song['title']}》\n🎤 {song['artist']}\n\n🎵 YouTube: {song['youtube']}\n\n搖滾萬歲！🤘", "text"
    
    elif any(word in message for word in ['推薦放鬆', '放鬆音樂']):
        song = get_random_song("放鬆")
        return f"🎹 推薦放鬆音樂：\n\n{song['emoji']} 《{song['title']}》\n🎤 {song['artist']}\n\n🎵 YouTube: {song['youtube']}\n\n好好放鬆一下吧～ ☁️", "text"
    
    elif any(word in message for word in ['推薦電音', '電音']):
        song = get_random_song("電音")
        return f"🎧 推薦電音：\n\n{song['emoji']} 《{song['title']}》\n🎤 {song['artist']}\n\n🎵 YouTube: {song['youtube']}\n\n準備好跳舞了嗎？💃🕺", "text"
    
    # 心情推薦
    elif any(word in message for word in ['開心', '快樂', '高興']):
        song, genre = get_music_by_mood("開心")
        return f"😊 你很開心呢！推薦這首{genre}歌曲：\n\n{song['emoji']} 《{song['title']}》\n🎤 {song['artist']}\n\n🎵 {song['youtube']}\n\n保持好心情！✨", "text"
    
    elif any(word in message for word in ['難過', '傷心', '憂鬱']):
        song, genre = get_music_by_mood("難過")
        return f"😔 心情不好嗎？這首歌也許能陪伴你：\n\n{song['emoji']} 《{song['title']}》\n🎤 {song['artist']}\n\n🎵 {song['youtube']}\n\n一切都會好起來的 💙", "text"
    
    elif any(word in message for word in ['生氣', '憤怒', '火大']):
        song, genre = get_music_by_mood("生氣")
        return f"😠 發洩一下情緒吧！\n\n{song['emoji']} 《{song['title']}》\n🎤 {song['artist']}\n\n🎵 {song['youtube']}\n\n讓音樂帶走負面情緒！🔥", "text"
    
    # 隨機音樂
    elif any(word in message for word in ['隨機', '隨便', '不知道聽什麼']):
        song = get_random_song()
        return f"🎲 隨機推薦：\n\n{song['emoji']} 《{song['title']}》\n🎤 {song['artist']}\n\n🎵 {song['youtube']}\n\n驚喜總是最棒的！🎁", "text"
    
    # 其他功能
    elif any(word in message for word in ['你好', 'hello', 'hi', '嗨']):
        return "🎵 哈囉！我是你的音樂小助手！\n\n想聽音樂嗎？試試說：\n• 「音樂」- 選擇音樂類型\n• 「開心」- 心情音樂推薦\n• 「隨機」- 隨機歌曲\n\n讓我們一起享受音樂吧！🎶", "text"
    
    elif any(word in message for word in ['幫助', 'help', '功能']):
        return """🎵 音樂機器人功能列表：

🎼 音樂推薦：
• 「音樂」→ 選擇音樂類型
• 「流行」「搖滾」「放鬆」「電音」

💭 心情音樂：
• 「開心」「難過」「生氣」
• 根據心情推薦適合的歌曲

🎲 其他功能：
• 「隨機」→ 隨機推薦
• 「時間」→ 查看現在時間
• 「笑話」→ 程式笑話

試試看吧！🎶""", "text"
    
    elif any(word in message for word in ['時間', 'time', '現在幾點']):
        now = datetime.now()
        return f"🕐 現在時間：{now.strftime('%Y-%m-%d %H:%M:%S')}\n\n要不要聽首歌配配時間？說「音樂」來選擇吧！🎵", "text"
    
    elif any(word in message for word in ['笑話', 'joke']):
        jokes = [
            "為什麼音樂家都很瘦？因為他們一直在減「音」！🎵😂",
            "什麼樂器最容易感冒？「薩克斯風」，因為它一直在吹！🎷🤧",
            "為什麼鋼琴家手指這麼靈活？因為他們會「彈」性工作！🎹✨",
            "DJ 最怕什麼？怕「混」不下去！🎧😱"
        ]
        return random.choice(jokes), "text"
    
    # 預設回應
    else:
        music_responses = [
            f"你說「{user_message}」讓我想到一首歌！說「隨機」讓我推薦給你 🎵",
            "想聽音樂嗎？說「音樂」我來幫你選！🎶",
            f"「{user_message}」...有趣！要不要聽首歌轉換心情？🎼",
            "我是音樂機器人！說「幫助」看看我能做什麼 🎵",
        ]
        return random.choice(music_responses), "text"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    reply_content, reply_type = get_smart_reply(user_message)
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        if reply_type == "template":
            # 發送模板訊息
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[reply_content]
                )
            )
        else:
            # 發送文字訊息
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_content)]
                )
            )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)