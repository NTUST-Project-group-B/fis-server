"""規則引擎(假版本)。

目前規則寫死在程式裡。正式版要讀 `rules` 資料表，但 rules 的條件格式未定案(v2 第 15 節)。

分成兩個函式:
- evaluate():純函式，不碰網路和資料庫。相同輸入一定得到相同結果(計畫書:結果必須可重現)。
- evaluate_and_notify():呼叫 evaluate(),再把警報交給通知模組(圖 4 第 12 步)。

尚未實作(圖 4):讀取品質旗標、事件、開缸設定;寫入 `advice_log`。
"""

from dataclasses import dataclass

from app.notifier.base import Notification, Notifier, Severity


@dataclass(frozen=True)
class ReadingInput:
    device_id: str
    temperature_c: float
    ph: float | None = None


@dataclass(frozen=True)
class Alert:
    rule_id: str
    severity: Severity
    title: str
    interpretation: str
    next_step: str
    basis: str


# 暫定門檻(未定案)。
# 來源:note/compass_artifact_...md 第 43 行，孔雀魚適溫 22–28°C、pH 7.0–8.0(多個來源的保守交集)。
TEMP_MIN_C = 22.0
TEMP_MAX_C = 28.0
PH_MIN = 7.0
PH_MAX = 8.0
_BASIS = "孔雀魚適溫 22–28°C、pH 7.0–8.0(暫定門檻，未定案)"


def evaluate(r: ReadingInput) -> list[Alert]:
    alerts: list[Alert] = []

    if r.temperature_c > TEMP_MAX_C:
        alerts.append(Alert(
            rule_id="FAKE-TEMP-HIGH",
            severity=Severity.CRITICAL,
            title="水溫過高",
            interpretation=f"水溫 {r.temperature_c:.1f}°C,高於上限 {TEMP_MAX_C:.0f}°C。",
            next_step="確認加熱棒是否持續加熱。必要時拔除加熱棒電源並開風扇。",
            basis=_BASIS,
        ))
    elif r.temperature_c < TEMP_MIN_C:
        alerts.append(Alert(
            rule_id="FAKE-TEMP-LOW",
            severity=Severity.CRITICAL,
            title="水溫過低",
            interpretation=f"水溫 {r.temperature_c:.1f}°C,低於下限 {TEMP_MIN_C:.0f}°C。",
            next_step="確認加熱棒是否通電、是否故障。",
            basis=_BASIS,
        ))

    if r.ph is not None and not (PH_MIN <= r.ph <= PH_MAX):
        alerts.append(Alert(
            rule_id="FAKE-PH-RANGE",
            severity=Severity.WARNING,
            title="pH 超出範圍",
            interpretation=f"pH {r.ph:.2f},不在 {PH_MIN}–{PH_MAX} 之間。",
            next_step="先用試劑確認 pH 讀值。讀值正確時再考慮換水。",
            basis=_BASIS,
        ))

    return alerts


def to_notification(alert: Alert, device_id: str) -> Notification:
    return Notification(
        title=alert.title,
        severity=alert.severity,
        interpretation=alert.interpretation,
        next_step=alert.next_step,
        basis=alert.basis,
        source_id=alert.rule_id,
        extra={"裝置": device_id, "規則": alert.rule_id},
    )


async def evaluate_and_notify(r: ReadingInput, notifier: Notifier) -> tuple[list[Alert], list[str]]:
    """回傳 (警報清單, 通知失敗訊息清單)。

    通知失敗不往外丟例外：送 Discord 失敗不應該讓讀值上傳失敗。
    """
    alerts = evaluate(r)
    errors: list[str] = []
    for a in alerts:
        try:
            await notifier.send(to_notification(a, r.device_id))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{a.rule_id}: {e}")
    return alerts, errors
