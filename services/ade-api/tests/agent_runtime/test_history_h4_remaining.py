"""Approved H4 remainder is an exact continuation of unattempted schedule only."""

from copy import deepcopy

import pytest

from workflows.evals.character_memory_dev.history_h4_campaign import (
    CampaignStop,
    _classify_cell_turns,
    _frozen_inputs,
    _planned_cells,
)
from workflows.evals.character_memory_dev.history_h4_remaining import (
    load_remaining,
    load_remaining_after_two,
    validate_remaining,
    validate_remaining_after_two,
)


def test_approved_remaining_schedule_excludes_all_attempted_and_binds_dependencies() -> (
    None
):
    contract, fixture, _ = _frozen_inputs()
    original, proposal, selected = load_remaining(_planned_cells(contract, fixture))
    assert len(selected) == 15
    assert len(proposal["remaining_turns"]) == 21
    assert len(proposal["excluded_attempted_cells"]) == 11
    assert ("user_retraction", "empty_history") not in {
        (cell["name"], cell["arm"]) for cell in selected
    }
    for turn in proposal["remaining_turns"]:
        if turn["turn"] == "followup":
            assert (
                turn["dependency"] == f"{turn['case']}:{turn['arm']}:target_committed"
            )
    mutated = deepcopy(original)
    mutated["cells"][10]["status"] = "unrun_after_stop"
    with pytest.raises(RuntimeError):
        validate_remaining(mutated, proposal, _planned_cells(contract, fixture))
    changed = deepcopy(proposal)
    changed["remaining_turns"][4]["dependency"] = None
    with pytest.raises(RuntimeError):
        validate_remaining(original, changed, _planned_cells(contract, fixture))


def test_18_turn_schedule_excludes_both_campaigns_and_keeps_dependencies() -> None:
    contract, fixture, _ = _frozen_inputs()
    planned = _planned_cells(contract, fixture)
    original, first_proposal, _ = load_remaining(planned)
    loaded_original, second, proposal, selected = load_remaining_after_two(planned)
    assert loaded_original == original
    assert len(selected) == 12
    assert len(proposal["remaining_turns"]) == 18
    assert len(proposal["excluded_attempted_turns"]) == 14
    assert sum(turn["turn"] == "followup" for turn in proposal["remaining_turns"]) == 6
    selected_keys = {(cell["name"], cell["arm"]) for cell in selected}
    excluded_keys = {
        (turn["case"], turn["arm"]) for turn in proposal["excluded_attempted_turns"]
    }
    assert selected_keys.isdisjoint(excluded_keys)
    assert ("invalidated_ended", "empty_history") in excluded_keys
    assert ("invalidated_ended", "automatic_history") in excluded_keys
    for turn in proposal["remaining_turns"]:
        if turn["turn"] == "followup":
            assert (
                turn["dependency"] == f"{turn['case']}:{turn['arm']}:target_committed"
            )

    changed_second = deepcopy(second)
    changed_second["cells"][1]["status"] = "unrun_after_stop"
    with pytest.raises(RuntimeError):
        validate_remaining_after_two(
            original, first_proposal, changed_second, proposal, planned
        )
    changed_proposal = deepcopy(proposal)
    changed_proposal["remaining_turns"][1]["dependency"] = None
    with pytest.raises(RuntimeError):
        validate_remaining_after_two(
            original, first_proposal, second, changed_proposal, planned
        )


def _committed() -> dict:
    return {
        "status": "committed",
        "terminal_outcome": "committed",
        "terminal_safety": "verified",
        "attempt_sha256": "a" * 64,
        "provider_captures": [{"status": "completed"}],
        "base_packet": {"messages": []},
    }


def test_followup_outcomes_and_capture_integrity() -> None:
    result = {
        "name": "removed_acknowledgment",
        "arm": "empty_history",
        "status": "observed",
        "setup": {"embedding_dispatches": 1},
        "setup_captures": [{"status": "completed"}],
        "target": _committed(),
        "followup": _committed(),
    }
    assert [entry["disposition"] for entry in _classify_cell_turns(result)] == [
        "committed",
        "committed",
    ]
    result["followup"]["provider_captures"][0]["status"] = "missing"
    with pytest.raises(CampaignStop):
        _classify_cell_turns(result)
    result["followup"]["provider_captures"][0]["status"] = "completed"
    result["setup_captures"][0]["status"] = "missing"
    with pytest.raises(CampaignStop):
        _classify_cell_turns(result)
    result["setup_captures"][0]["status"] = "completed"
    result["target"] = {
        "status": "rejected",
        "terminal_outcome": "confirmed_rejection",
        "terminal_safety": "verified",
        "attempt_sha256": "b" * 64,
        "provider_captures": [{"status": "completed"}],
        "run": {"status": "failed"},
        "failure_detail_code": "conversation_tool_step_budget_exceeded",
        "observed_delta": {
            "generation_advance": 0,
            "revision_count": 0,
            "entity_additions": [],
            "run_revisions": [],
            "other_revision_ids": [],
        },
    }
    result["status"] = "rejected"
    result["followup"] = {"status": "unrun_dependency"}
    assert [entry["disposition"] for entry in _classify_cell_turns(result)] == [
        "bounded_rejection",
        "dependency_skip",
    ]
