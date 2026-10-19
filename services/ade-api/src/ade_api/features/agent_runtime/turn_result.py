"""Validated output crossing from turn execution into atomic finalization."""

from __future__ import annotations

from dataclasses import dataclass

from .compaction import ModelCompaction
from .context import BuiltContext
from .executor import ExecutorResult


@dataclass(frozen=True)
class AttemptResult:
    assistant_text: str
    context: BuiltContext
    executor: ExecutorResult
    compaction: ModelCompaction | None
    memory_lookups: tuple[dict, ...] = ()
