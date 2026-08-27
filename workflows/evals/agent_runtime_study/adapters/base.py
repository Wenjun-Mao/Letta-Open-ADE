from __future__ import annotations

from typing import Any

from ..contracts import RunEventType


class ExecutorError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        retryable: bool,
        events: tuple[tuple[RunEventType, dict[str, Any]], ...] = (),
        raw_messages: tuple[dict[str, Any], ...] = (),
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.events = events
        self.raw_messages = raw_messages


class RetryableModelError(ExecutorError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, retryable=True, **kwargs)


class NonRetryableModelError(ExecutorError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, retryable=False, **kwargs)


class ModelProtocolError(NonRetryableModelError):
    pass


def with_trace(
    error: ExecutorError,
    *,
    events: list[tuple[RunEventType, dict[str, Any]]],
    raw_messages: list[dict[str, Any]],
) -> ExecutorError:
    error.events = tuple(events)
    error.raw_messages = tuple(raw_messages)
    return error
