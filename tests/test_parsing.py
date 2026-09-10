"""測試輸入解析（不碰資料庫、不碰網路）。"""
from datetime import timedelta

import pytest

import app
from util import taiwan_now


@pytest.mark.parametrize(
    "text, expected",
    [
        ("支出 150 餐飲 午餐", ("expense", 150.0, "餐飲", "午餐")),
        ("收入 5000 薪水 月薪", ("income", 5000.0, "薪水", "月薪")),
        ("+50 咖啡 星巴克", ("expense", 50.0, "咖啡", "星巴克")),
        ("-3000 兼職 家教費", ("income", 3000.0, "兼職", "家教費")),
        ("支出 99 交通", ("expense", 99.0, "交通", "交通")),  # 沒填說明就用分類當說明
        ("花費 60 早餐", ("expense", 60.0, "早餐", "早餐")),   # 支援同義詞
    ],
)
def test_parse_ok(text, expected):
    r = app.parse_accounting_input(text)
    assert r is not None
    assert (r["type"], r["amount"], r["category"], r["description"]) == expected


@pytest.mark.parametrize(
    "text",
    ["隨便打字", "支出 abc 餐飲", "支出 -50 餐飲", "支出 0 餐飲", "帳單", "支出 100"],
)
def test_parse_reject(text):
    assert app.parse_accounting_input(text) is None


def test_parse_with_date():
    r = app.parse_accounting_input("+50 咖啡 星巴克 昨天")
    assert r["date"] == (taiwan_now() - timedelta(days=1)).strftime("%Y-%m-%d")
    assert r["description"] == "星巴克"  # 「昨天」被當日期抽走，不會混進說明


def test_parse_date_relative():
    assert app.parse_date("今天") == taiwan_now().strftime("%Y-%m-%d")
    assert app.parse_date("前天") == (taiwan_now() - timedelta(days=2)).strftime("%Y-%m-%d")


def test_parse_date_absolute():
    assert app.parse_date("2025-12-31") == "2025-12-31"
    assert app.parse_date("2025/12/31") == "2025-12-31"
    assert app.parse_date("亂寫") is None


@pytest.mark.parametrize(
    "text, days",
    [("帳單", None), ("今天帳單", 0), ("本週統計", 7), ("本月帳單", 30), ("近 5 天", 5)],
)
def test_parse_days(text, days):
    assert app.parse_days(text) == days
