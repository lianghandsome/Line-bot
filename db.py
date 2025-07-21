import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    'dbname': 'linebot_db_tgex',
    'user': 'linebot_db_tgex_user',
    'password': 'jReUNI2Qtis6qCzVAV0DT8wPb4mjhGPJ',
    'host': 'dpg-d1vabq6r433s73fgr750-a',
    'port': 5432
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            item TEXT,
            amount INT,
            timestamp TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def add_record(user_id, item, amount):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO records (user_id, item, amount)
        VALUES (%s, %s, %s);
    """, (user_id, item, amount))
    conn.commit()
    cur.close()
    conn.close()

def get_weekly_records(user_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT item, amount, timestamp
        FROM records
        WHERE user_id = %s AND timestamp >= NOW() - INTERVAL '7 days'
        ORDER BY timestamp DESC;
    """, (user_id,))
    records = cur.fetchall()
    cur.close()
    conn.close()
    return records
