"""Tests for icpy.core.async_job_poller — generic async polling helper."""

import pytest
from unittest.mock import AsyncMock

from icpy.core.async_job_poller import AsyncJobPoller


@pytest.fixture
def poller():
    """Create a poller with fast intervals for testing."""
    return AsyncJobPoller(initial_interval=0.01, backoff_factor=1.0, max_interval=0.01)


class TestAsyncJobPoller:
    """Verify polling semantics: success, failure, timeout."""

    @pytest.mark.asyncio
    async def test_immediate_completion(self, poller):
        """If first fetch is already complete, return immediately."""
        fetch = AsyncMock(return_value={"status": "done"})

        result = await poller.poll_until_terminal(
            fetch_status=fetch,
            is_complete=lambda s: s["status"] == "done",
            is_failed=lambda s: s["status"] == "failed",
            timeout_seconds=5,
            on_timeout=lambda: TimeoutError("timeout"),
            on_failure=lambda s: RuntimeError("failed"),
        )

        assert result == {"status": "done"}
        assert fetch.await_count == 1

    @pytest.mark.asyncio
    async def test_completes_after_several_polls(self, poller):
        """Should keep polling until status transitions to complete."""
        statuses = [
            {"status": "processing"},
            {"status": "processing"},
            {"status": "done"},
        ]
        fetch = AsyncMock(side_effect=statuses)

        result = await poller.poll_until_terminal(
            fetch_status=fetch,
            is_complete=lambda s: s["status"] == "done",
            is_failed=lambda s: s["status"] == "failed",
            timeout_seconds=5,
            on_timeout=lambda: TimeoutError("timeout"),
            on_failure=lambda s: RuntimeError("failed"),
        )

        assert result == {"status": "done"}
        assert fetch.await_count == 3

    @pytest.mark.asyncio
    async def test_raises_on_failure(self, poller):
        """Should raise on_failure exception when status is failed."""
        fetch = AsyncMock(return_value={"status": "failed", "error": "boom"})

        with pytest.raises(RuntimeError, match="boom"):
            await poller.poll_until_terminal(
                fetch_status=fetch,
                is_complete=lambda s: s["status"] == "done",
                is_failed=lambda s: s["status"] == "failed",
                timeout_seconds=5,
                on_timeout=lambda: TimeoutError("timeout"),
                on_failure=lambda s: RuntimeError(s["error"]),
            )

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self, poller):
        """Should raise on_timeout exception when elapsed > timeout."""
        # fetch always returns processing → will trigger timeout
        fetch = AsyncMock(return_value={"status": "processing"})

        with pytest.raises(TimeoutError, match="timeout"):
            await poller.poll_until_terminal(
                fetch_status=fetch,
                is_complete=lambda s: False,
                is_failed=lambda s: False,
                timeout_seconds=0.05,  # 50ms
                on_timeout=lambda: TimeoutError("timeout"),
                on_failure=lambda s: RuntimeError("failed"),
            )

        # Should have polled at least once
        assert fetch.await_count >= 1

    @pytest.mark.asyncio
    async def test_backoff_increases_interval(self):
        """Verify backoff factor increases sleep interval (indirectly via poll count)."""
        # With very short timeout and increasing intervals, should poll fewer times
        poller_fast = AsyncJobPoller(initial_interval=0.01, backoff_factor=1.0, max_interval=0.01)
        poller_slow = AsyncJobPoller(initial_interval=0.02, backoff_factor=2.0, max_interval=1.0)

        fetch_fast = AsyncMock(return_value={"status": "processing"})
        fetch_slow = AsyncMock(return_value={"status": "processing"})

        with pytest.raises(TimeoutError):
            await poller_fast.poll_until_terminal(
                fetch_status=fetch_fast,
                is_complete=lambda s: False,
                is_failed=lambda s: False,
                timeout_seconds=0.1,
                on_timeout=lambda: TimeoutError("t"),
                on_failure=lambda s: RuntimeError("f"),
            )

        with pytest.raises(TimeoutError):
            await poller_slow.poll_until_terminal(
                fetch_status=fetch_slow,
                is_complete=lambda s: False,
                is_failed=lambda s: False,
                timeout_seconds=0.1,
                on_timeout=lambda: TimeoutError("t"),
                on_failure=lambda s: RuntimeError("f"),
            )

        # Faster poller should poll more times than slower one
        assert fetch_fast.await_count >= fetch_slow.await_count
