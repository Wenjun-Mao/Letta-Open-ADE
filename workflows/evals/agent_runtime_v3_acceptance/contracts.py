from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from agent_runtime_eval_contracts import (
    EventObservation,
    FactObservation,
    ToolObservation,
    TurnObservation,
    score_case,
)


def score_observations(
    *,
    case: Any,
    facts_by_subject: Mapping[str, Sequence[FactObservation]],
    results_by_conversation: Mapping[str, Sequence[TurnObservation]],
) -> dict[str, Any]:
    """Score only through the versioned shared evaluation contract."""
    return score_case(
        case=case,
        facts_by_subject=facts_by_subject,
        results_by_conversation=results_by_conversation,
    )


__all__ = [
    "EventObservation",
    "FactObservation",
    "ToolObservation",
    "TurnObservation",
    "score_observations",
]
