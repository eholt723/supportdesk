import asyncio
import hashlib
import json
import time

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks

from app.database import get_pool
from app.security import verify_webhook_signature
from app import events as event_bus
from app.pipeline import run_pipeline

router = APIRouter()


@router.post("/ticket")
async def receive_ticket(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for incoming support tickets.

    Expected headers:
        X-Webhook-Signature: HMAC-SHA256 hex of "<timestamp>.<payload>"
        X-Webhook-Timestamp: Unix timestamp (seconds) of when the request was sent

    Expected JSON body:
        { "email": "...", "subject": "...", "body": "...", "timestamp": <int> }
    """
    raw_body = await request.body()
    sig = request.headers.get("X-Webhook-Signature")
    ts = request.headers.get("X-Webhook-Timestamp")

    signature_valid = True
    try:
        verify_webhook_signature(raw_body, sig, ts)
    except HTTPException:
        signature_valid = False
        # Log the failed attempt before re-raising
        await _log_webhook_event(raw_body, signature_valid=False)
        raise

    payload = await request.json()
    email = payload.get("email", "")
    subject = payload.get("subject", "")
    body = payload.get("body", "")

    if not all([email, subject, body]):
        raise HTTPException(status_code=422, detail="Missing required fields: email, subject, body")

    # Log webhook event
    webhook_id = await _log_webhook_event(raw_body, signature_valid=True, payload=payload)

    # Create ticket record
    pool = await get_pool()
    async with pool.acquire() as conn:
        ticket_id = await conn.fetchval(
            """
            INSERT INTO tickets (source_email, subject, body)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            email, subject, body,
        )

    await event_bus.broadcast(
        "WEBHOOK",
        f"New ticket received from {email}",
        {"ticket_id": ticket_id},
    )

    # Run pipeline asynchronously — don't block the 200 response
    background_tasks.add_task(run_pipeline, ticket_id)

    return {"status": "accepted", "ticket_id": ticket_id}


async def _log_webhook_event(raw_body: bytes, signature_valid: bool, payload: dict | None = None) -> int:
    payload_hash = hashlib.sha256(raw_body).hexdigest()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row_id = await conn.fetchval(
            """
            INSERT INTO webhook_events (payload_hash, signature_valid, raw_payload)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            payload_hash,
            signature_valid,
            json.dumps(payload) if payload is not None else None,
        )
    return row_id
