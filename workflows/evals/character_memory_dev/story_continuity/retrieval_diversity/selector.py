"""Offline novelty-penalized selection experiment; never wired into runtime."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime


LIMIT = 4


@dataclass(frozen=True)
class Window:
    id: str
    assistant_at: str
    text: str


def _bigrams(text: str) -> frozenset[str]:
    normalized = "".join(char.casefold() for char in text if char.isalnum())
    return frozenset(
        normalized[index : index + 2] for index in range(len(normalized) - 1)
    )


def select_diverse(
    windows: Sequence[Window], relevance: Mapping[str, float]
) -> list[str]:
    """Select complete source IDs, with no scorer annotations or episode labels.

    Eligibility belongs to the caller. No scope queries, synthetic sources,
    provider calls, source merging or inference of correction authority occur here.
    """
    ids = [window.id for window in windows]
    if len(set(ids)) != len(ids) or set(relevance) != set(ids):
        raise ValueError("scores must cover unique source IDs exactly")
    if any(
        not math.isfinite(score) or not 0 <= score <= 1 for score in relevance.values()
    ):
        raise ValueError("this lexical experiment requires finite relevance in [0, 1]")
    times = {}
    for window in windows:
        if not window.id or not window.text.strip():
            raise ValueError("source ID and text must be nonempty")
        timestamp = datetime.fromisoformat(window.assistant_at)
        if timestamp.utcoffset() is None:
            raise ValueError("source timestamp must be timezone-aware")
        times[window.id] = timestamp
    remaining = sorted(windows, key=lambda window: window.id)
    remaining.sort(key=lambda window: times[window.id], reverse=True)
    features = {window.id: _bigrams(window.text) for window in remaining}
    selected: list[str] = []

    def utility(window: Window) -> float:
        candidate = features[window.id]
        overlaps = []
        for source_id in selected:
            other = features[source_id]
            union = candidate | other
            overlaps.append(len(candidate & other) / len(union) if union else 0.0)
        return relevance[window.id] * (1 - max(overlaps, default=0.0))

    while remaining and len(selected) < LIMIT:
        # max preserves the pre-established chronology/ID ordering on ties.
        choice = max(remaining, key=utility)
        selected.append(choice.id)
        remaining.remove(choice)
    return selected
