"""通知模組的介面。

規則引擎(警報)和之後的排程器(日常提醒)都透過這個介面送通知，
所以這裡不依賴規則引擎的型別。

尚未實作(計畫書要求):同一規則的冷卻時間。
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Notification:
    title: str
    severity: Severity
    # 圖 4 第 12 步：警報內容包含嚴重度、判讀、下一步、依據
    interpretation: str
    next_step: str
    basis: str
    source_id: str = ""  # 例如規則 ID,之後做冷卻時間會用到
    extra: dict[str, str] = field(default_factory=dict)


class Notifier(Protocol):
    async def send(self, notification: Notification) -> None: ...
