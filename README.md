# LINE 記帳機器人

用 LINE 聊天就能記帳的機器人。傳一句「支出 150 餐飲 午餐」就記一筆，隨時查帳單和收支統計。

- **後端**：Python / Flask webhook
- **訊息平台**：LINE Messaging API（`line-bot-sdk` v3）
- **資料庫**：PostgreSQL（部署環境）／SQLite（本機開發自動切換）
- **部署**：gunicorn + Procfile

## 功能

| 你傳的訊息 | 機器人做的事 |
|---|---|
| `支出 150 餐飲 午餐` | 記一筆支出 |
| `收入 5000 薪水 月薪` | 記一筆收入 |
| `+50 咖啡 星巴克 昨天` | 支出簡寫，可帶「今天／昨天／12-31」等日期 |
| `-3000 兼職 家教費` | 收入簡寫 |
| `帳單`、`今天帳單`、`本週帳單`、`本月帳單` | 列出記錄（最多 10 筆）|
| `統計`、`本月統計` | 總收入／總支出／淨收支／分類統計 |
| `刪除 3` | 刪除編號 3 的記錄 |
| `分類` | 查看常用分類 |
| `幫助` | 使用說明 |

每個 LINE 使用者的資料用 `user_id` 分開存，編號（`seq`）是各自獨立的流水號。

## 專案結構

```
app.py       Flask 路由、LINE webhook、訊息解析與回覆邏輯
db.py        資料存取層（PostgreSQL / SQLite 雙模式）
config.py    從環境變數讀取金鑰與 DATABASE_URL
util.py      台灣時區工具
Procfile     gunicorn 啟動指令（部署用）
tests/       pytest 測試
```

## 本機執行

不需要資料庫也不需要 LINE 憑證就能跑起來測試（會自動用本機 SQLite）。

```bash
pip install -r requirements.txt
python app.py
# 開 http://localhost:5000/ 可看到運行狀態
```

要實際收發 LINE 訊息：

```bash
cp .env.example .env      # 填入 LINE_CHANNEL_ACCESS_TOKEN / LINE_CHANNEL_SECRET
python app.py
ngrok http 5000           # 把 https 網址 + /callback 填到 LINE Developers 的 Webhook URL
```

## 測試

三個層次：

| 層次 | 怎麼做 | 需要什麼 |
|---|---|---|
| 邏輯測試 | `pip install -r requirements-dev.txt` 後 `pytest` | 什麼都不用，跑臨時 SQLite |
| 本機整合 | `python app.py` + `ngrok`，用手機傳訊息給 bot | LINE 憑證 |
| Webhook 驗證 | LINE Developers 後台 Webhook URL 旁的「Verify」按鈕 | 已部署的網址 |

`pytest` 涵蓋：輸入解析（`支出 100 餐飲`、日期、同義詞、各種錯誤輸入）、
資料庫增刪查、收支統計、訊息處理流程、Flask 路由、以及**「程式重啟後資料還在」**
（就是舊 JSON 版會失敗的地方）。

```bash
pytest -q          # 32 個測試
```

## 部署

全免費方案（Neon + Render + cron-job.org）的逐步教學見 [DEPLOY.md](DEPLOY.md)。
資料存在雲端 PostgreSQL，主機重啟／休眠都不會遺失。

## 開發過程中學到的

這是我第一次做 LINE bot，邊查官方文件邊做。資料儲存的方式改過三次：

1. **本機 JSON 檔** — 最快，但雲端主機每次重啟／休眠都會清空檔案系統，記錄會不見。
2. **SQLite** — 解決格式問題，但免費方案的磁碟一樣不持久。
3. **PostgreSQL（現在）** — 資料庫是獨立的持久化服務，重新部署也不會掉資料。

`db.py` 保留了 SQLite 模式，讓別人 clone 下來不用設定任何東西就能先跑起來看。
