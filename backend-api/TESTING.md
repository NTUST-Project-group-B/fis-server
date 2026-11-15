# 執行與測試步驟

本文件說明如何在自己的電腦上執行後端，並確認每個功能正常。

- 指令以 Windows PowerShell 為例。macOS 和 Linux 的差異寫在相關步驟裡。
- API 格式未定。格式變更時，本文件的範例也要跟著改。

## 需要的工具

| 工具 | 用途 | 確認指令 |
|---|---|---|
| uv | 管理 Python 和套件 | `uv --version` |
| Python 3.13 以上 | 執行程式。如果電腦沒有，uv 會自動下載 | `uv run python --version` |
| Discord 頻道的 webhook 網址 | 接收警報。只有步驟 3 和步驟 8 需要 | 無 |

如果 `uv` 不是可辨識的指令，先依照 uv 官方文件安裝:https://docs.astral.sh/uv/

## 一、準備環境(第一次才需要)

### 步驟 1:進入 `backend-api/`

```powershell
cd fis-server\backend-api
```

之後所有指令都在這個資料夾執行。

### 步驟 2:安裝套件

```powershell
uv sync
```

uv 會讀 `pyproject.toml` 和 `uv.lock`,在 `.venv/` 裡安裝固定版本的套件。

### 步驟 3:建立 `.env`

> 警告:`.env` 存放 webhook 網址。不要把 `.env` 傳給別人。`.gitignore` 已經排除 `.env`,不要強制提交它。
> 理由:任何人拿到 webhook 網址，都可以發訊息到你的頻道。

1. 複製範本:

   ```powershell
   Copy-Item .env.example .env
   ```

   macOS 和 Linux 改用 `cp .env.example .env`。

2. 在 Discord 取得 webhook 網址:
   1. 開啟要接收警報的頻道。
   2. 選「編輯頻道」→「整合」→「Webhook」→「新增 Webhook」。
   3. 按「複製 Webhook 網址」。
3. 打開 `.env`,把網址貼在 `DISCORD_WEBHOOK_URL=` 後面。

如果只要執行步驟 4 的自動測試，可以跳過這一步。理由：自動測試用假的 webhook 網址，不讀 `.env`。

## 二、執行自動測試

### 步驟 4:執行測試

```powershell
uv run pytest
```

預期結果：最後一行顯示 `7 passed`。

- 畫面會出現 1 個 `StarletteDeprecationWarning`。這是套件版本的提示，不影響結果。
- 如果有測試失敗，畫面會顯示 `FAILED` 和失敗原因。

自動測試不會真的連到 Discord。每個測試檢查的內容如下:

| 測試名稱 | 檢查內容 |
|---|---|
| `test_normal_reading_no_alert` | 水溫 25°C、pH 7.4 時，規則引擎不產生警報 |
| `test_high_temp_alert` | 水溫 30.5°C 時，規則引擎只產生「水溫過高」警報 |
| `test_evaluate_is_reproducible` | 同一筆讀值判斷兩次，結果相同。水溫 20°C、pH 6.5 時產生 2 個警報 |
| `test_alert_is_sent_to_discord` | 上傳異常讀值後，通知模組送出 1 則 Discord 訊息，標題正確 |
| `test_no_alert_no_discord_call` | 上傳正常讀值後，通知模組不送任何訊息 |
| `test_rate_limit_retry` | Discord 回 429(請求太頻繁)時，通知模組等待後重送 1 次 |
| `test_discord_failure_does_not_fail_upload` | Discord 回 500 時，讀值上傳仍然成功，錯誤寫在 `notify_errors` |

## 三、啟動伺服器並手動測試

### 步驟 5:啟動伺服器

```powershell
uv run uvicorn app.main:app --reload
```

預期結果：畫面顯示 `Uvicorn running on http://127.0.0.1:8000`。

- `--reload` 的意思：修改程式後，伺服器自動重新啟動。
- 讓這個視窗保持開著。開另一個終端機執行步驟 6 到步驟 9,同樣先進入 `backend-api/`。

### 步驟 6:確認伺服器正在執行

用瀏覽器開啟 http://127.0.0.1:8000/health

預期結果:`{"status":"ok"}`

### 步驟 7:送一筆正常讀值

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/device/readings -ContentType 'application/json' -Body '{"device_id": "tank-01", "temperature_c": 25.0}' | ConvertTo-Json -Depth 5
```

預期結果:`alerts` 和 `notify_errors` 都是空清單。Discord 頻道不會收到訊息。

### 步驟 8:送一筆異常讀值

> 警告：這一步會發 2 則訊息到 `.env` 設定的 Discord 頻道。

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/device/readings -ContentType 'application/json' -Body '{"device_id": "tank-01", "temperature_c": 30.5, "ph": 6.5}' | ConvertTo-Json -Depth 5
```

macOS 和 Linux 改用:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/device/readings -H 'Content-Type: application/json' -d '{"device_id": "tank-01", "temperature_c": 30.5, "ph": 6.5}'
```

預期結果:

- `alerts` 有 2 個警報:`FAKE-TEMP-HIGH`(水溫過高)和 `FAKE-PH-RANGE`(pH 超出範圍)。
- `notify_errors` 是空清單。
- Discord 頻道收到 2 則訊息：紅色色條的「水溫過高」和黃色色條的「pH 超出範圍」。

### 步驟 9:送一筆格式錯誤的讀值

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/device/readings -ContentType 'application/json' -Body '{"device_id": "tank-01", "temperature_c": "abc"}'
```

預期結果:PowerShell 顯示紅色錯誤訊息，裡面有 `422`。這表示裝置 API 拒絕了格式錯誤的資料，是正確的行為。

### 用網頁代替步驟 7 到步驟 9

1. 用瀏覽器開啟 http://127.0.0.1:8000/docs
2. 展開 `POST /api/v1/device/readings`。
3. 按「Try it out」。
4. 修改 Request body 的數值。
5. 按「Execute」,在下方看回應。

### 步驟 10:停止伺服器

在步驟 5 的視窗按 `Ctrl+C`。

## 常見問題

| 現象 | 原因 | 處理 |
|---|---|---|
| `/health` 正常，但上傳讀值回 `500` | 沒有 `.env`,或沒有填 `DISCORD_WEBHOOK_URL` | 做步驟 3,再重新啟動伺服器 |
| `notify_errors` 出現 `All connection attempts failed` | 連不到 webhook 網址 | 檢查網路和網址 |
| `notify_errors` 出現 `Discord 回應 401` 或 `404` | webhook 網址錯誤，或 webhook 已被刪除 | 重新複製網址，再重新啟動伺服器 |
| 啟動時顯示 port 已被使用 | 另一個伺服器還在執行 | 關掉另一個伺服器，或在步驟 5 的指令後面加 `--port 8001` |
