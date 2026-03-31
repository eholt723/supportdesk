import json

import resend
from fastapi import APIRouter, BackgroundTasks, HTTPException, Path
from fastapi.responses import StreamingResponse

from app.config import settings
from app.database import get_pool
from app.models import ApproveRequest
from app import events as event_bus
from app import sse
from app.pipeline import run_pipeline

router = APIRouter()

resend.api_key = settings.resend_api_key


@router.get("")
async def list_tickets():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.id, t.source_email, t.subject, t.body, t.type, t.urgency,
                   t.status, t.created_at,
                   d.confidence_score, d.sent_at,
                   (SELECT COUNT(*) FROM pipeline_runs pr WHERE pr.ticket_id = t.id) AS stage_count,
                   (SELECT COUNT(*) FROM delivery_log dl WHERE dl.ticket_id = t.id AND dl.status = 'sent') AS sent_count
            FROM tickets t
            LEFT JOIN draft_responses d ON d.ticket_id = t.id
            ORDER BY
                CASE t.urgency WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                t.created_at DESC
            """
        )
    return [dict(r) for r in rows]


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: int = Path(...)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        ticket = await conn.fetchrow(
            "SELECT * FROM tickets WHERE id = $1", ticket_id
        )
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        draft = await conn.fetchrow(
            "SELECT * FROM draft_responses WHERE ticket_id = $1 ORDER BY created_at DESC LIMIT 1",
            ticket_id,
        )
        stages = await conn.fetch(
            "SELECT stage, status, duration_ms, created_at FROM pipeline_runs WHERE ticket_id = $1 ORDER BY created_at",
            ticket_id,
        )

    result = dict(ticket)
    result["draft"] = dict(draft) if draft else None
    if result["draft"] and isinstance(result["draft"].get("sources_used"), str):
        result["draft"]["sources_used"] = json.loads(result["draft"]["sources_used"])
    result["pipeline_stages"] = [dict(s) for s in stages]
    return result


@router.get("/{ticket_id}/stream")
async def stream_draft(ticket_id: int = Path(...)):
    """SSE endpoint — streams draft tokens as the LLM generates them."""
    return StreamingResponse(
        sse.token_stream(ticket_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{ticket_id}/approve")
async def approve_ticket(ticket_id: int, body: ApproveRequest):
    pool = await get_pool()
    async with pool.acquire() as conn:
        ticket = await conn.fetchrow(
            "SELECT id, source_email, status FROM tickets WHERE id = $1", ticket_id
        )
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if ticket["status"] != "pending":
            raise HTTPException(status_code=409, detail=f"Ticket is already '{ticket['status']}'")

        draft = await conn.fetchrow(
            "SELECT id, draft_text FROM draft_responses WHERE ticket_id = $1 ORDER BY created_at DESC LIMIT 1",
            ticket_id,
        )
        if not draft:
            raise HTTPException(status_code=409, detail="No draft found for this ticket")

    await event_bus.broadcast(
        "APPROVED",
        f"Agent approved — sending via Resend",
        {"ticket_id": ticket_id},
    )

    # Send email via Resend
    try:
        resend.Emails.send({
            "from": settings.resend_from_email,
            "to": ticket["source_email"],
            "subject": "Re: SupportDesk Ticket Update",
            "text": draft["draft_text"],
        })
        delivery_status = "sent"
        error_message = None
    except Exception as exc:
        delivery_status = "failed"
        error_message = str(exc)

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Update ticket status
        new_status = "sent" if delivery_status == "sent" else "pending"
        await conn.execute(
            "UPDATE tickets SET status = $1 WHERE id = $2",
            new_status, ticket_id,
        )
        # Update draft with approval info
        from datetime import datetime, timezone
        await conn.execute(
            "UPDATE draft_responses SET approved_by = $1, sent_at = $2 WHERE id = $3",
            body.agent_name,
            datetime.now(timezone.utc) if delivery_status == "sent" else None,
            draft["id"],
        )
        # Log delivery
        await conn.execute(
            """
            INSERT INTO delivery_log (ticket_id, recipient_email, status, error_message)
            VALUES ($1, $2, $3, $4)
            """,
            ticket_id, ticket["source_email"], delivery_status, error_message,
        )

    if delivery_status == "sent":
        await event_bus.broadcast(
            "SENT",
            f"Delivered to {ticket['source_email']}",
            {"ticket_id": ticket_id},
        )
    else:
        await event_bus.broadcast(
            "ERROR",
            f"Delivery failed: {error_message}",
            {"ticket_id": ticket_id},
        )

    return {"status": delivery_status}


@router.post("/{ticket_id}/discard")
async def discard_ticket(ticket_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE tickets SET status = 'discarded' WHERE id = $1 AND status = 'pending'",
            ticket_id,
        )
    if result == "UPDATE 0":
        raise HTTPException(status_code=409, detail="Ticket not in pending state")
    return {"status": "discarded"}


@router.post("/{ticket_id}/reset")
async def reset_ticket(ticket_id: int, background_tasks: BackgroundTasks):
    """Reset a ticket to pending and re-run the full pipeline."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        ticket = await conn.fetchrow("SELECT id FROM tickets WHERE id = $1", ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        await conn.execute("DELETE FROM delivery_log WHERE ticket_id = $1", ticket_id)
        await conn.execute("DELETE FROM draft_responses WHERE ticket_id = $1", ticket_id)
        await conn.execute("DELETE FROM pipeline_runs WHERE ticket_id = $1", ticket_id)
        await conn.execute("UPDATE tickets SET status = 'pending', type = NULL, urgency = NULL WHERE id = $1", ticket_id)
    background_tasks.add_task(run_pipeline, ticket_id)
    return {"status": "pending"}
