"""Tests for icpy.core.http_retry — shared async retry helpers."""

import pytest
from unittest.mock import AsyncMock

import httpx

from icpy.core.http_retry import is_transient_transport_error, retry_async_operation


# ── is_transient_transport_error ────────────────────────────────────────────


class TestIsTransientTransportError:
    """Verify the classifier recognises known transient errors."""

    def test_httpx_transport_error(self):
        assert is_transient_transport_error(httpx.TransportError("connection reset"))

    def test_runtime_handler_closed(self):
        exc = RuntimeError("unable to perform operation on <TCPTransport>; the handler is closed")
        assert is_transient_transport_error(exc)

    def test_runtime_event_loop_closed(self):
        exc = RuntimeError("Event loop is closed")
        assert is_transient_transport_error(exc)

    def test_value_error_not_transient(self):
        assert not is_transient_transport_error(ValueError("bad input"))

    def test_plain_runtime_error_not_transient(self):
        assert not is_transient_transport_error(RuntimeError("unrelated error"))


# ── retry_async_operation ───────────────────────────────────────────────────


class TestRetryAsyncOperation:
    """Verify retry semantics for the generic helper."""

    @pytest.mark.asyncio
    async def test_succeeds_first_try(self):
        op = AsyncMock(return_value="ok")
        result = await retry_async_operation(op)
        assert result == "ok"
        assert op.await_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self):
        """Should retry after transient transport error and succeed."""
        op = AsyncMock(
            side_effect=[httpx.TransportError("conn reset"), "recovered"]
        )
        reset_fn = AsyncMock()

        result = await retry_async_operation(
            op,
            on_retry_reset=reset_fn,
            operation_name="test-op",
        )

        assert result == "recovered"
        assert op.await_count == 2
        reset_fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_non_transient_immediately(self):
        """Non-transient errors should propagate without retry."""
        op = AsyncMock(side_effect=ValueError("bad"))

        with pytest.raises(ValueError, match="bad"):
            await retry_async_operation(op)

        assert op.await_count == 1

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self):
        """Should give up after max_attempts even for transient errors."""
        op = AsyncMock(side_effect=httpx.TransportError("always fails"))

        with pytest.raises(httpx.TransportError):
            await retry_async_operation(op, max_attempts=2, base_delay_seconds=0.01)

        assert op.await_count == 2

    @pytest.mark.asyncio
    async def test_custom_should_retry_predicate(self):
        """Custom predicate controls which exceptions trigger retry."""
        op = AsyncMock(side_effect=[ValueError("retry me"), "ok"])

        result = await retry_async_operation(
            op,
            should_retry=lambda e: isinstance(e, ValueError),
            base_delay_seconds=0.01,
        )

        assert result == "ok"
        assert op.await_count == 2

    @pytest.mark.asyncio
    async def test_reset_failure_does_not_abort(self):
        """If on_retry_reset raises, retry should still continue."""
        reset_fn = AsyncMock(side_effect=RuntimeError("reset boom"))
        op = AsyncMock(side_effect=[httpx.TransportError("err"), "ok"])

        result = await retry_async_operation(
            op,
            on_retry_reset=reset_fn,
            base_delay_seconds=0.01,
        )

        assert result == "ok"
