"""測試資料存取層。"""
import importlib

import db

U = "U_test"


def test_add_returns_incrementing_seq():
    assert db.add_record(U, "expense", 150, "餐飲", "午餐") == 1
    assert db.add_record(U, "income", 5000, "薪水", "月薪") == 2


def test_per_user_isolation():
    db.add_record("userA", "expense", 100, "餐飲", "x")
    db.add_record("userB", "expense", 200, "交通", "y")
    a = db.get_records("userA")
    assert len(a) == 1 and a[0]["amount"] == 100
    # userB 的第一筆也應該是自己的 seq 1
    assert db.get_records("userB")[0]["seq"] == 1


def test_delete():
    db.add_record(U, "expense", 100, "餐飲", "a")
    s2 = db.add_record(U, "expense", 200, "娛樂", "b")
    assert db.delete_record(U, s2) is True
    assert db.delete_record(U, 999) is False
    left = db.get_records(U)
    assert len(left) == 1 and left[0]["amount"] == 100


def test_seq_not_reused_while_records_exist():
    db.add_record(U, "expense", 10, "a", "a")        # seq 1
    s2 = db.add_record(U, "expense", 20, "b", "b")   # seq 2
    db.add_record(U, "expense", 30, "c", "c")        # seq 3
    db.delete_record(U, s2)                           # 刪掉中間那筆
    s4 = db.add_record(U, "expense", 40, "d", "d")
    assert s4 == 4                                    # 不回收已刪的 2、也不撞現有編號
    assert sorted(r["seq"] for r in db.get_records(U)) == [1, 3, 4]


def test_summary():
    db.add_record(U, "income", 5000, "薪水", "x")
    db.add_record(U, "expense", 150, "餐飲", "y")
    db.add_record(U, "expense", 50, "餐飲", "z")
    s = db.get_summary(U)
    assert s["total_income"] == 5000
    assert s["total_expense"] == 200
    assert s["balance"] == 4800
    assert s["categories"]["餐飲"]["expense"] == 200
    assert s["record_count"] == 3


def test_data_survives_restart():
    """之前 JSON 版就是死在這裡：伺服器一重啟資料就沒了。"""
    db.add_record(U, "expense", 123, "測試", "persist")
    importlib.reload(db)          # 模擬重新啟動程式
    db.init_db()
    assert any(r["amount"] == 123 for r in db.get_records(U))
