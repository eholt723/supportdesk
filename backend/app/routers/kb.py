from fastapi import APIRouter

from app.database import get_pool

router = APIRouter()


@router.get("")
async def list_documents():
    """Return distinct documents loaded in the knowledge base with chunk counts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT document_name, COUNT(*) AS chunk_count, MAX(created_at) AS loaded_at
            FROM kb_chunks
            GROUP BY document_name
            ORDER BY document_name
            """
        )
    return [dict(r) for r in rows]


@router.get("/chunks")
async def list_chunks(document_name: str | None = None, limit: int = 50, offset: int = 0):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if document_name:
            rows = await conn.fetch(
                """
                SELECT id, document_name, chunk_text, created_at
                FROM kb_chunks
                WHERE document_name = $1
                ORDER BY id
                LIMIT $2 OFFSET $3
                """,
                document_name, limit, offset,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, document_name, chunk_text, created_at
                FROM kb_chunks
                ORDER BY id
                LIMIT $1 OFFSET $2
                """,
                limit, offset,
            )
    return [dict(r) for r in rows]
