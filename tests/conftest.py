"""測試共用設定：一律用臨時 SQLite，絕不連到 PostgreSQL。"""
import os
import sys
import tempfile

import pytest

# 這兩行必須在 import 專案任何模組「之前」執行
os.environ["DATABASE_URL"] = ""  # 強制走 SQLite，就算你 .env 填了真的資料庫也不會被測試碰到
_TEST_DB = os.path.join(tempfile.gettempdir(), "linebot_pytest.db")
os.environ["SQLITE_PATH"] = _TEST_DB

# 讓 tests/ 內的檔案能 import 到專案根目錄的 app.py / db.py …
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def fresh_db():
    """每個測試開始前都給一個乾淨的資料庫。"""
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
    import db
    db.init_db()
    yield
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
