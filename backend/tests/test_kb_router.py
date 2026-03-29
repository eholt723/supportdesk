"""Tests for the knowledge base router: chunking logic and HTTP endpoints."""
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Pure unit tests — _chunk_text
# ---------------------------------------------------------------------------

def test_chunk_text_splits_on_double_newline():
    from app.routers.kb import _chunk_text
    a = "A" * 100
    b = "B" * 100
    chunks = _chunk_text(f"{a}\n\n{b}")
    assert chunks == [a, b]


def test_chunk_text_drops_short_chunks():
    from app.routers.kb import _chunk_text
    short = "Too short."
    long = "This is a sufficiently long chunk that describes billing policy in full detail." * 2
    chunks = _chunk_text(f"{short}\n\n{long}")
    assert len(chunks) == 1
    assert chunks[0] == long


def test_chunk_text_empty_input():
    from app.routers.kb import _chunk_text
    assert _chunk_text("") == []


def test_chunk_text_all_short_returns_empty():
    from app.routers.kb import _chunk_text
    assert _chunk_text("Short.\n\nAlso short.") == []


def test_chunk_text_strips_surrounding_whitespace():
    from app.routers.kb import _chunk_text
    content = "A" * 100
    chunks = _chunk_text(f"\n\n  {content}  \n\n")
    assert chunks == [content]


def test_chunk_text_multiple_blank_lines_treated_as_split():
    from app.routers.kb import _chunk_text
    a = "A" * 100
    b = "B" * 100
    chunks = _chunk_text(f"{a}\n\n\n\n{b}")
    assert len(chunks) == 2


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------

SECRET = "test-kb-secret"


def _make_pool(conn):
    pool = AsyncMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=False),
        )
    )
    return pool


@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock(return_value=None)
    return conn


@pytest.fixture
def client(mock_conn):
    pool = _make_pool(mock_conn)
    with patch("app.config.settings") as mock_settings, \
         patch("app.security.settings") as mock_sec, \
         patch("app.database.get_pool", return_value=pool), \
         patch("app.routers.kb.get_pool", return_value=pool):
        mock_settings.webhook_secret = SECRET
        mock_settings.groq_api_key = "test"
        mock_settings.resend_api_key = "test"
        mock_settings.resend_from_email = "from@test.com"
        mock_settings.database_url = "postgresql://x"
        mock_sec.webhook_secret = SECRET
        from app.main import app
        yield TestClient(app, raise_server_exceptions=False), mock_conn


class TestListDocuments:
    def test_returns_documents(self, client):
        tc, conn = client
        conn.fetch = AsyncMock(return_value=[
            {"document_name": "Billing FAQ", "chunk_count": 5, "loaded_at": "2024-01-01T00:00:00"},
        ])
        r = tc.get("/api/kb")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["document_name"] == "Billing FAQ"
        assert data[0]["chunk_count"] == 5

    def test_empty_kb(self, client):
        tc, conn = client
        conn.fetch = AsyncMock(return_value=[])
        r = tc.get("/api/kb")
        assert r.status_code == 200
        assert r.json() == []


class TestListChunks:
    def test_all_chunks(self, client):
        tc, conn = client
        conn.fetch = AsyncMock(return_value=[
            {"id": 1, "document_name": "FAQ", "chunk_text": "Some text.", "created_at": "2024-01-01T00:00:00"},
        ])
        r = tc.get("/api/kb/chunks")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_filtered_by_document(self, client):
        tc, conn = client
        conn.fetch = AsyncMock(return_value=[])
        r = tc.get("/api/kb/chunks?document_name=Billing+FAQ")
        assert r.status_code == 200
        call_args = conn.fetch.call_args
        assert "Billing FAQ" in call_args.args

    def test_default_pagination(self, client):
        tc, conn = client
        conn.fetch = AsyncMock(return_value=[])
        r = tc.get("/api/kb/chunks?limit=10&offset=5")
        assert r.status_code == 200
        call_args = conn.fetch.call_args
        assert 10 in call_args.args
        assert 5 in call_args.args


class TestUploadDocument:
    def _long_chunk(self):
        return "Detailed billing policy: customers may cancel at any time. " * 5

    def test_valid_txt_upload(self, client):
        tc, conn = client
        chunk = self._long_chunk()
        content = f"{chunk}\n\n{chunk}".encode()

        mock_embedder = MagicMock()
        mock_embedder.embed = MagicMock(return_value=iter([
            np.array([0.1] * 384),
            np.array([0.2] * 384),
        ]))

        with patch("app.search._get_embedder", return_value=mock_embedder):
            r = tc.post("/api/kb/upload", files={"file": ("billing.txt", content, "text/plain")})

        assert r.status_code == 200
        data = r.json()
        assert data["document_name"] == "Billing"
        assert data["chunks_stored"] == 2

    def test_non_txt_rejected(self, client):
        tc, _ = client
        r = tc.post("/api/kb/upload", files={"file": ("report.csv", b"a,b,c", "text/csv")})
        assert r.status_code == 422

    def test_file_with_no_usable_chunks_rejected(self, client):
        tc, _ = client
        r = tc.post("/api/kb/upload", files={"file": ("empty.txt", b"short", "text/plain")})
        assert r.status_code == 422

    def test_document_name_derived_from_filename(self, client):
        tc, conn = client
        chunk = self._long_chunk()

        mock_embedder = MagicMock()
        mock_embedder.embed = MagicMock(return_value=iter([np.array([0.1] * 384)]))

        with patch("app.search._get_embedder", return_value=mock_embedder):
            r = tc.post(
                "/api/kb/upload",
                files={"file": ("getting_started.txt", chunk.encode(), "text/plain")},
            )

        assert r.status_code == 200
        assert r.json()["document_name"] == "Getting Started"


class TestDeleteDocument:
    def test_success(self, client):
        tc, conn = client
        conn.execute = AsyncMock(return_value="DELETE 4")
        r = tc.delete("/api/kb/Billing%20FAQ")
        assert r.status_code == 200
        assert r.json()["deleted_chunks"] == 4

    def test_not_found(self, client):
        tc, conn = client
        conn.execute = AsyncMock(return_value="DELETE 0")
        r = tc.delete("/api/kb/Nonexistent")
        assert r.status_code == 404
