"""Unit tests for draft response generation."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def make_stream_chunk(content):
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta.content = content
    return chunk


def make_async_stream(chunks):
    """Return an async generator that yields the given chunks."""
    async def _stream():
        for c in chunks:
            yield c
    return _stream()


def make_mock_pool():
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=False),
        )
    )
    return mock_pool


PASSAGES = [
    {"document_name": "Billing FAQ", "chunk_text": "Cancel anytime.", "score": 0.9},
    {"document_name": "Terms", "chunk_text": "Refunds take 3-5 days.", "score": 0.8},
]


@pytest.mark.asyncio
async def test_draft_confidence_averages_passages():
    """Confidence score is the mean of all passage scores."""
    from app.draft import draft_response

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=make_async_stream([make_stream_chunk("Hello.")])
    )

    with patch("app.draft._get_client", return_value=mock_client), \
         patch("app.draft.get_pool", return_value=make_mock_pool()), \
         patch("app.draft.sse.broadcast_token", new_callable=AsyncMock), \
         patch("app.draft.sse.broadcast_done", new_callable=AsyncMock):
        result = await draft_response(1, "Subject", "Body", PASSAGES)

    assert result["confidence_score"] == pytest.approx(0.85)


@pytest.mark.asyncio
async def test_draft_empty_passages_fallback():
    """No passages → confidence_score defaults to 0.5."""
    from app.draft import draft_response

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=make_async_stream([make_stream_chunk("Reply.")])
    )

    with patch("app.draft._get_client", return_value=mock_client), \
         patch("app.draft.get_pool", return_value=make_mock_pool()), \
         patch("app.draft.sse.broadcast_token", new_callable=AsyncMock), \
         patch("app.draft.sse.broadcast_done", new_callable=AsyncMock):
        result = await draft_response(1, "Subject", "Body", [])

    assert result["confidence_score"] == 0.5


@pytest.mark.asyncio
async def test_draft_streams_non_null_tokens():
    """Each non-null delta is broadcast; null deltas are skipped."""
    from app.draft import draft_response

    chunks = [
        make_stream_chunk("Hi"),
        make_stream_chunk(None),
        make_stream_chunk(" there"),
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=make_async_stream(chunks)
    )

    mock_broadcast_token = AsyncMock()
    mock_broadcast_done = AsyncMock()

    with patch("app.draft._get_client", return_value=mock_client), \
         patch("app.draft.get_pool", return_value=make_mock_pool()), \
         patch("app.draft.sse.broadcast_token", mock_broadcast_token), \
         patch("app.draft.sse.broadcast_done", mock_broadcast_done):
        result = await draft_response(1, "Subject", "Body", [])

    assert mock_broadcast_token.call_count == 2
    mock_broadcast_done.assert_called_once_with(1)
    assert result["draft_text"] == "Hi there"


@pytest.mark.asyncio
async def test_draft_concatenates_all_deltas():
    """Full draft text is all deltas joined in order."""
    from app.draft import draft_response

    chunks = [make_stream_chunk(t) for t in ["Thank ", "you ", "for ", "reaching ", "out."]]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=make_async_stream(chunks)
    )

    with patch("app.draft._get_client", return_value=mock_client), \
         patch("app.draft.get_pool", return_value=make_mock_pool()), \
         patch("app.draft.sse.broadcast_token", new_callable=AsyncMock), \
         patch("app.draft.sse.broadcast_done", new_callable=AsyncMock):
        result = await draft_response(1, "Subject", "Body", [])

    assert result["draft_text"] == "Thank you for reaching out."


@pytest.mark.asyncio
async def test_draft_returns_correct_ticket_id_and_sources():
    """Return value includes ticket_id and the original passages under sources_used."""
    from app.draft import draft_response

    passages = [{"document_name": "FAQ", "chunk_text": "...", "score": 0.75}]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=make_async_stream([make_stream_chunk("Reply")])
    )

    with patch("app.draft._get_client", return_value=mock_client), \
         patch("app.draft.get_pool", return_value=make_mock_pool()), \
         patch("app.draft.sse.broadcast_token", new_callable=AsyncMock), \
         patch("app.draft.sse.broadcast_done", new_callable=AsyncMock):
        result = await draft_response(42, "Subject", "Body", passages)

    assert result["ticket_id"] == 42
    assert result["sources_used"] == passages
