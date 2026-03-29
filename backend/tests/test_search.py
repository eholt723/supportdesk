"""Unit tests for RAG search result formatting."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_search_returns_top_k():
    from app.search import search_kb

    fake_rows = [
        {"id": 1, "document_name": "Billing FAQ", "chunk_text": "Cancel anytime.", "score": 0.92},
        {"id": 2, "document_name": "Billing FAQ", "chunk_text": "Refunds take 3-5 days.", "score": 0.85},
        {"id": 3, "document_name": "Terms of Service", "chunk_text": "Liability is limited.", "score": 0.71},
    ]

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=fake_rows)

    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    import numpy as np
    mock_embedder = MagicMock()
    mock_embedder.embed = MagicMock(return_value=iter([np.array([0.1] * 384)]))

    with patch("app.search.get_pool", return_value=mock_pool), \
         patch("app.search._get_embedder", return_value=mock_embedder):
        results = await search_kb("cancel subscription", top_k=3)

    assert len(results) == 3
    assert results[0]["document_name"] == "Billing FAQ"
    assert results[0]["score"] == 0.92
    assert "chunk_text" in results[0]


@pytest.mark.asyncio
async def test_search_score_rounded():
    from app.search import search_kb

    fake_rows = [
        {"id": 1, "document_name": "Doc", "chunk_text": "text", "score": 0.912345678},
    ]

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=fake_rows)
    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))
    import numpy as np
    mock_embedder = MagicMock()
    mock_embedder.embed = MagicMock(return_value=iter([np.array([0.1] * 384)]))

    with patch("app.search.get_pool", return_value=mock_pool), \
         patch("app.search._get_embedder", return_value=mock_embedder):
        results = await search_kb("query")

    assert results[0]["score"] == round(0.912345678, 4)
