"""Generic async job polling utility with timeout and exponential backoff."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import TypeVar

T = TypeVar("T")


class AsyncJobPoller:
    """Poll asynchronous jobs until complete, failed, or timed out."""

    def __init__(
        self,
        *,
        initial_interval: float = 2.0,
        backoff_factor: float = 1.2,
        max_interval: float = 10.0,
    ):
        self.initial_interval = initial_interval
        self.backoff_factor = backoff_factor
        self.max_interval = max_interval

    async def poll_until_terminal(
        self,
        *,
        fetch_status: Callable[[], Awaitable[T]],
        is_complete: Callable[[T], bool],
        is_failed: Callable[[T], bool],
        timeout_seconds: float,
        on_timeout: Callable[[], Exception],
        on_failure: Callable[[T], Exception],
    ) -> T:
        """Poll status endpoint until terminal state and return final payload."""
        start_time = datetime.now()
        max_wait = timedelta(seconds=timeout_seconds)
        current_interval = self.initial_interval

        while True:
            if datetime.now() - start_time > max_wait:
                raise on_timeout()

            status_payload = await fetch_status()

            if is_complete(status_payload):
                return status_payload

            if is_failed(status_payload):
                raise on_failure(status_payload)

            await asyncio.sleep(current_interval)
            current_interval = min(current_interval * self.backoff_factor, self.max_interval)
