from __future__ import annotations

import asyncio

import pytest

from ade_api.features.agent_runtime_v3.retry import execute_with_retries
from ade_api.features.agent_runtime_v3.router_transport import RouterRequestError


def test_zero_retry_means_exactly_one_attempt() -> None:
    attempts = []

    async def operation(attempt: int):
        attempts.append(attempt)
        raise RouterRequestError("timeout", retryable=True)

    with pytest.raises(RouterRequestError):
        asyncio.run(execute_with_retries(operation, retry_count=0))
    assert attempts == [1]


def test_two_retries_mean_exactly_three_attempts() -> None:
    attempts = []
    delays = []

    async def operation(attempt: int):
        attempts.append(attempt)
        if attempt < 3:
            raise RouterRequestError("temporary", retryable=True)
        return "ok"

    async def sleep(delay: float):
        delays.append(delay)

    result = asyncio.run(
        execute_with_retries(
            operation,
            retry_count=2,
            sleep=sleep,
            random_value=lambda: 0.5,
        )
    )
    assert result == "ok"
    assert attempts == [1, 2, 3]
    assert delays == [0.25, 0.5]


def test_non_transient_error_never_retries() -> None:
    attempts = []

    async def operation(attempt: int):
        attempts.append(attempt)
        raise RouterRequestError("bad request", retryable=False, status_code=400)

    with pytest.raises(RouterRequestError):
        asyncio.run(execute_with_retries(operation, retry_count=5))
    assert attempts == [1]
