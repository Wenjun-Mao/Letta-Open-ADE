"""Focused red contracts, retained until their owning checkpoints implement them."""

from __future__ import annotations

from ade_api.features.agent_runtime.context import ContextBudget, build_context
from ade_api.features.agent_runtime.natural_memory_review import NaturalReviewDecision
from ade_api.features.agent_runtime.persistence.metadata import memory_subjects


def test_mandatory_policy_is_never_truncated_to_fit_an_optional_allocation() -> None:
    policy = "MANDATORY_POLICY_SENTINEL " * 100
    context = build_context(
        system_prompt=policy,
        persona="Persona",
        active_facts=[],
        retrieved_facts=[],
        recent_messages=[],
        current_user_content="Hello",
        budget=ContextBudget(
            context_window=8192,
            max_output_tokens=512,
            tool_schema_tokens=128,
            prompt_tokens=32,
        ),
    )
    assert policy in context.messages[0]["content"]


def test_subject_has_distinct_monotonic_memory_generation() -> None:
    assert "memory_generation" in memory_subjects.c
    assert "version" in memory_subjects.c


def test_reviewer_accepts_closed_reason_for_natural_revision() -> None:
    decision = NaturalReviewDecision.model_validate(
        {
            "decisions": [
                {
                    "kind": "revise",
                    "reason": "supersede",
                    "target": "F1",
                    "value": "Toronto",
                    "evidence": {"mode": "direct", "current_quote": "我现在住多伦多"},
                }
            ],
        }
    )
    assert decision.decisions[0].operation == "revise"
