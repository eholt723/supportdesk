"""
Three-stage async pipeline: classify → search → draft.
Each stage writes to pipeline_runs and broadcasts events.
"""
import asyncio
import json
import time
from typing import Any

from app.database import get_pool
from app import events as event_bus
from app.classify import classify_ticket
from app.search import search_kb
from app.draft import draft_response


async def run_pipeline(ticket_id: int):
    pool = await get_pool()

    async with pool.acquire() as conn:
        ticket = await conn.fetchrow(
            "SELECT id, source_email, subject, body FROM tickets WHERE id = $1",
            ticket_id,
        )

    if not ticket:
        return

    # Stage 1: Classify
    classify_result = await _run_stage(
        ticket_id,
        "classify",
        _classify_stage,
        ticket,
    )
    if classify_result is None:
        return

    ticket_type = classify_result["type"]
    urgency = classify_result["urgency"]
    confidence = classify_result["confidence"]

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE tickets SET type = $1, urgency = $2 WHERE id = $3",
            ticket_type, urgency, ticket_id,
        )

    await event_bus.broadcast(
        "CLASSIFY",
        f"Type: {ticket_type}  Urgency: {urgency}  Confidence: {confidence:.2f}",
        {"ticket_id": ticket_id, "type": ticket_type, "urgency": urgency},
    )

    # Stage 2: Search
    search_result = await _run_stage(
        ticket_id,
        "search",
        _search_stage,
        ticket,
    )
    if search_result is None:
        return

    passages = search_result["passages"]
    await event_bus.broadcast(
        "SEARCH",
        f"Retrieved {len(passages)} passages from knowledge base",
        {"ticket_id": ticket_id, "passage_count": len(passages)},
    )

    # Stage 3: Draft
    draft_result = await _run_stage(
        ticket_id,
        "draft",
        _draft_stage,
        ticket,
        passages,
    )
    if draft_result is None:
        return

    word_count = len(draft_result["draft_text"].split())
    source_count = len(draft_result["sources_used"])
    await event_bus.broadcast(
        "DRAFT",
        f"Response generated — {word_count} words — {source_count} sources cited",
        {"ticket_id": ticket_id},
    )

    await event_bus.broadcast(
        "PENDING",
        "Awaiting agent approval",
        {"ticket_id": ticket_id},
    )


async def _run_stage(ticket_id: int, stage: str, fn, *args) -> Any | None:
    pool = await get_pool()
    start = time.monotonic()

    async with pool.acquire() as conn:
        run_id = await conn.fetchval(
            """
            INSERT INTO pipeline_runs (ticket_id, stage, status)
            VALUES ($1, $2, 'running')
            RETURNING id
            """,
            ticket_id, stage,
        )

    try:
        result = await fn(*args)
        duration_ms = int((time.monotonic() - start) * 1000)
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE pipeline_runs SET status = 'completed', duration_ms = $1 WHERE id = $2",
                duration_ms, run_id,
            )
        return result
    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE pipeline_runs SET status = 'failed', duration_ms = $1 WHERE id = $2",
                duration_ms, run_id,
            )
        await event_bus.broadcast(
            "ERROR",
            f"Stage '{stage}' failed: {exc}",
            {"ticket_id": ticket_id, "stage": stage},
        )
        return None


async def _classify_stage(ticket: Any) -> dict:
    return await classify_ticket(
        subject=ticket["subject"],
        body=ticket["body"],
    )


async def _search_stage(ticket: Any) -> dict:
    query = f"{ticket['subject']} {ticket['body']}"
    passages = await search_kb(query, top_k=3)
    return {"passages": passages}


async def _draft_stage(ticket: Any, passages: list[dict]) -> dict:
    pool = await get_pool()
    result = await draft_response(
        ticket_id=ticket["id"],
        subject=ticket["subject"],
        body=ticket["body"],
        passages=passages,
    )
    return result
