from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class FactObservation:
    """The stable fact fields used by deterministic fixture scoring."""

    key: str
    value: str


@dataclass(frozen=True)
class EventObservation:
    """A normalized runtime event name without workflow-specific payloads."""

    type: str


@dataclass(frozen=True)
class ToolObservation:
    """The tool outcome fields used by deterministic fixture scoring."""

    name: str
    succeeded: bool


@dataclass(frozen=True)
class TurnObservation:
    """A runtime-neutral turn representation for score calculation."""

    status: str
    assistant_text: str | None
    candidate_assistant_text: str | None
    events: tuple[EventObservation, ...] = ()
    tools: tuple[ToolObservation, ...] = ()
    usage: Mapping[str, int] = field(default_factory=dict)
    elapsed_seconds: float = 0.0
