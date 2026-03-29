import hashlib
import hmac
import time

from fastapi import Request, HTTPException

from app.config import settings

# Reject webhooks older than 5 minutes
TIMESTAMP_TOLERANCE_SECONDS = 300


def verify_webhook_signature(payload: bytes, signature_header: str | None, timestamp_header: str | None) -> None:
    """
    Verify HMAC-SHA256 webhook signature and timestamp freshness.
    Raises HTTPException(401) on failure.
    """
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing X-Webhook-Signature header")

    if not timestamp_header:
        raise HTTPException(status_code=401, detail="Missing X-Webhook-Timestamp header")

    # Validate timestamp to prevent replay attacks
    try:
        timestamp = int(timestamp_header)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-Webhook-Timestamp header")

    age = abs(time.time() - timestamp)
    if age > TIMESTAMP_TOLERANCE_SECONDS:
        raise HTTPException(status_code=401, detail="Webhook timestamp too old")

    # Compute expected signature over timestamp + "." + payload
    signed_content = f"{timestamp_header}.".encode() + payload
    expected = hmac.new(
        settings.webhook_secret.encode(),
        signed_content,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
