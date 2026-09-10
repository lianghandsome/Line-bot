"""測試訊息處理與 Flask 路由（把整段流程串起來，但不呼叫 LINE API）。"""
import app

U = "U_handler"


def test_record_then_show_on_bill():
    r = app.handle_user_message("支出 150 餐飲 午餐", U)
    assert "已記錄" in r and "150" in r

    r = app.handle_user_message("帳單", U)
    assert "餐飲" in r and "午餐" in r


def test_summary_flow():
    app.handle_user_message("收入 5000 薪水 月薪", U)
    app.handle_user_message("支出 200 餐飲 晚餐", U)
    r = app.handle_user_message("統計", U)
    assert "總收入" in r and "5,000" in r
    assert "淨收支" in r


def test_delete_flow():
    app.handle_user_message("支出 100 餐飲 a", U)
    app.handle_user_message("支出 200 娛樂 b", U)
    assert "已刪除" in app.handle_user_message("刪除 2", U)
    assert "找不到" in app.handle_user_message("刪除 99", U)


def test_help_and_unknown():
    assert "使用說明" in app.handle_user_message("幫助", U)
    assert "看不懂" in app.handle_user_message("asdfgh", U)


def test_home_route():
    r = app.app.test_client().get("/")
    assert r.status_code == 200
    assert "記帳機器人" in r.get_data(as_text=True)



def test_callback_rejects_bad_signature():
    r = app.app.test_client().post(
        "/callback", data="{}", headers={"X-Line-Signature": "bad"}
    )
    assert r.status_code == 400
