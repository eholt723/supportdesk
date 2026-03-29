import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app import events as event_bus

router = APIRouter()


@router.websocket("/ws")
async def websocket_events(websocket: WebSocket):
    """
    WebSocket endpoint for the live event log.
    Broadcasts all pipeline events (WEBHOOK, CLASSIFY, SEARCH, DRAFT, etc.) in real time.
    """
    await websocket.accept()
    q = event_bus.subscribe()
    try:
        while True:
            event = await asyncio.wait_for(q.get(), timeout=30.0)
            await websocket.send_text(json.dumps(event))
    except asyncio.TimeoutError:
        # Send a heartbeat ping so the connection stays alive
        try:
            await websocket.send_text(json.dumps({"type": "ping"}))
        except Exception:
            pass
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.unsubscribe(q)


@router.get("/recent")
async def recent_events():
    """Return the last N events from the database for dashboard load."""
    from app.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                we.processed_at AS time,
                'WEBHOOK' AS type,
                'Ticket received' AS message,
                we.signature_valid,
                we.id
            FROM webhook_events we
            ORDER BY we.processed_at DESC
            LIMIT 50
            """
        )
    return [dict(r) for r in rows]
