"""資料存取層（SQLite）。

seq 是「每個使用者自己的流水號」，使用者在 LINE 看到、刪除時用的就是它。
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import timedelta

from util import taiwan_now

_DB_PATH = os.getenv("SQLITE_PATH", "accounting.db")


def get_connection():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _cursor(commit=False):
    conn = get_connection()
    cur = conn.cursor()
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
    with _cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                user_id     TEXT    NOT NULL,
                seq         INTEGER NOT NULL,
                type        TEXT    NOT NULL,
                amount      REAL    NOT NULL,
                category    TEXT    NOT NULL,
                description TEXT,
                record_date TEXT    NOT NULL,
                created_at  TEXT    NOT NULL,
                PRIMARY KEY (user_id, seq)
            )
            """
        )


def add_record(user_id, record_type, amount, category, description, record_date=None):
    record_date = record_date or taiwan_now().strftime("%Y-%m-%d")
    created_at = taiwan_now().isoformat(timespec="seconds")
    with _cursor(commit=True) as cur:
        cur.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM records WHERE user_id = ?",
            (user_id,),
        )
        next_seq = cur.fetchone()["next_seq"] or 1
        cur.execute(
            """
            INSERT INTO records
                (user_id, seq, type, amount, category, description, record_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, next_seq, record_type, amount, category, description,
             record_date, created_at),
        )
        return next_seq


def get_records(user_id, days=None):
    sql = "SELECT * FROM records WHERE user_id = ?"
    params = [user_id]
    if days is not None:
        cutoff = (taiwan_now() - timedelta(days=days)).strftime("%Y-%m-%d")
        sql += " AND record_date >= ?"
        params.append(cutoff)
    sql += " ORDER BY record_date DESC, created_at DESC"
    with _cursor() as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
