"""Frozen wire and authority regressions for the compact natural review."""

from __future__ import annotations

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.natural_memory_review import (
    natural_review_json_schema,
    parse_natural_review_decision,
)


def test_decisions_are_required_and_empty_list_is_explicit_no_change() -> None:
    with pytest.raises(RuntimeValidationError):
        parse_natural_review_decision({})
    with pytest.raises(RuntimeValidationError):
        parse_natural_review_decision({"decisions": None})
    assert parse_natural_review_decision({"decisions": []}).decisions == []


def test_subject_add_has_no_entity_selector_even_in_generated_schema() -> None:
    schema = natural_review_json_schema()
    subject_add = schema["$defs"]["NaturalSubjectAdd"]
    assert "entity_ref" not in subject_add["properties"]
    assert "subject_id" not in subject_add["properties"]
    with pytest.raises(RuntimeValidationError):
        parse_natural_review_decision(
            {
                "decisions": [
                    {
                        "kind": "subject_add",
                        "fact_type": "person.preference",
                        "qualifier": "drink",
                        "value": "morning coffee",
                        "evidence": {"mode": "direct", "current_quote": "morning coffee"},
                        "entity_ref": "subject-uuid",
                    }
                ]
            }
        )


def test_no_write_decisions_need_no_executable_fields() -> None:
    decision = parse_natural_review_decision(
        {
            "decisions": [
                {
                    "kind": "defer",
                    "current_quote": "Roxy",
                    "reason": "unresolved",
                }
            ]
        }
    )
    assert decision.decisions[0].kind == "defer"
