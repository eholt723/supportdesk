"""Shared test helpers used across the test suite."""
import sys
from unittest.mock import AsyncMock, MagicMock

# Stub heavy optional dependencies not installed in the test environment.
# Must happen before any app module is imported.
sys.modules.setdefault("fastembed", MagicMock())


class AsyncIter:
    """Wraps a list as an async iterable — used to mock streaming LLM responses."""

    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration


def make_mock_pool(fetchrow=None, fetchval=None, fetch=None, execute="UPDATE 1"):
    """Return (pool, conn) mocks wired together for DB patching."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=fetchrow)
    mock_conn.fetchval = AsyncMock(return_value=fetchval)
    mock_conn.fetch = AsyncMock(return_value=fetch if fetch is not None else [])
    mock_conn.execute = AsyncMock(return_value=execute)
    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=False),
        )
    )
    return mock_pool, mock_conn
