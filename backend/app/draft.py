"""
Draft a grounded support response using Groq LLM with RAG context injected.
Stores the result in draft_responses and streams tokens via SSE.
"""
import asyncio
import json

from groq import AsyncGroq

from app.config import settings
from app.database import get_pool
from app import sse

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


DRAFT_PROMPT = """\
You are a customer support agent for Vela, a project management SaaS tool. \
Write a professional, empathetic, and helpful reply to the customer's support ticket.

Your reply must be grounded in the reference passages provided. \
Cite only information that appears in those passages. \
Do not invent features, policies, or timelines that are not mentioned.

If the passages do not contain enough information to fully answer the question, \
acknowledge that and offer to escalate.

Keep the response concise: 100–250 words. Use a friendly but professional tone. \
Do not use markdown headers. Sign off as "Vela Support".

--- REFERENCE PASSAGES ---
{passages}
--- END PASSAGES ---

Customer ticket
Subject: {subject}
Message: {body}

Write the reply now:"""


async def draft_response(
    ticket_id: int,
    subject: str,
    body: str,
    passages: list[dict],
) -> dict:
    """
    Generate a draft response, stream tokens via SSE, and persist to database.
    """
    client = _get_client()

    passages_text = "\n\n".join(
        f"[{i+1}] From '{p['document_name']}' (score {p['score']:.2f}):\n{p['chunk_text']}"
        for i, p in enumerate(passages)
    )

    prompt = DRAFT_PROMPT.format(
        passages=passages_text,
        subject=subject,
        body=body,
    )

    stream = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=512,
        stream=True,
    )

    full_text = ""
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            full_text += delta
            # Broadcast each token to SSE listeners for this ticket
            await sse.broadcast_token(ticket_id, delta)

    # Signal end of stream
    await sse.broadcast_done(ticket_id)

    # Compute a simple confidence score from the average passage score
    avg_score = (
        sum(p["score"] for p in passages) / len(passages) if passages else 0.5
    )

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO draft_responses (ticket_id, draft_text, sources_used, confidence_score)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT DO NOTHING
            """,
            ticket_id,
            full_text,
            json.dumps(passages),
            avg_score,
        )

    return {
        "ticket_id": ticket_id,
        "draft_text": full_text,
        "sources_used": passages,
        "confidence_score": avg_score,
    }
