"""Frozen, evaluation-only H4 capacity binding for the history probe."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .context import ContextBudget
from .errors import RuntimeValidationError
from .natural_context import HISTORY_PROBE_POLICY
from .natural_evaluation_capacity import (
    DEEPSEEK_ROUTE,
    NaturalEvaluationCapacity,
)

HISTORY_CAPACITY_CONTRACT = "natural-history-probe-h4-v2"
CONVERSATION_BUDGET = ContextBudget(
    context_window=16_384, max_output_tokens=4_096, tool_schema_tokens=256
)
# 16_384 - 4_096 - floor(16_384 * .05) = 11_469 input tokens.
REVIEWER_BUDGET = ContextBudget(
    context_window=16_384, max_output_tokens=4_096, tool_schema_tokens=0
)
ROLE_LIMITS = {
    "conversation": {
        "context_window": 16_384,
        "max_output_tokens": 4_096,
        "max_model_requests": 2,
    },
    "reviewer": {
        "context_window": 16_384,
        "max_output_tokens": 4_096,
        "max_model_requests": 1,
    },
}


def bind_history_probe_capacity(prepared: dict[str, Any]) -> dict[str, Any]:
    bound = deepcopy(prepared)
    if bound.get("memory_policy_version") != HISTORY_PROBE_POLICY:
        raise RuntimeValidationError("H4 capacity requires the history probe policy")
    snapshots = bound.get("deployment_snapshot")
    if not isinstance(snapshots, list):
        raise RuntimeValidationError("H4 deployment snapshot is missing")
    roles = {snapshot.get("role"): snapshot for snapshot in snapshots}
    if set(roles) != {"conversation", "reviewer", "retriever"}:
        raise RuntimeValidationError("H4 requires three deployment roles")
    for role, limits in ROLE_LIMITS.items():
        snapshot = roles[role]
        if snapshot.get("route_alias") != DEEPSEEK_ROUTE:
            raise RuntimeValidationError("H4 DeepSeek route differs")
        snapshot["natural_evaluation_capacity"] = {
            "contract": HISTORY_CAPACITY_CONTRACT,
            "deployment_fingerprint": snapshot["fingerprint"],
            **limits,
        }
    return bound


def checked_history_probe_capacity(
    definition: dict[str, Any], *, purpose: str
) -> NaturalEvaluationCapacity | None:
    snapshots = definition.get("deployment_snapshot")
    if not isinstance(snapshots, list):
        raise RuntimeValidationError("H4 deployment snapshot is missing")
    roles = {snapshot.get("role"): snapshot for snapshot in snapshots}
    if set(roles) != {"conversation", "reviewer", "retriever"}:
        raise RuntimeValidationError("H4 requires three deployment roles")
    present = {
        role
        for role, snapshot in roles.items()
        if "natural_evaluation_capacity" in snapshot
    }
    if not present:
        return None
    if (
        purpose != "evaluation"
        or definition.get("memory_policy_version") != HISTORY_PROBE_POLICY
        or present != {"conversation", "reviewer"}
    ):
        raise RuntimeValidationError("H4 capacity is outside evaluation history scope")
    for role, limits in ROLE_LIMITS.items():
        snapshot = roles[role]
        expected = {
            "contract": HISTORY_CAPACITY_CONTRACT,
            "deployment_fingerprint": snapshot.get("fingerprint"),
            **limits,
        }
        if (
            snapshot.get("route_alias") != DEEPSEEK_ROUTE
            or snapshot.get("natural_evaluation_capacity") != expected
        ):
            raise RuntimeValidationError("H4 capacity binding differs")
        provider_context = snapshot.get("fingerprint_payload", {}).get(
            "context_settings", {}
        )
        if (
            int(provider_context.get("total_tokens") or 0) < limits["context_window"]
            or int(provider_context.get("max_output_tokens") or 0)
            < limits["max_output_tokens"]
            or int(provider_context.get("max_model_requests") or 0)
            < limits["max_model_requests"]
        ):
            raise RuntimeValidationError("H4 exceeds pinned provider capacity")
    if (
        roles["reviewer"]["fingerprint_payload"]["context_settings"].get(
            "reviewer_repair_count"
        )
        != 0
    ):
        raise RuntimeValidationError("H4 requires zero reviewer repairs")
    if (
        CONVERSATION_BUDGET.input_limit != 11_213
        or REVIEWER_BUDGET.input_limit != 11_469
    ):
        raise RuntimeValidationError("H4 frozen input limits drifted")
    return NaturalEvaluationCapacity(
        conversation=CONVERSATION_BUDGET,
        reviewer=REVIEWER_BUDGET,
        conversation_requests=2,
        reviewer_shared_suffix_tokens=640,
        reviewer_request_max_tokens=4_096,
    )
