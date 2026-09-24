"""Validated output crossing from turn execution into atomic finalization."""

from __future__ import annotations

from dataclasses import dataclass

from .compaction import ModelCompaction
from .context import BuiltContext
from .executor import ExecutorResult
from .memory_policy import PreparedMemoryReview
from .natural_memory_policy import PreparedNaturalReview
from .natural_memory_reviewer import NaturalReviewerResult
from .reviewer import ReviewerResult


@dataclass(frozen=True)
class AttemptResult:
    assistant_text: str
    context: BuiltContext
    executor: ExecutorResult
    reviewer: ReviewerResult | NaturalReviewerResult
    review: PreparedMemoryReview | PreparedNaturalReview
    operation_embeddings: tuple[list[float] | None, ...]
    embedding_fingerprint: str
    embedding_dimensions: int
    retrieval_policy_version: str
    compaction: ModelCompaction | None
    natural_source_message_ids: tuple[str, ...] = ()
