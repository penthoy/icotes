"""Shared async retry helpers for transient httpx transport failures."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

T = TypeVar("T")


def is_transient_transport_error(exc: Exception) -> bool:
    """Return True for errors that are often fixed by recreating HTTP clients."""
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, RuntimeError):
        message = str(exc).lower()
        if "handler is closed" in message or "tcptransport" in message or "event loop is closed" in message:
            return True
    return False


async def retry_async_operation(
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay_seconds: float = 0.25,
    should_retry: Callable[[Exception], bool] = is_transient_transport_error,
    on_retry_reset: Callable[[], Awaitable[None]] | None = None,
    logger: logging.Logger | None = None,
    operation_name: str = "operation",
) -> T:
    """Retry an async operation when known transient transport errors occur."""
    last_exception: Exception | None = None

    for attempt in range(max_attempts):
        try:
            return await operation()
        except Exception as exc:
            last_exception = exc
            if not should_retry(exc) or attempt == max_attempts - 1:
                raise

            if logger is not None:
                logger.warning(
                    "Transient transport error during %s (attempt %s/%s). Resetting client and retrying: %s",
                    operation_name,
                    attempt + 1,
                    max_attempts,
                    exc,
                )

            if on_retry_reset is not None:
                try:
                    await on_retry_reset()
                except Exception:
                    pass

            await asyncio.sleep(base_delay_seconds * (attempt + 1))

    if last_exception is not None:
        raise last_exception
    raise RuntimeError(f"Retry operation '{operation_name}' failed without exception details")
