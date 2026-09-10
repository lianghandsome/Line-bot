# config.py — 從環境變數讀取設定，不要把金鑰寫死在程式裡
import os

# 本機開發時，若有 .env 檔就自動載入（部署環境會直接用系統環境變數）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
