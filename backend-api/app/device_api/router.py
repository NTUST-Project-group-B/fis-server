"""裝置 API(暫代版本，之後由 A 改寫)。

流程照圖 4:接收讀值 → 觸發規則評估 → 規則引擎把警報交給通知模組。

和圖 4 的差異(假版本先省略):
- 不驗證裝置金鑰
- 不寫入 `readings`、`device_status`
- 不觸發資料品質檢查
- 不回應最新設定(目標溫度與上下限)
"""

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.device_api.schemas import AlertOut, ReadingIn, ReadingResult
from app.notifier.base import Notifier
from app.notifier.discord import DiscordWebhookNotifier
from app.rules_engine.engine import ReadingInput, evaluate_and_notify

router = APIRouter(prefix="/api/v1/device", tags=["裝置 API(暫代)"])


def get_notifier() -> Notifier:
    # 測試時用 app.dependency_overrides 換掉，就不用真的 webhook
    url = get_settings().discord_webhook_url.get_secret_value()
    return DiscordWebhookNotifier(url)


@router.post("/readings", response_model=ReadingResult)
async def upload_reading(body: ReadingIn, notifier: Notifier = Depends(get_notifier)) -> ReadingResult:
    reading = ReadingInput(device_id=body.device_id, temperature_c=body.temperature_c, ph=body.ph)
    alerts, errors = await evaluate_and_notify(reading, notifier)
    return ReadingResult(
        alerts=[AlertOut(rule_id=a.rule_id, severity=a.severity, title=a.title) for a in alerts],
        notify_errors=errors,
    )
