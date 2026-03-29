"""Tests for HMAC webhook signature verification."""
import hashlib
import hmac
import time

import pytest
from fastapi import HTTPException

from app.security import verify_webhook_signature


def make_sig(secret: str, timestamp: str, payload: bytes) -> str:
    signed = f"{timestamp}.".encode() + payload
    return hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()


PAYLOAD = b'{"email":"a@b.com","subject":"test","body":"hello"}'
SECRET = "test-secret"


def test_valid_signature():
    ts = str(int(time.time()))
    sig = make_sig(SECRET, ts, PAYLOAD)

    import os
    os.environ["WEBHOOK_SECRET"] = SECRET
    # Patch settings
    import app.security as sec
    from unittest.mock import patch
    with patch("app.security.settings") as mock_settings:
        mock_settings.webhook_secret = SECRET
        verify_webhook_signature(PAYLOAD, sig, ts)  # should not raise


def test_missing_signature():
    ts = str(int(time.time()))
    from unittest.mock import patch
    with patch("app.security.settings") as mock_settings:
        mock_settings.webhook_secret = SECRET
        with pytest.raises(HTTPException) as exc_info:
            verify_webhook_signature(PAYLOAD, None, ts)
        assert exc_info.value.status_code == 401


def test_missing_timestamp():
    sig = make_sig(SECRET, str(int(time.time())), PAYLOAD)
    from unittest.mock import patch
    with patch("app.security.settings") as mock_settings:
        mock_settings.webhook_secret = SECRET
        with pytest.raises(HTTPException) as exc_info:
            verify_webhook_signature(PAYLOAD, sig, None)
        assert exc_info.value.status_code == 401


def test_wrong_signature():
    ts = str(int(time.time()))
    from unittest.mock import patch
    with patch("app.security.settings") as mock_settings:
        mock_settings.webhook_secret = SECRET
        with pytest.raises(HTTPException) as exc_info:
            verify_webhook_signature(PAYLOAD, "badhex", ts)
        assert exc_info.value.status_code == 401


def test_expired_timestamp():
    old_ts = str(int(time.time()) - 400)  # 400s ago, over the 300s limit
    sig = make_sig(SECRET, old_ts, PAYLOAD)
    from unittest.mock import patch
    with patch("app.security.settings") as mock_settings:
        mock_settings.webhook_secret = SECRET
        with pytest.raises(HTTPException) as exc_info:
            verify_webhook_signature(PAYLOAD, sig, old_ts)
        assert exc_info.value.status_code == 401
