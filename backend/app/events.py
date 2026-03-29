"""
In-process event bus for broadcasting pipeline events to WebSocket clients
and writing to the database audit log.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any

# Connected WebSocket queues — one per client
_subscribers: list[asyncio.Queue] = []


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


async def broadcast(event_type: str, message: str, extra: dict[str, Any] | None = None):
    """Send an event to all connected WebSocket clients."""
    payload = {
        "time": _now_iso(),
        "type": event_type,
        "message": message,
        **(extra or {}),
    }
    dead = []
    for q in _subscribers:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _subscribers.remove(q)


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue):
    try:
        _subscribers.remove(q)
    except ValueError:
        pass
