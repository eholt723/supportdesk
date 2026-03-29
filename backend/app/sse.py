"""
Server-Sent Events (SSE) manager for streaming draft tokens to the frontend.
Each ticket gets its own set of listeners.
"""
import asyncio
from collections import defaultdict
from typing import AsyncIterator

# ticket_id -> list of queues (one per connected client)
_listeners: dict[int, list[asyncio.Queue]] = defaultdict(list)


def subscribe(ticket_id: int) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=512)
    _listeners[ticket_id].append(q)
    return q


def unsubscribe(ticket_id: int, q: asyncio.Queue):
    try:
        _listeners[ticket_id].remove(q)
    except ValueError:
        pass
    if not _listeners[ticket_id]:
        del _listeners[ticket_id]


async def broadcast_token(ticket_id: int, token: str):
    dead = []
    for q in _listeners.get(ticket_id, []):
        try:
            q.put_nowait({"type": "token", "data": token})
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        unsubscribe(ticket_id, q)


async def broadcast_done(ticket_id: int):
    for q in _listeners.get(ticket_id, []):
        try:
            q.put_nowait({"type": "done"})
        except asyncio.QueueFull:
            pass


async def token_stream(ticket_id: int) -> AsyncIterator[str]:
    """Yield SSE-formatted strings for a given ticket."""
    q = subscribe(ticket_id)
    try:
        while True:
            event = await asyncio.wait_for(q.get(), timeout=60.0)
            if event["type"] == "token":
                token = event["data"].replace("\n", "\\n")
                yield f"data: {token}\n\n"
            elif event["type"] == "done":
                yield "data: [DONE]\n\n"
                break
    except asyncio.TimeoutError:
        yield "data: [TIMEOUT]\n\n"
    finally:
        unsubscribe(ticket_id, q)
