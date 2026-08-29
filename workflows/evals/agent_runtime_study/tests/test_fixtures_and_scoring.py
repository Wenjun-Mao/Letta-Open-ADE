from __future__ import annotations

from pathlib import Path

import pytest

from workflows.evals.agent_runtime_study.fixtures import (
    FixtureError,
    load_cases,
    select_cases,
)
from workflows.evals.agent_runtime_study.product_material import (
    CHAT_SYSTEM_PROMPT,
    SOURCE_CHAT_SYSTEM_PROMPT,
)
from workflows.evals.agent_runtime_study.scoring import (
    visible_private_reasoning_markers,
    weighted_candidate_score,
)
from workflows.evals.agent_runtime_study.world import build_case_world


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "study_cases.json"


def test_ade_native_prompt_removes_letta_owned_blocks_only() -> None:
    assert "<basic_functions>" in SOURCE_CHAT_SYSTEM_PROMPT
    assert "<memory>" in SOURCE_CHAT_SYSTEM_PROMPT
    assert "<basic_functions>" not in CHAT_SYSTEM_PROMPT
    assert "<memory>" not in CHAT_SYSTEM_PROMPT
    assert "<style>" in CHAT_SYSTEM_PROMPT
    assert "PURE DIALOGUE ONLY" in CHAT_SYSTEM_PROMPT


def test_visible_private_reasoning_markers_are_a_mandatory_signal() -> None:
    assert visible_private_reasoning_markers("普通对话") == ()
    assert visible_private_reasoning_markers("Thinking process:\nprivate plan") == (
        "thinking process:",
    )


def test_fixture_suite_covers_every_required_behavior() -> None:
    cases = load_cases(FIXTURES)
    assert {case.key for case in cases} == {
        "chat_memory_baseline",
        "correction_chain",
        "explicit_forgetting",
        "cross_agent_subject_sharing",
        "cross_subject_isolation",
        "old_memory_deep_search",
        "long_history_compaction",
        "false_memory_prevention",
        "weather_tool_selection",
        "weather_tool_failure",
    }
    assert select_cases(cases, ("correction_chain",))[0].key == "correction_chain"
    with pytest.raises(FixtureError, match="Unknown fixture"):
        select_cases(cases, ("missing",))


def test_weighted_score_requires_all_dimensions_and_preserves_gate_result() -> None:
    dimensions = {
        "comprehension_maintainability": 90,
        "explicit_control": 100,
        "observability": 80,
        "protocol_fidelity": 70,
        "dependency_security_burden": 95,
        "measured_overhead": 85,
    }
    score = weighted_candidate_score(
        candidate="custom_loop",
        dimensions=dimensions,
        mandatory_gates={"memory": True, "isolation": False},
    )
    assert score.weighted_total == 88.25
    assert score.passed_mandatory_gates is False
    assert score.failed_gates == ("isolation",)
    with pytest.raises(ValueError, match="Missing score dimensions"):
        weighted_candidate_score(
            candidate="bad",
            dimensions={"explicit_control": 1},
            mandatory_gates={},
        )


def test_seeded_old_memory_does_not_leak_into_test_conversation_history() -> None:
    case = select_cases(load_cases(FIXTURES), ("old_memory_deep_search",))[0]
    world = build_case_world(case, model_key="scripted")
    primary_id = world.conversation_ids["primary"]

    assert world.repository.list_messages(primary_id) == ()
    assert (
        len(
            world.repository.list_subject_facts(
                world.subject_ids["primary"], active_only=True
            )
        )
        == 8
    )
