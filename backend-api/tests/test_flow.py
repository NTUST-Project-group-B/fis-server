import json

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.device_api.router import get_notifier
from app.main import app
from app.notifier.discord import DiscordWebhookNotifier
from app.rules_engine.engine import ReadingInput, evaluate

FAKE_URL = "https://discord.test/api/webhooks/fake"


@pytest.fixture
def client():
    app.dependency_overrides[get_notifier] = lambda: DiscordWebhookNotifier(FAKE_URL, max_retries=1)
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---- 規則引擎：純函式，可重現 ----

def test_normal_reading_no_alert():
    assert evaluate(ReadingInput("t", temperature_c=25.0, ph=7.4)) == []


def test_high_temp_alert():
    alerts = evaluate(ReadingInput("t", temperature_c=30.5))
    assert [a.rule_id for a in alerts] == ["FAKE-TEMP-HIGH"]


def test_evaluate_is_reproducible():
    r = ReadingInput("t", temperature_c=20.0, ph=6.5)
    assert evaluate(r) == evaluate(r)
    assert {a.rule_id for a in evaluate(r)} == {"FAKE-TEMP-LOW", "FAKE-PH-RANGE"}


# ---- 整條流程：裝置 API → 規則引擎 → 通知模組 → Discord ----

@respx.mock
def test_alert_is_sent_to_discord(client):
    route = respx.post(FAKE_URL).mock(return_value=httpx.Response(204))
    resp = client.post("/api/v1/device/readings", json={"device_id": "tank-01", "temperature_c": 30.5})

    assert resp.status_code == 200
    assert resp.json()["alerts"][0]["rule_id"] == "FAKE-TEMP-HIGH"
    assert resp.json()["notify_errors"] == []
    assert route.call_count == 1
    embed = json.loads(route.calls[0].request.content)["embeds"][0]
    assert embed["title"] == "水溫過高"


@respx.mock
def test_no_alert_no_discord_call(client):
    route = respx.post(FAKE_URL).mock(return_value=httpx.Response(204))
    resp = client.post("/api/v1/device/readings", json={"device_id": "tank-01", "temperature_c": 25.0})
    assert resp.json()["alerts"] == []
    assert route.call_count == 0


@respx.mock
def test_rate_limit_retry(client):
    route = respx.post(FAKE_URL).mock(side_effect=[
        httpx.Response(429, json={"retry_after": 0.01}),
        httpx.Response(204),
    ])
    resp = client.post("/api/v1/device/readings", json={"device_id": "tank-01", "temperature_c": 30.5})
    assert resp.json()["notify_errors"] == []
    assert route.call_count == 2


@respx.mock
def test_discord_failure_does_not_fail_upload(client):
    respx.post(FAKE_URL).mock(return_value=httpx.Response(500, text="boom"))
    resp = client.post("/api/v1/device/readings", json={"device_id": "tank-01", "temperature_c": 30.5})
    assert resp.status_code == 200
    assert "500" in resp.json()["notify_errors"][0]
