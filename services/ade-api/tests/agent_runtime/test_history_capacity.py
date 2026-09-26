"""The frozen H4 budget is an evaluation-only, fingerprint-bound profile."""

from __future__ import annotations

from copy import deepcopy

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.history_capacity import (
    bind_history_probe_capacity,
    checked_history_probe_capacity,
)
from ade_api.features.agent_runtime.natural_context import HISTORY_PROBE_POLICY
from workflows.evals.character_memory_dev.history_h4_campaign import (
    reviewer_envelope_lower_bound,
)
from workflows.evals.character_memory_dev.history_h4_run import _frozen_inputs


def _definition() -> dict:
    return {
        "memory_policy_version": HISTORY_PROBE_POLICY,
        "deployment_snapshot": [
            {
                "role": role,
                "route_alias": (
                    "deepseek::deepseek-flash"
                    if role != "retriever"
                    else "qwen::embedding"
                ),
                "fingerprint": role * 16,
                "fingerprint_payload": {
                    "context_settings": {
                        "total_tokens": 16384,
                        "max_output_tokens": 4096,
                        "max_model_requests": 6,
                        "reviewer_repair_count": 0,
                    }
                },
            }
            for role in ("conversation", "reviewer", "retriever")
        ],
    }


def test_h4_capacity_is_exact_and_does_not_mutate_prepared_definition() -> None:
    original = _definition()
    frozen = deepcopy(original)
    assert checked_history_probe_capacity(original, purpose="evaluation") is None
    bound = bind_history_probe_capacity(original)
    capacity = checked_history_probe_capacity(bound, purpose="evaluation")
    assert original == frozen
    assert capacity.conversation.input_limit == 11213
    assert capacity.conversation.max_output_tokens == 4096
    assert capacity.reviewer.input_limit == 6759
    assert capacity.reviewer_request_max_tokens == 4096
    assert capacity.conversation_requests == 2


def test_frozen_h4_reviewer_envelope_cannot_reserve_full_generation_reply() -> None:
    contract, fixture, _ = _frozen_inputs()
    envelope = reviewer_envelope_lower_bound(contract, fixture)
    assert envelope["frozen_input_limit"] == 6759
    assert envelope["minimum_input_tokens"] > envelope["frozen_input_limit"]


@pytest.mark.parametrize("mutation", ["fingerprint", "capacity", "provider", "repair"])
def test_h4_capacity_fails_closed_on_drift(mutation: str) -> None:
    bound = bind_history_probe_capacity(_definition())
    reviewer = bound["deployment_snapshot"][1]
    if mutation == "fingerprint":
        reviewer["fingerprint"] = "changed"
    elif mutation == "capacity":
        reviewer["natural_evaluation_capacity"]["max_output_tokens"] = 1024
    elif mutation == "provider":
        reviewer["fingerprint_payload"]["context_settings"]["max_output_tokens"] = 1024
    else:
        reviewer["fingerprint_payload"]["context_settings"]["reviewer_repair_count"] = 1
    with pytest.raises(RuntimeValidationError):
        checked_history_probe_capacity(bound, purpose="evaluation")
