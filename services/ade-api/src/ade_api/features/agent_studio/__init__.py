"""Agent Studio public interface without runtime initialization side effects."""

from importlib import import_module
from typing import Any


__all__ = ["ensure_agent_not_archived"]


def __getattr__(name: str) -> Any:
    if name == "ensure_agent_not_archived":
        return getattr(import_module(".access", __name__), name)
    raise AttributeError(name)
