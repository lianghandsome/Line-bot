"""資料存取層。

有設定 DATABASE_URL（例如部署到 Render 時）就連 PostgreSQL；
沒設定時自動改用本機 SQLite 檔，方便在自己電腦上開發測試。

之前的版本把資料寫在伺服器的 accounting_data.json，
雲端主機每次重啟／休眠都會清空檔案系統，所以記錄會不見；
改用資料庫之後就會持久保存。
"""
from contextlib import contextmanager
from datetime import timedelta

from config import DATABASE_URL
from util import taiwan_now

_USE_PG = bool(DATABASE_URL)
BACKEND = "PostgreSQL" if _USE_PG else "SQLite（本機）"

if _USE_PG:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    _PH = "%s"          # PostgreSQL 的參數佔位符
else:
    import os
    import sqlite3
    _PH = "?"           # SQLite 的參數佔位符
    _SQLITE_PATH = os.getenv("SQLITE_PATH", "accounting.db")


def get_connection():
    if _USE_PG:
        return psycopg2.connect(DATABASE_URL)
    conn = sqlite3.connect(_SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _cursor(commit=False):
    """統一處理連線、cursor、commit/rollback、關閉。"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _USE_PG else conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def init_db():
    """建立資料表（欄位型別刻意選用 PostgreSQL 和 SQLite 都支援的寫法）。

    seq 是「每個使用者自己的流水號」，使用者在 LINE 看到的編號就是它，
    刪除時也用這個編號；用 (user_id, seq) 當複合主鍵。
    """
    with _cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                user_id     TEXT    NOT NULL,
                seq         INTEGER NOT NULL,
                type        TEXT    NOT NULL,   -- 'income' 或 'expense'
                amount      REAL    NOT NULL,
                category    TEXT    NOT NULL,
                description TEXT,
                record_date TEXT    NOT NULL,   -- YYYY-MM-DD
                created_at  TEXT    NOT NULL,   -- ISO 8601
                PRIMARY KEY (user_id, seq)
            )
            """
        )


def add_record(user_id, record_type, amount, category, description, record_date=None):
    """新增一筆記錄，回傳這位使用者的流水號 seq。"""
    record_date = record_date or taiwan_now().strftime("%Y-%m-%d")
    created_at = taiwan_now().isoformat(timespec="seconds")
    with _cursor(commit=True) as cur:
        cur.execute(
            f"SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM records WHERE user_id = {_PH}",
            (user_id,),
        )
        next_seq = cur.fetchone()["next_seq"] or 1
        cur.execute(
            f"""
            INSERT INTO records
                (user_id, seq, type, amount, category, description, record_date, created_at)
            VALUES ({_PH}, {_PH}, {_PH}, {_PH}, {_PH}, {_PH}, {_PH}, {_PH})
            """,
            (user_id, next_seq, record_type, amount, category, description,
             record_date, created_at),
        )
        return next_seq


def get_records(user_id, days=None):
    """取得使用者的記錄，新到舊排序。days 為 None 代表全部。"""
    sql = f"SELECT * FROM records WHERE user_id = {_PH}"
    params = [user_id]
    if days is not None:
        cutoff = (taiwan_now() - timedelta(days=days)).strftime("%Y-%m-%d")
        sql += f" AND record_date >= {_PH}"
        params.append(cutoff)
    sql += " ORDER BY record_date DESC, created_at DESC"
    with _cursor() as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def get_records_on(user_id, date_str):
    """取得使用者在指定某一天的記錄。"""
    with _cursor() as cur:
        cur.execute(
            f"SELECT * FROM records WHERE user_id = {_PH} AND record_date = {_PH} "
            f"ORDER BY created_at DESC",
            (user_id, date_str),
        )
        return [dict(row) for row in cur.fetchall()]


def delete_record(user_id, seq):
    """刪除指定流水號的記錄，回傳是否有刪到。"""
    with _cursor(commit=True) as cur:
        cur.execute(
            f"DELETE FROM records WHERE user_id = {_PH} AND seq = {_PH}",
            (user_id, seq),
        )
        return cur.rowcount > 0


def get_summary(user_id, days=None):
    """收支統計：總收入、總支出、淨額、各分類金額、筆數。"""
    records = get_records(user_id, days)
    total_income = sum(r["amount"] for r in records if r["type"] == "income")
    total_expense = sum(r["amount"] for r in records if r["type"] == "expense")

    categories = {}
    for r in records:
        bucket = categories.setdefault(r["category"], {"income": 0.0, "expense": 0.0})
        bucket[r["type"]] += r["amount"]

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": total_income - total_expense,
        "categories": categories,
        "record_count": len(records),
    }


def count_all_records():
    """全體記錄總數（給首頁狀態頁用）。"""
    with _cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM records")
        return cur.fetchone()["n"]
