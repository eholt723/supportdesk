import re

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.database import get_pool

router = APIRouter()

CHUNK_MIN_CHARS = 80


def _chunk_text(text: str) -> list[str]:
    """Split on double newlines, drop very short chunks."""
    return [c.strip() for c in re.split(r"\n{2,}", text.strip()) if len(c.strip()) >= CHUNK_MIN_CHARS]


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


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a plain text (.txt) file, chunk it, embed with fastembed,
    and store in kb_chunks. Replaces any existing chunks for the same document name.
    """
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=422, detail="Only .txt files are supported")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="File must be UTF-8 encoded")

    document_name = file.filename[:-4].replace("_", " ").title()
    chunks = _chunk_text(text)

    if not chunks:
        raise HTTPException(status_code=422, detail="No usable text found in file")

    # Import here to avoid loading model on every request
    from app.search import _get_embedder
    embedder = _get_embedder()
    embeddings = list(embedder.embed(chunks))

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM kb_chunks WHERE document_name = $1", document_name)
        for chunk_text, embedding in zip(chunks, embeddings):
            await conn.execute(
                """
                INSERT INTO kb_chunks (document_name, chunk_text, embedding)
                VALUES ($1, $2, $3::vector)
                """,
                document_name,
                chunk_text,
                str(embedding.tolist()),
            )

    return {"document_name": document_name, "chunks_stored": len(chunks)}


@router.delete("/{document_name}")
async def delete_document(document_name: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM kb_chunks WHERE document_name = $1", document_name
        )
    deleted = int(result.split()[-1])
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted_chunks": deleted}
