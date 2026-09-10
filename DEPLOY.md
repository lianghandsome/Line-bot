# 部署（全免費，資料永久保存）

三個免費服務，都不用信用卡：

| 角色 | 服務 | 免費額度 |
|---|---|---|
| 資料庫 | [Neon](https://neon.tech) PostgreSQL | 0.5 GB（約 500 萬筆記錄），專案不會過期 |
| 跑 bot | [Render](https://render.com) Web Service | 750 小時/月（夠一個服務 24 小時跑） |
| 防休眠 | [cron-job.org](https://cron-job.org) | 每分鐘可觸發 |

> 資料存在 Neon，Render 重啟或休眠都不影響 → **記過的東西不會不見**。

---

## 1. Neon：建資料庫

1. 開 [neon.tech](https://neon.tech) → **Sign up** → 選 **Continue with GitHub**
2. 第一次登入會要你建專案（**Create project**）：
   - Project name：`line-bot`（隨便）
   - Postgres version：預設就好
   - Region：**選跟你 Render 服務一樣的**（Render 在 Oregon 就選 `AWS US West (Oregon)`；
     在 Singapore 就選 `AWS Asia Pacific (Singapore)`）。兩邊不同區只是每次查詢慢個 0.5～1 秒，
     不會壞，但能一致最好。
   - 按 **Create project**
3. 建好後會跳出 / 或在專案首頁右邊有一個 **Connection string** 區塊：
   - 確認下拉選單選的是你的 database（預設 `neondb`）
   - 點眼睛圖示顯示密碼，按 **Copy snippet**
   - 複製到的東西長這樣：
     ```
     postgresql://neondb_owner:XXXXXXXX@ep-cool-name-12345.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
     ```
   - 貼到記事本，等下 Render 要用。**這串就是 `DATABASE_URL`。**

## 2. Render：部署 bot（用 Blueprint，最少手動設定）

repo 裡有一個 `render.yaml`，Render 會照它自動把服務建好，你只要填 3 個祕密值。

1. 開 [render.com](https://render.com) → **Get Started** → 用 **GitHub** 登入（免費方案不用信用卡）
2. 右上角 **New +** → 選 **Blueprint**
3. 第一次要授權 GitHub：**Configure account** → 選 **Only select repositories** → 勾 `lianghandsome/Line-bot` → **Install & Authorize**
4. 回 Render，選 `lianghandsome/Line-bot` → **Connect**
5. Render 讀到 `render.yaml`，顯示要建一個 web service `line-bot`。下面會要你填三個值：

   | 欄位 | 貼什麼 |
   |---|---|
   | `LINE_CHANNEL_ACCESS_TOKEN` | LINE 後台重發的 token（很長）|
   | `LINE_CHANNEL_SECRET` | LINE 後台重發的 secret（32 碼）|
   | `DATABASE_URL` | 步驟 1 從 Neon 複製的 `postgresql://...` 整串 |

   （前後不要有多餘空白）
6. 點 **Apply** → 進 Logs 看它跑，最後出現 `==> Your service is live 🎉`
7. 上方會有網址，例如 `https://line-bot-xxxx.onrender.com` → **複製起來**
8. 瀏覽器開 `https://line-bot-xxxx.onrender.com/`，應該看到：
   ```
   💰 記帳機器人運行中
   資料庫：PostgreSQL          ← 有這行代表 DATABASE_URL 正確
   總記錄數：0 筆
   ```
   - 寫 **SQLite（本機）** → `DATABASE_URL` 沒吃到 → Render 服務頁 → **Environment** 檢查
   - **Exited with status 1** → 看 Logs 最後幾行，多半是 Neon 字串貼錯

> `render.yaml` 裡 `region: oregon`。要換區的話改這行、再 `git push`，Neon 也選一樣的區。

## 3. LINE：接上 webhook

1. [LINE Developers](https://developers.line.biz/console/) → 選你的 channel → **Messaging API** 分頁
2. 找到 **Webhook settings**：
   - **Webhook URL** 填 `https://line-bot-xxxx.onrender.com/callback`（換成你的 Render 網址，尾巴一定要 `/callback`）→ **Update**
   - **Use webhook** 開關打開
   - 按 **Verify** → 出現 **Success** 就對了
3. 往下 **LINE Official Account features** → **Auto-reply messages** 點 **Edit**，
   把「自動回應訊息」關掉（不然你每傳一句，bot 會多回一句官方罐頭訊息）
4. 加自己的 bot 好友：同一頁最上面有 **Bot basic ID** 和 **QR code**，用手機掃

## 4. cron-job.org：讓 Render 不要睡

Render 免費版閒置 **15 分鐘**沒人連就休眠，休眠時剛好有訊息進來會被漏掉。
（Neon 也會休眠，但它 2 秒就醒，頂多第一則訊息慢一點，不會掉資料，不用特別管。）

1. 註冊 [cron-job.org](https://cron-job.org)（免費，只要 email）
2. Console → **Create cronjob**
   - Title：`keep line-bot awake`
   - URL：`https://line-bot-7cot.onrender.com/`（用你的網址，結尾 `/`）
   - Schedule：**Every 5 minutes**（`*/5`）
3. **Create** 儲存
4. 驗證：點進這個 job → 看 **History**，每 5 分鐘一筆、狀態 200（綠色）就對了

戳 `/` 這個路徑會順便查一次資料庫，所以 Render 和 Neon 都會保持清醒。

---

## 這樣是否真的一直免費、不會掉資料？

| | 免費額度 | 這個 bot 實際用量 |
|---|---|---|
| Render | 750 執行小時/月（一個服務跑滿整月約 744 小時）| 剛好夠 **一個** 服務 24 小時跑。**別再開第二個免費 web service**，會超額被停 |
| Neon | 0.5 GB 儲存 + 每月一定額度的運算時間 | 一筆記錄約 100 bytes；自動休眠讓運算用量很低。用不完 |
| cron-job.org | 一個 job 每分鐘可觸發 | 每 5 分鐘一次，綽綽有餘 |

資料放在 Neon，**Render 休眠、重新部署、甚至整個砍掉重建都不影響**——只要 `DATABASE_URL` 還指向同一個 Neon 資料庫，記錄都在。

## 完成後

手機加 bot 好友（LINE 後台 Messaging API 頁有 QR code），傳「支出 100 餐飲 午餐」試試。
再開一次 Render 的網址 `/`，「總記錄數」應該變成 1。

之後要改程式，`git push` 上去 Render 會自動重新部署（約 2 分鐘），Neon 裡的資料不受影響。

## 驗證資料真的不會不見

1. 記一筆帳
2. Render → 你的服務 → 右上 **Manual Deploy** → **Deploy latest commit**（強制重啟一次）
3. 等它 live 後，傳「帳單」給 bot → 剛剛那筆**還在** = 成功
4. 想直接看資料：Neon Console → 你的專案 → **SQL Editor** → 貼 `SELECT * FROM records;` → Run

## 更新環境變數（例如又換了金鑰）

Render → 你的服務 → 左邊 **Environment** → 改完按 Save，會自動重新部署。不用動程式碼。

---

## 常見問題

| 症狀 | 原因 / 解法 |
|---|---|
| Render 部署卡在 build 很久後失敗 | 通常是 `psycopg2-binary` 或 Python 版本問題。到 Environment 加 `PYTHON_VERSION` = `3.12.7` 再 Manual Deploy |
| Logs 出現 `No open ports detected` | Start Command 沒有 `--bind 0.0.0.0:$PORT`，補上去 |
| Logs 出現 `Exited with status 1` + `OperationalError` | `DATABASE_URL` 貼錯。回 Neon 重新 Copy snippet，整串換掉 |
| 網址 `/` 顯示「資料庫：SQLite（本機）」 | `DATABASE_URL` 這個環境變數沒設或名字打錯 |
| LINE 按 Verify 失敗 | Webhook URL 尾巴要有 `/callback`；Render 服務要是 live 狀態（先開網址確認）|
| bot 已讀不回 | ①「Use webhook」沒開 ②`LINE_CHANNEL_SECRET` 或 `LINE_CHANNEL_ACCESS_TOKEN` 貼錯 ③ 看 Render Logs 有沒有錯誤 |
| 傳訊息偶爾要等很久才回 | Render / Neon 剛從休眠喚醒。確認 cron-job.org 的定時任務有在跑（它的後台看 execution history 應該每 5 分鐘一筆綠色）|
| 第一次傳的訊息沒被記到 | 同上，主機在冷啟動。cron-job.org 設好之後就不會了 |

## 看 Logs

Render → 你的服務 → 左邊 **Logs**。這裡會即時顯示每則收到的訊息和錯誤，debug 都看這。
