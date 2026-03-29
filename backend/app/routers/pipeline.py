from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.database import get_pool
from app.pipeline import run_pipeline

router = APIRouter()


@router.post("/{ticket_id}/run")
async def trigger_pipeline(ticket_id: int, background_tasks: BackgroundTasks):
    """Manually trigger the pipeline for an existing ticket (e.g., re-run after failure)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        ticket = await conn.fetchrow("SELECT id FROM tickets WHERE id = $1", ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    background_tasks.add_task(run_pipeline, ticket_id)
    return {"status": "pipeline started", "ticket_id": ticket_id}


@router.get("/{ticket_id}/stages")
async def get_stages(ticket_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT stage, status, duration_ms, created_at
            FROM pipeline_runs
            WHERE ticket_id = $1
            ORDER BY created_at
            """,
            ticket_id,
        )
    return [dict(r) for r in rows]
