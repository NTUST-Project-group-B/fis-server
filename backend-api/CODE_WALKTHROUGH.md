# 假流程程式導讀

> 學習用筆記，內容對應 2026-11-15 的假流程版本，之後不隨程式更新。

## 整體流程：一筆讀值從進來到發出 Discord 警報

假設 ESP32 送來一筆讀值:`{"device_id": "tank-01", "temperature_c": 30.5}`

```
ESP32 ──POST /api/v1/device/readings──▶ main.py(把請求交給 device_api)
                                          │
                                          ▼
                             device_api/router.py   收資料、檢查格式
                                          │
                                          ▼
                             rules_engine/engine.py  判斷 30.5 > 28 → 產生「水溫過高」警報
                                          │
                                          ▼
                             notifier/discord.py     把警報排成 Discord 訊息送出
                                          │
                                          ▼
                                      Discord 頻道
```

最後 ESP32 收到的回應會是：「有哪些警報」和「通知有沒有送失敗」。

---

## 1. `app/main.py`:程式進入點

```python
app = FastAPI(title="智慧魚缸後端")       # 建立網頁伺服器物件
app.include_router(device_router)         # 掛上裝置 API 的所有網址

@app.get("/health")                       # 有人 GET /health 時
async def health():
    return {"status": "ok"}               # 回「我還活著」
```

- `FastAPI` 是 Python 的網頁框架。它負責收 HTTP 請求，再交給對應的函式處理。
- `@app.get("/health")` 這種寫法叫**裝飾器**。意思是「把底下這個函式綁到這個網址」。
- `include_router` 的作用是把別的檔案定義的網址掛進來。之後應用 API 也用同樣方法掛上去。

## 2. `app/device_api/`:裝置 API(收 ESP32 的資料)

分兩個檔案。

### `schemas.py`:規定資料長什麼樣子

```python
class ReadingIn(BaseModel):
    device_id: str = Field(min_length=1)   # 必填，不能是空字串
    temperature_c: float                   # 必填，要是數字
    ph: float | None = None                # 選填，沒給就是 None
```

`BaseModel` 來自 Pydantic 套件。它會**自動檢查**送進來的 JSON。例如 `temperature_c` 送了 `"abc"`,FastAPI 會直接回 422 錯誤，不會進到程式裡。`ReadingResult` 規定回應的格式。

### `router.py`:處理請求

```python
router = APIRouter(prefix="/api/v1/device")   # 這個檔案的網址都以這段開頭

@router.post("/readings")                     # 完整網址:POST /api/v1/device/readings
async def upload_reading(body: ReadingIn, notifier: Notifier = Depends(get_notifier)):
    reading = ReadingInput(...)                                    # 1. 轉成規則引擎要的格式
    alerts, errors = await evaluate_and_notify(reading, notifier)  # 2. 交給規則引擎
    return ReadingResult(alerts=..., notify_errors=errors)         # 3. 回傳結果
```

兩個比較難懂的地方:

- **`body: ReadingIn`**:FastAPI 看到這個型別，就會把 JSON 轉成 `ReadingIn` 物件並檢查格式。
- **`Depends(get_notifier)`**:這叫**依賴注入**。FastAPI 會先呼叫 `get_notifier()` 拿到一個 Discord 通知器，再傳進來。好處是：測試時可以換成假的通知器，不用真的發 Discord。

## 3. `app/rules_engine/engine.py`:規則引擎

裡面分三層:

| 函式 | 做什麼 | 會不會連網路 |
|---|---|---|
| `evaluate()` | 只做判斷，回傳警報清單 | 不會 |
| `to_notification()` | 把「警報」轉成「通知」格式 | 不會 |
| `evaluate_and_notify()` | 呼叫上面兩個，再交給通知模組送出 | 會 |

### `evaluate()`:核心判斷

其實就是一串 `if`:

```python
if r.temperature_c > 28:        # 規則 1:水溫過高
    alerts.append(Alert(rule_id="FAKE-TEMP-HIGH", severity=CRITICAL, ...))
elif r.temperature_c < 22:      # 規則 2:水溫過低
    alerts.append(Alert(rule_id="FAKE-TEMP-LOW", ...))

if r.ph is not None and not (7.0 <= r.ph <= 8.0):   # 規則 3:pH 超出範圍(有給 pH 才檢查)
    alerts.append(Alert(rule_id="FAKE-PH-RANGE", severity=WARNING, ...))
```

每個 `Alert` 都帶四項內容：判讀、下一步、依據、嚴重度。這四項來自圖 4 第 12 步。門檻 22–28°C、pH 7.0–8.0 是暫定值(未定案)。

`evaluate()` 單獨拆出來的理由：計畫書規定「規則引擎結果必須可重現」。`evaluate()` 不碰網路和資料庫，所以同一筆讀值一定得到同樣的警報，也容易寫測試。

### `evaluate_and_notify()`:送出通知

```python
for a in alerts:
    try:
        await notifier.send(...)
    except Exception as e:
        errors.append(...)      # 送失敗只記下來，不讓整個請求失敗
```

理由:Discord 掛掉時，讀值上傳本身不應該跟著失敗。

### `@dataclass(frozen=True)`

這是 Python 定義「純資料物件」的簡寫，會自動產生建構函式。`frozen=True` 表示建立後不能修改內容。

## 4. `app/notifier/`:通知模組

### `base.py`:定義「通知」的共同格式

```python
class Severity(StrEnum):        # 嚴重度只有三種:info / warning / critical
class Notification:             # 一則通知的內容：標題、嚴重度、判讀、下一步、依據
class Notifier(Protocol):       # 「通知器」只要有 send() 方法就算
    async def send(self, notification): ...
```

`Protocol` 只規定通知器要有哪些方法，不管它內部怎麼送。規則引擎只認 `Notifier`,不知道背後是 Discord。以後要改成 LINE 或 Email,只要新寫一個有 `send()` 的類別，規則引擎不用改。

### `discord.py`:Discord 的實作

- `build_payload()`:把 `Notification` 排成 Discord 的 embed 格式。依嚴重度加上不同顏色的色條(紅、黃、藍)。每個欄位截到 1024 字，因為這是 Discord 的上限。
- `send()`:用 `httpx` 把 JSON POST 到 webhook 網址。
  - 如果 Discord 回 429(請求太頻繁),就等它指定的秒數再重送一次。
  - 如果成功(Discord 回 204),就結束。
  - 其他情況丟出 `DiscordError`。錯誤訊息裡刻意不放 webhook 網址，避免外洩。

Webhook 網址存在 `.env` 檔，由 `app/config.py` 讀進來。網址用 `SecretStr` 包住，所以印出來只會顯示 `**********`。
