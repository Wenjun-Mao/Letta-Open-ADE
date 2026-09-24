from __future__ import annotations

from copy import deepcopy

import pytest

from workflows.evals.character_memory_dev.natural_memory_contract import (
    expanded_cells,
    load_cases,
    load_matrix,
    validate_cases,
    validate_matrix,
)


def test_all_worked_arcs_are_chronological_isolated_fixtures() -> None:
    cases = load_cases()
    assert [arc["section"] for arc in cases["arcs"]] == list(range(1, 23))
    assert sum(len(arc["branches"]) for arc in cases["arcs"]) >= 40
    branches = {branch["id"] for arc in cases["arcs"] for branch in arc["branches"]}
    assert {
        "partial-assent",
        "no-save-endorsement",
        "reply-write-contradiction",
        "identity-race",
        "compaction-after-breakup",
    } <= branches


def test_future_turn_cannot_be_an_expected_checkpoint_source() -> None:
    cases = deepcopy(load_cases())
    first = cases["arcs"][0]["branches"][0]
    first["expected"] = [first["expected"][1], first["expected"][0]]
    with pytest.raises(ValueError, match="chronological"):
        validate_cases(cases)


def test_matrix_freezes_mandatory_cells_and_request_accounting() -> None:
    matrix = load_matrix()
    names = [name for name, _, _ in expanded_cells(matrix)]
    assert len(names) == len(set(names)) == 30
    assert "pressure-dog::A" in names
    assert "pressure-dog::B" in names
    assert "summary-after-change::A0" in names
    assert (
        matrix["live_request_schedule_proposed_not_authorized"][
            "outbound_provider_calls_at_checkpoint_1"
        ]
        == 0
    )


def test_pressure_must_withhold_for_a_while_b_and_reviewer_fit() -> None:
    matrix = deepcopy(load_matrix())
    matrix["budgets"]["pressure"]["reviewer_full_packet_max_tokens"] = 8000
    with pytest.raises(ValueError, match="mechanically distinguishable"):
        validate_matrix(matrix, load_cases())


def test_every_mandatory_response_has_same_selectable_variants() -> None:
    matrix = deepcopy(load_matrix())
    response = next(cell for cell in matrix["cells"] if cell["id"] == "pressure-dog")
    response["variants"] = ["B"]
    with pytest.raises(ValueError, match="compare A and B"):
        validate_matrix(matrix, load_cases())


def test_compaction_must_preserve_useful_information_outside_raw_suffix() -> None:
    matrix = deepcopy(load_matrix())
    matrix["positive_compaction_assertion"]["raw_suffix_excludes"] = []
    with pytest.raises(ValueError, match="outside raw suffix"):
        validate_matrix(matrix, load_cases())
