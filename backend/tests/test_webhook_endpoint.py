"""Integration tests for the webhook endpoint using FastAPI TestClient."""
import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient


def make_sig(secret: str, ts: str, payload: bytes) -> str:
    signed = f"{ts}.".encode() + payload
    return hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()


SECRET = "test-secret-key"
PAYLOAD = json.dumps({"email": "test@example.com", "subject": "Test", "body": "Hello"}).encode()


@pytest.fixture
def client():
    with patch("app.config.settings") as mock_settings:
        mock_settings.webhook_secret = SECRET
        mock_settings.groq_api_key = "test"
        mock_settings.resend_api_key = "test"
        mock_settings.resend_from_email = "test@test.com"
        mock_settings.database_url = "postgresql://x"

        with patch("app.security.settings") as mock_sec_settings, \
             patch("app.database.get_pool") as mock_pool_fn, \
             patch("app.routers.webhook.run_pipeline"), \
             patch("app.routers.webhook.event_bus.broadcast", new_callable=AsyncMock):
            mock_sec_settings.webhook_secret = SECRET

            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(return_value=42)
            mock_conn.execute = AsyncMock()
            mock_pool = AsyncMock()
            mock_pool.acquire = MagicMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock(return_value=False),
            ))
            mock_pool_fn.return_value = mock_pool

            from app.main import app
            yield TestClient(app, raise_server_exceptions=False)


def test_webhook_valid_signature(client):
    ts = str(int(time.time()))
    sig = make_sig(SECRET, ts, PAYLOAD)
    r = client.post(
        "/api/webhook/ticket",
        content=PAYLOAD,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": sig,
            "X-Webhook-Timestamp": ts,
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


def test_webhook_missing_signature(client):
    ts = str(int(time.time()))
    r = client.post(
        "/api/webhook/ticket",
        content=PAYLOAD,
        headers={"Content-Type": "application/json", "X-Webhook-Timestamp": ts},
    )
    assert r.status_code == 401


def test_webhook_bad_signature(client):
    ts = str(int(time.time()))
    r = client.post(
        "/api/webhook/ticket",
        content=PAYLOAD,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": "deadbeef",
            "X-Webhook-Timestamp": ts,
        },
    )
    assert r.status_code == 401


def test_webhook_expired_timestamp(client):
    old_ts = str(int(time.time()) - 400)
    sig = make_sig(SECRET, old_ts, PAYLOAD)
    r = client.post(
        "/api/webhook/ticket",
        content=PAYLOAD,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": sig,
            "X-Webhook-Timestamp": old_ts,
        },
    )
    assert r.status_code == 401


def test_webhook_missing_body_fields(client):
    ts = str(int(time.time()))
    bad_payload = json.dumps({"email": "x@x.com"}).encode()
    sig = make_sig(SECRET, ts, bad_payload)
    r = client.post(
        "/api/webhook/ticket",
        content=bad_payload,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": sig,
            "X-Webhook-Timestamp": ts,
        },
    )
    assert r.status_code == 422
