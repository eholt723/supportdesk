"""Unit tests for ticket classification response parsing."""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def make_mock_response(content: str):
    mock_msg = MagicMock()
    mock_msg.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    return mock_resp


@pytest.mark.asyncio
async def test_classify_billing():
    from app.classify import classify_ticket
    mock_resp = make_mock_response('{"type": "billing", "urgency": "high", "confidence": 0.92}')
    with patch("app.classify._get_client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_client_fn.return_value = mock_client
        result = await classify_ticket("Cancel subscription", "I can't cancel and keep getting charged")
    assert result["type"] == "billing"
    assert result["urgency"] == "high"
    assert result["confidence"] == 0.92


@pytest.mark.asyncio
async def test_classify_fallback_on_bad_json():
    from app.classify import classify_ticket
    mock_resp = make_mock_response("I cannot classify this.")
    with patch("app.classify._get_client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_client_fn.return_value = mock_client
        result = await classify_ticket("Hello", "Hello")
    assert result["type"] == "general"
    assert result["urgency"] == "medium"


@pytest.mark.asyncio
async def test_classify_normalizes_invalid_type():
    from app.classify import classify_ticket
    mock_resp = make_mock_response('{"type": "unknown_type", "urgency": "low", "confidence": 0.5}')
    with patch("app.classify._get_client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_client_fn.return_value = mock_client
        result = await classify_ticket("Something weird", "body")
    assert result["type"] == "general"
