# util.py — 共用小工具
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
    TAIWAN_TZ = ZoneInfo("Asia/Taipei")
except Exception:  # 少數環境沒有 tzdata 時退回固定 +8 時區
    from datetime import timedelta, timezone
    TAIWAN_TZ = timezone(timedelta(hours=8))


def taiwan_now():
    """回傳台灣當前時間（帶時區資訊）"""
    return datetime.now(TAIWAN_TZ)


def today_str():
    """回傳台灣今天日期，格式 YYYY-MM-DD"""
    return taiwan_now().strftime("%Y-%m-%d")
