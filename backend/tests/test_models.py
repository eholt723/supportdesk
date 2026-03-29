"""Unit tests for Pydantic model validation."""
import pytest
from pydantic import ValidationError


class TestWebhookPayload:
    def test_valid(self):
        from app.models import WebhookPayload
        p = WebhookPayload(email="a@b.com", subject="Hi", body="Hello", timestamp=1700000000)
        assert p.email == "a@b.com"
        assert p.timestamp == 1700000000

    def test_missing_email_raises(self):
        from app.models import WebhookPayload
        with pytest.raises(ValidationError):
            WebhookPayload(subject="Hi", body="Hello", timestamp=1700000000)

    def test_missing_subject_raises(self):
        from app.models import WebhookPayload
        with pytest.raises(ValidationError):
            WebhookPayload(email="a@b.com", body="Hello", timestamp=1700000000)

    def test_missing_body_raises(self):
        from app.models import WebhookPayload
        with pytest.raises(ValidationError):
            WebhookPayload(email="a@b.com", subject="Hi", timestamp=1700000000)

    def test_missing_timestamp_raises(self):
        from app.models import WebhookPayload
        with pytest.raises(ValidationError):
            WebhookPayload(email="a@b.com", subject="Hi", body="Hello")


class TestClassifyResult:
    def test_valid(self):
        from app.models import ClassifyResult
        r = ClassifyResult(type="billing", urgency="high", confidence=0.92)
        assert r.type == "billing"
        assert r.confidence == 0.92

    def test_confidence_as_int_coerced(self):
        from app.models import ClassifyResult
        r = ClassifyResult(type="general", urgency="low", confidence=1)
        assert r.confidence == 1.0

    def test_missing_field_raises(self):
        from app.models import ClassifyResult
        with pytest.raises(ValidationError):
            ClassifyResult(type="billing", urgency="high")


class TestApproveRequest:
    def test_default_agent_name(self):
        from app.models import ApproveRequest
        r = ApproveRequest()
        assert r.agent_name == "agent"

    def test_custom_agent_name(self):
        from app.models import ApproveRequest
        r = ApproveRequest(agent_name="alice")
        assert r.agent_name == "alice"

    def test_none_agent_name(self):
        from app.models import ApproveRequest
        r = ApproveRequest(agent_name=None)
        assert r.agent_name is None


class TestTicketCreate:
    def test_valid(self):
        from app.models import TicketCreate
        t = TicketCreate(source_email="x@y.com", subject="Issue", body="Details")
        assert t.source_email == "x@y.com"

    def test_missing_fields_raises(self):
        from app.models import TicketCreate
        with pytest.raises(ValidationError):
            TicketCreate(source_email="x@y.com")


class TestKBChunk:
    def test_valid(self):
        from app.models import KBChunk
        c = KBChunk(id=1, document_name="Billing FAQ", chunk_text="...", score=0.87)
        assert c.score == 0.87

    def test_score_as_int_coerced(self):
        from app.models import KBChunk
        c = KBChunk(id=1, document_name="Doc", chunk_text="...", score=1)
        assert c.score == 1.0


class TestDraftResponse:
    def test_valid(self):
        from app.models import DraftResponse
        d = DraftResponse(
            ticket_id=1,
            draft_text="Hello, thank you for reaching out.",
            sources_used=[{"document_name": "FAQ", "chunk_text": "...", "score": 0.9}],
            confidence_score=0.9,
        )
        assert d.ticket_id == 1
        assert len(d.sources_used) == 1

    def test_empty_sources(self):
        from app.models import DraftResponse
        d = DraftResponse(ticket_id=2, draft_text="Reply", sources_used=[], confidence_score=0.5)
        assert d.sources_used == []
