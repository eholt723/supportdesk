"""
Ingest Vela knowledge base documents into pgvector.

Chunks each document by paragraph, generates embeddings with fastembed
(BAAI/bge-small-en-v1.5), and upserts into kb_chunks.

Usage:
    cd backend
    python -m scripts.ingest_kb
"""
import asyncio
import os
import re
from pathlib import Path

import asyncpg
from dotenv import load_dotenv
from fastembed import TextEmbedding

load_dotenv()

KB_DIR = Path(__file__).parent.parent / "kb_documents"
MODEL_NAME = "BAAI/bge-small-en-v1.5"
CHUNK_MIN_CHARS = 80


def chunk_document(text: str, document_name: str) -> list[dict]:
    """Split document into paragraph-level chunks, skipping very short ones."""
    # Split on double newlines (paragraph boundaries)
    raw_chunks = re.split(r"\n{2,}", text.strip())
    chunks = []
    for raw in raw_chunks:
        chunk = raw.strip()
        if len(chunk) >= CHUNK_MIN_CHARS:
            chunks.append({"document_name": document_name, "chunk_text": chunk})
    return chunks


async def ingest():
    db_url = os.environ["DATABASE_URL"]
    pool = await asyncpg.create_pool(db_url)

    print(f"Loading embedding model: {MODEL_NAME}")
    embedder = TextEmbedding(MODEL_NAME)

    doc_files = sorted(KB_DIR.glob("*.txt"))
    if not doc_files:
        print(f"No .txt files found in {KB_DIR}")
        return

    all_chunks = []
    for doc_file in doc_files:
        text = doc_file.read_text(encoding="utf-8")
        doc_name = doc_file.stem.replace("_", " ").title()
        chunks = chunk_document(text, doc_name)
        print(f"  {doc_file.name}: {len(chunks)} chunks")
        all_chunks.extend(chunks)

    print(f"\nTotal chunks: {len(all_chunks)}")
    print("Generating embeddings...")

    texts = [c["chunk_text"] for c in all_chunks]
    embeddings = list(embedder.embed(texts))

    print("Inserting into database...")

    async with pool.acquire() as conn:
        # Clear existing KB chunks so re-runs are idempotent
        await conn.execute("DELETE FROM kb_chunks")

        for chunk, embedding in zip(all_chunks, embeddings):
            emb_list = embedding.tolist()
            await conn.execute(
                """
                INSERT INTO kb_chunks (document_name, chunk_text, embedding)
                VALUES ($1, $2, $3::vector)
                """,
                chunk["document_name"],
                chunk["chunk_text"],
                str(emb_list),
            )

    await pool.close()
    print(f"Ingestion complete. {len(all_chunks)} chunks stored.")


if __name__ == "__main__":
    asyncio.run(ingest())
