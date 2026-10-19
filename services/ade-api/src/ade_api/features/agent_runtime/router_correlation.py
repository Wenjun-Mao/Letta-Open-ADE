"""Task-local correlation without modifying model payloads or transport callers."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class RouterCorrelation:
    headers: dict[str, str] = field(default_factory=dict)
    router_request_id: str | None = None


_CURRENT: ContextVar[RouterCorrelation | None] = ContextVar(
    "ade_router_correlation", default=None
)


@contextmanager
def correlate_request(metadata: dict):
    correlation = RouterCorrelation(
        headers={
            f"X-ADE-{key.replace('_', '-')}": str(value)
            for key, value in metadata.items()
        }
    )
    token = _CURRENT.set(correlation)
    try:
        yield correlation
    finally:
        _CURRENT.reset(token)


def correlation_headers() -> dict[str, str]:
    current = _CURRENT.get()
    return dict(current.headers) if current else {}


def receive_router_identity(value: str | None) -> None:
    current = _CURRENT.get()
    if current is not None and value:
        try:
            current.router_request_id = str(UUID(value))
        except ValueError:
            pass
