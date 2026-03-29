"""Integration tests for the tickets router."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


SECRET = "test-tickets-secret"

TICKET_ROW = {
    "id": 1,
    "source_email": "user@test.com",
    "subject": "Can't login",
    "body": "I can't access my account.",
    "type": "technical",
    "urgency": "high",
    "status": "pending",
    "created_at": "2024-01-01T00:00:00",
}

DRAFT_ROW = {
    "id": 10,
    "ticket_id": 1,
    "draft_text": "Thank you for contacting support.",
    "sources_used": json.dumps([{"document_name": "FAQ", "chunk_text": "...", "score": 0.9}]),
    "confidence_score": 0.9,
    "approved_by": None,
    "sent_at": None,
    "created_at": "2024-01-01T00:00:01",
}


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
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock(return_value="UPDATE 1")
    return conn


@pytest.fixture
def client(mock_conn):
    pool = _make_pool(mock_conn)
    with patch("app.config.settings") as mock_settings, \
         patch("app.security.settings") as mock_sec, \
         patch("app.database.get_pool", return_value=pool), \
         patch("app.routers.tickets.get_pool", return_value=pool), \
         patch("app.events.broadcast", new_callable=AsyncMock), \
         patch("resend.Emails.send") as mock_send:
        mock_settings.webhook_secret = SECRET
        mock_settings.groq_api_key = "test"
        mock_settings.resend_api_key = "test"
        mock_settings.resend_from_email = "from@test.com"
        mock_settings.database_url = "postgresql://x"
        mock_sec.webhook_secret = SECRET
        mock_send.return_value = {"id": "email-123"}
        from app.main import app
        yield TestClient(app, raise_server_exceptions=False), mock_conn, mock_send


class TestListTickets:
    def test_returns_ticket_list(self, client):
        tc, conn, _ = client
        conn.fetch = AsyncMock(return_value=[
            {**TICKET_ROW, "confidence_score": 0.9, "stage_count": 3},
        ])
        r = tc.get("/api/tickets")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["urgency"] == "high"

    def test_returns_empty_list(self, client):
        tc, conn, _ = client
        conn.fetch = AsyncMock(return_value=[])
        r = tc.get("/api/tickets")
        assert r.status_code == 200
        assert r.json() == []


class TestGetTicket:
    def test_found_with_draft_and_stages(self, client):
        tc, conn, _ = client
        stage_row = {"stage": "classify", "status": "completed", "duration_ms": 120, "created_at": "2024-01-01T00:00:02"}
        conn.fetchrow = AsyncMock(side_effect=[TICKET_ROW, DRAFT_ROW])
        conn.fetch = AsyncMock(return_value=[stage_row])
        r = tc.get("/api/tickets/1")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == 1
        assert data["draft"] is not None
        assert isinstance(data["draft"]["sources_used"], list)
        assert len(data["pipeline_stages"]) == 1

    def test_no_draft(self, client):
        tc, conn, _ = client
        conn.fetchrow = AsyncMock(side_effect=[TICKET_ROW, None])
        conn.fetch = AsyncMock(return_value=[])
        r = tc.get("/api/tickets/1")
        assert r.status_code == 200
        assert r.json()["draft"] is None

    def test_not_found_returns_404(self, client):
        tc, conn, _ = client
        conn.fetchrow = AsyncMock(return_value=None)
        r = tc.get("/api/tickets/999")
        assert r.status_code == 404


class TestApproveTicket:
    def test_success_sends_email(self, client):
        tc, conn, mock_send = client
        conn.fetchrow = AsyncMock(side_effect=[
            TICKET_ROW,
            {"id": 10, "draft_text": "Thank you for contacting support."},
        ])
        r = tc.post("/api/tickets/1/approve", json={"agent_name": "alice"})
        assert r.status_code == 200
        assert r.json()["status"] == "sent"
        mock_send.assert_called_once()

    def test_default_agent_name(self, client):
        tc, conn, _ = client
        conn.fetchrow = AsyncMock(side_effect=[
            TICKET_ROW,
            {"id": 10, "draft_text": "Reply."},
        ])
        r = tc.post("/api/tickets/1/approve", json={})
        assert r.status_code == 200

    def test_ticket_not_found(self, client):
        tc, conn, _ = client
        conn.fetchrow = AsyncMock(return_value=None)
        r = tc.post("/api/tickets/1/approve", json={})
        assert r.status_code == 404

    def test_ticket_already_sent_returns_409(self, client):
        tc, conn, _ = client
        conn.fetchrow = AsyncMock(return_value={**TICKET_ROW, "status": "sent"})
        r = tc.post("/api/tickets/1/approve", json={})
        assert r.status_code == 409

    def test_ticket_discarded_returns_409(self, client):
        tc, conn, _ = client
        conn.fetchrow = AsyncMock(return_value={**TICKET_ROW, "status": "discarded"})
        r = tc.post("/api/tickets/1/approve", json={})
        assert r.status_code == 409

    def test_no_draft_returns_409(self, client):
        tc, conn, _ = client
        conn.fetchrow = AsyncMock(side_effect=[TICKET_ROW, None])
        r = tc.post("/api/tickets/1/approve", json={})
        assert r.status_code == 409

    def test_email_failure_returns_failed_status(self, client):
        tc, conn, mock_send = client
        mock_send.side_effect = Exception("SMTP connection refused")
        conn.fetchrow = AsyncMock(side_effect=[
            TICKET_ROW,
            {"id": 10, "draft_text": "Draft text."},
        ])
        r = tc.post("/api/tickets/1/approve", json={})
        assert r.status_code == 200
        assert r.json()["status"] == "failed"


class TestDiscardTicket:
    def test_success(self, client):
        tc, conn, _ = client
        conn.execute = AsyncMock(return_value="UPDATE 1")
        r = tc.post("/api/tickets/1/discard")
        assert r.status_code == 200
        assert r.json()["status"] == "discarded"

    def test_ticket_not_pending_returns_409(self, client):
        tc, conn, _ = client
        conn.execute = AsyncMock(return_value="UPDATE 0")
        r = tc.post("/api/tickets/1/discard")
        assert r.status_code == 409
