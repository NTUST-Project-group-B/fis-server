"""裝置 API 的格式(暫代)。

計畫書分工：裝置 API 由 A 負責。這裡是 B 為了測試流程先寫的假版本，之後由 A 改寫。
格式未凍結(第 2 個月底前兩人共同凍結)。
"""

from pydantic import BaseModel, Field


class ReadingIn(BaseModel):
    device_id: str = Field(min_length=1, examples=["tank-01"])
    temperature_c: float = Field(examples=[30.5])
    ph: float | None = Field(default=None, examples=[7.2])
    tds_ppm: float | None = Field(default=None, examples=[250])


class AlertOut(BaseModel):
    rule_id: str
    severity: str
    title: str


class ReadingResult(BaseModel):
    alerts: list[AlertOut]
    notify_errors: list[str]
