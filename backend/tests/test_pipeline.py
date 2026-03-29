"""Unit tests for the pipeline orchestration logic."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def make_mock_pool(fetchrow=None, fetchval=None):
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=fetchrow)
    mock_conn.fetchval = AsyncMock(return_value=fetchval)
    mock_conn.execute = AsyncMock()
    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))
    return mock_pool


@pytest.mark.asyncio
async def test_pipeline_skips_missing_ticket():
    """Pipeline should exit silently if ticket_id not found."""
    from app.pipeline import run_pipeline

    mock_pool = make_mock_pool(fetchrow=None)

    with patch("app.pipeline.get_pool", return_value=mock_pool), \
         patch("app.pipeline.event_bus.broadcast", new_callable=AsyncMock), \
         patch("app.pipeline._run_stage", new_callable=AsyncMock) as mock_stage:
        await run_pipeline(9999)
        mock_stage.assert_not_called()


@pytest.mark.asyncio
async def test_run_stage_marks_failed_on_exception():
    from app.pipeline import _run_stage

    mock_pool = make_mock_pool(fetchval=1)

    async def bad_fn():
        raise ValueError("boom")

    with patch("app.pipeline.get_pool", return_value=mock_pool), \
         patch("app.pipeline.event_bus.broadcast", new_callable=AsyncMock):
        result = await _run_stage(1, "classify", bad_fn)

    assert result is None


@pytest.mark.asyncio
async def test_run_stage_returns_result_on_success():
    from app.pipeline import _run_stage

    mock_pool = make_mock_pool(fetchval=1)

    async def good_fn():
        return {"type": "billing", "urgency": "high", "confidence": 0.9}

    with patch("app.pipeline.get_pool", return_value=mock_pool), \
         patch("app.pipeline.event_bus.broadcast", new_callable=AsyncMock):
        result = await _run_stage(1, "classify", good_fn)

    assert result == {"type": "billing", "urgency": "high", "confidence": 0.9}
