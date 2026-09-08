from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from .router_transport import RouterRequestError


T = TypeVar("T")
AttemptCallable = Callable[[int], Awaitable[T]]
RetryEventCallable = Callable[[int, int, float, Exception], Awaitable[None]]


async def execute_with_retries(
    operation: AttemptCallable[T],
    *,
    retry_count: int,
    on_retry: RetryEventCallable | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    random_value: Callable[[], float] = random.random,
) -> T:
    if not 0 <= retry_count <= 5:
        raise ValueError("retry_count must be between 0 and 5")
    last_error: Exception | None = None
    for attempt in range(1, retry_count + 2):
        try:
            return await operation(attempt)
        except Exception as exc:
            last_error = exc
            if attempt > retry_count or not is_retryable(exc):
                raise
            ceiling = min(4.0, 0.5 * (2 ** (attempt - 1)))
            delay = ceiling * max(0.0, min(1.0, random_value()))
            retry_after = getattr(exc, "retry_after_seconds", None)
            if isinstance(retry_after, int | float) and not isinstance(
                retry_after, bool
            ):
                delay = max(delay, min(4.0, max(0.0, float(retry_after))))
            if on_retry is not None:
                await on_retry(attempt, attempt + 1, delay, exc)
            await sleep(delay)
    assert last_error is not None
    raise last_error


def is_retryable(exc: Exception) -> bool:
    if isinstance(exc, RouterRequestError):
        return exc.retryable
    return isinstance(
        exc,
        (
            TimeoutError,
            asyncio.TimeoutError,
            ConnectionError,
        ),
    )
