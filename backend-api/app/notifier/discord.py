"""用 Discord Webhook 送通知。"""

import asyncio
import logging

import httpx

from app.notifier.base import Notification, Severity

log = logging.getLogger(__name__)

# embed 左側色條的顏色
_COLORS = {
    Severity.INFO: 0x3498DB,      # 藍
    Severity.WARNING: 0xF1C40F,   # 黃
    Severity.CRITICAL: 0xE74C3C,  # 紅
}
_LABELS = {
    Severity.INFO: "資訊",
    Severity.WARNING: "警告",
    Severity.CRITICAL: "緊急",
}
_FIELD_LIMIT = 1024  # Discord 限制：embed 每個欄位最多 1024 字


class DiscordError(Exception):
    pass


class DiscordWebhookNotifier:
    def __init__(self, webhook_url: str, *, timeout_s: float = 10.0, max_retries: int = 1):
        self._url = webhook_url
        self._timeout_s = timeout_s
        self._max_retries = max_retries

    def build_payload(self, n: Notification) -> dict:
        fields = [
            {"name": "嚴重度", "value": _LABELS[n.severity], "inline": True},
            {"name": "判讀", "value": n.interpretation[:_FIELD_LIMIT], "inline": False},
            {"name": "下一步", "value": n.next_step[:_FIELD_LIMIT], "inline": False},
            {"name": "依據", "value": n.basis[:_FIELD_LIMIT], "inline": False},
        ]
        fields += [{"name": k, "value": v[:_FIELD_LIMIT], "inline": True} for k, v in n.extra.items()]
        return {
            "username": "智慧魚缸",
            "embeds": [{"title": n.title[:256], "color": _COLORS[n.severity], "fields": fields}],
        }

    async def send(self, notification: Notification) -> None:
        payload = self.build_payload(notification)
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            for attempt in range(self._max_retries + 1):
                resp = await client.post(self._url, json=payload)
                # 被限流：Discord 回 429,body 的 retry_after 是要等待的秒數
                if resp.status_code == 429 and attempt < self._max_retries:
                    wait_s = float(resp.json().get("retry_after", 1.0))
                    log.warning("Discord 限流，%.1f 秒後重送", wait_s)
                    await asyncio.sleep(wait_s)
                    continue
                if resp.is_success:  # 成功時 Discord 回 204
                    return
                # 不把 URL 寫進錯誤訊息，避免外洩
                raise DiscordError(f"Discord 回應 {resp.status_code}: {resp.text[:200]}")
