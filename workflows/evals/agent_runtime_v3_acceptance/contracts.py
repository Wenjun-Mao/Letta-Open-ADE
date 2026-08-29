from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from agent_runtime_eval_contracts import (
    EventObservation,
    FactObservation,
    ToolObservation,
    TurnObservation,
    score_case,
)


class ContractBoundaryError(RuntimeError):
    pass


def observation_instance(kind: type[Any], payload: dict[str, Any]) -> Any:
    """Construct a shared-contract observation without retaining local duplicates."""
    try:
        signature = inspect.signature(kind)
    except (TypeError, ValueError) as exc:
        raise ContractBoundaryError(f"cannot inspect shared contract {kind!r}") from exc
    parameters = signature.parameters
    if any(item.kind is item.VAR_KEYWORD for item in parameters.values()):
        return kind(**payload)
    accepted = {
        name: value
        for name, value in payload.items()
        if name in parameters
        and parameters[name].kind is not parameters[name].POSITIONAL_ONLY
    }
    try:
        return kind(**accepted)
    except TypeError as exc:
        raise ContractBoundaryError(
            f"shared contract {getattr(kind, '__name__', kind)!r} rejected normalized observation"
        ) from exc


def score_observations(case: object, observations: dict[str, Any]) -> dict[str, Any]:
    """Use the canonical scorer while keeping API normalization local to this workflow."""
    scorer = _callable(score_case)
    parameters = inspect.signature(scorer).parameters
    if "observations" in parameters:
        result = scorer(case=case, observations=observations)
    else:
        candidates = {
            "case": case,
            "facts_by_subject": observations["facts_by_subject"],
            "turns_by_conversation": observations["turns_by_conversation"],
            "events_by_run": observations["events_by_run"],
            "tools_by_run": observations["tools_by_run"],
        }
        supported = {
            key: value for key, value in candidates.items() if key in parameters
        }
        if "case" not in supported or len(supported) == 1:
            raise ContractBoundaryError(
                "shared score_case has no supported observation input"
            )
        result = scorer(**supported)
    if not isinstance(result, dict):
        raise ContractBoundaryError("shared score_case must return a mapping")
    return result


def _callable(value: Callable[..., object]) -> Callable[..., Any]:
    return value


__all__ = [
    "ContractBoundaryError",
    "EventObservation",
    "FactObservation",
    "ToolObservation",
    "TurnObservation",
    "observation_instance",
    "score_observations",
]
