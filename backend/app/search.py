"""
RAG search: embed query with fastembed and retrieve top-k chunks from pgvector.
"""
from functools import lru_cache

from fastembed import TextEmbedding

from app.database import get_pool

MODEL_NAME = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=1)
def _get_embedder() -> TextEmbedding:
    return TextEmbedding(MODEL_NAME)


async def search_kb(query: str, top_k: int = 3) -> list[dict]:
    """
    Embed query and return top_k closest kb_chunks by cosine similarity.

    Returns list of dicts:
        [{"id": int, "document_name": str, "chunk_text": str, "score": float}, ...]
    """
    embedder = _get_embedder()
    embedding = list(embedder.embed([query]))[0].tolist()

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                id,
                document_name,
                chunk_text,
                1 - (embedding <=> $1::vector) AS score
            FROM kb_chunks
            ORDER BY embedding <=> $1::vector
            LIMIT $2
            """,
            str(embedding),
            top_k,
        )

    return [
        {
            "id": row["id"],
            "document_name": row["document_name"],
            "chunk_text": row["chunk_text"],
            "score": round(float(row["score"]), 4),
        }
        for row in rows
    ]
