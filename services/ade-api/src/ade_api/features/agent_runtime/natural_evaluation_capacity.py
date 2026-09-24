"""Immutable, evaluation-only capacity binding for natural-memory checkpoint 6.

The provider deployment fingerprint remains the actual catalog identity. These
smaller role limits are an additional persisted evaluation contract, never a
replacement fingerprint or a production deployment setting.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .context import ContextBudget
from .errors import RuntimeValidationError


CONTRACT_ID = "natural-memory-checkpoint6-v1"
DEEPSEEK_ROUTE = "deepseek::deepseek-flash"
_LIMITS = {
    "conversation": {
        "context_window": 4096,
        "max_output_tokens": 512,
        "max_model_requests": 2,
    },
    "reviewer": {
        "context_window": 8192,
        "max_output_tokens": 1024,
        "max_model_requests": 1,
    },
}


@dataclass(frozen=True)
class NaturalEvaluationCapacity:
    conversation: ContextBudget
    reviewer: ContextBudget
    conversation_requests: int
    reviewer_shared_suffix_tokens: int


def bind_checkpoint6_capacity(prepared: dict[str, Any]) -> dict[str, Any]:
    """Add the exact approved limits after real catalog deployment resolution."""

    bound = deepcopy(prepared)
    snapshots = bound.get("deployment_snapshot")
    if not isinstance(snapshots, list):
        raise RuntimeValidationError(
            "Natural evaluation deployment snapshot is missing"
        )
    roles = {snapshot.get("role"): snapshot for snapshot in snapshots}
    if set(roles) != {"conversation", "reviewer", "retriever"}:
        raise RuntimeValidationError(
            "Natural evaluation requires three deployment roles"
        )
    for role in ("conversation", "reviewer"):
        snapshot = roles[role]
        if snapshot.get("route_alias") != DEEPSEEK_ROUTE:
            raise RuntimeValidationError("Natural evaluation DeepSeek route differs")
        snapshot["natural_evaluation_capacity"] = {
            "contract": CONTRACT_ID,
            "deployment_fingerprint": snapshot["fingerprint"],
            **_LIMITS[role],
        }
    return bound


def checked_checkpoint6_capacity(
    definition: dict[str, Any], *, purpose: str, natural_variant: str | None
) -> NaturalEvaluationCapacity | None:
    snapshots = definition.get("deployment_snapshot")
    if not isinstance(snapshots, list):
        return None
    roles = {snapshot.get("role"): snapshot for snapshot in snapshots}
    present = {
        role
        for role, snapshot in roles.items()
        if isinstance(snapshot, dict) and "natural_evaluation_capacity" in snapshot
    }
    if not present:
        return None
    if (
        purpose != "evaluation"
        or natural_variant not in {"A", "A0", "B"}
        or present != {"conversation", "reviewer"}
        or set(roles) != {"conversation", "reviewer", "retriever"}
    ):
        raise RuntimeValidationError("Natural evaluation capacity is outside its scope")
    for role in ("conversation", "reviewer"):
        snapshot = roles[role]
        profile = snapshot["natural_evaluation_capacity"]
        expected = {
            "contract": CONTRACT_ID,
            "deployment_fingerprint": snapshot.get("fingerprint"),
            **_LIMITS[role],
        }
        if profile != expected or snapshot.get("route_alias") != DEEPSEEK_ROUTE:
            raise RuntimeValidationError("Natural evaluation capacity binding differs")
        provider_context = snapshot.get("fingerprint_payload", {}).get(
            "context_settings", {}
        )
        if (
            not isinstance(provider_context, dict)
            or int(provider_context.get("total_tokens") or 0)
            < _LIMITS[role]["context_window"]
            or int(provider_context.get("max_output_tokens") or 0)
            < _LIMITS[role]["max_output_tokens"]
            or int(provider_context.get("max_model_requests") or 0)
            < _LIMITS[role]["max_model_requests"]
        ):
            raise RuntimeValidationError("Natural evaluation exceeds provider capacity")
    reviewer_context = roles["reviewer"]["fingerprint_payload"]["context_settings"]
    if reviewer_context.get("reviewer_repair_count") != 0:
        raise RuntimeValidationError("Natural evaluation requires zero reviewer repair")
    conversation = ContextBudget(
        context_window=4096, max_output_tokens=512, tool_schema_tokens=256
    )
    reviewer = ContextBudget(
        context_window=8192, max_output_tokens=1024, tool_schema_tokens=0
    )
    if conversation.input_limit != 3072 or reviewer.input_limit != 6759:
        raise RuntimeValidationError("Natural evaluation input limits drifted")
    return NaturalEvaluationCapacity(
        conversation=conversation,
        reviewer=reviewer,
        conversation_requests=2,
        reviewer_shared_suffix_tokens=640,
    )
