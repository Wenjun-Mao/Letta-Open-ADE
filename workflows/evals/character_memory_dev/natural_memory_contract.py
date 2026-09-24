"""Frozen offline inputs for the bounded natural-memory comparison.

This module validates the comparison contract; it does not run providers or score
model replies. Runtime manifests must later be checked against these inputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "natural_memory"
ALLOWED_ROLES = frozenset({"user", "assistant", "operator"})
SELECTABLE_VARIANTS = frozenset({"A", "B"})


def _read_fixture(name: str) -> dict[str, Any]:
    with (FIXTURE_DIR / name).open(encoding="utf-8") as stream:
        return json.load(stream)


def load_cases() -> dict[str, Any]:
    cases = _read_fixture("cases.json")
    validate_cases(cases)
    return cases


def load_matrix() -> dict[str, Any]:
    matrix = _read_fixture("matrix.json")
    validate_matrix(matrix, load_cases())
    return matrix


def _branches(cases: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (arc["id"], branch["id"]): branch
        for arc in cases["arcs"]
        for branch in arc["branches"]
    }


def validate_cases(cases: dict[str, Any]) -> None:
    if cases.get("schema_version") != 1:
        raise ValueError("unsupported natural-memory cases schema")
    arcs = cases.get("arcs")
    if not isinstance(arcs, list) or len(arcs) != 22:
        raise ValueError("exactly 22 worked arcs are required")
    if {arc["section"] for arc in arcs} != set(range(1, 23)):
        raise ValueError("scenario sections must cover 1–22 exactly once")
    if len({arc["id"] for arc in arcs}) != len(arcs):
        raise ValueError("arc IDs must be unique")
    for arc in arcs:
        branch_ids: set[str] = set()
        for branch in arc["branches"]:
            if branch["id"] in branch_ids:
                raise ValueError("branch IDs must be unique within an arc")
            branch_ids.add(branch["id"])
            turns = branch["turns"]
            if not turns:
                raise ValueError("a branch requires chronological turns")
            ids = [turn[0] for turn in turns]
            if len(ids) != len(set(ids)):
                raise ValueError("turn IDs must be unique within a branch")
            if any(
                len(turn) != 3
                or turn[1] not in ALLOWED_ROLES
                or not isinstance(turn[2], str)
                or not turn[2].strip()
                for turn in turns
            ):
                raise ValueError("turns require ID, source role and nonempty text")
            if not branch["expected"] or not branch["allowed_sources"]:
                raise ValueError("state and source authority are required")
            if not branch["useful_reply"] or not branch["forbidden_claims"]:
                raise ValueError("usefulness and forbidden claims are required")
            if "unsupported" not in branch:
                raise ValueError("unsupported scope must be explicit")
            previous = -1
            for checkpoint in branch["expected"]:
                if checkpoint["after"] not in ids or not checkpoint["state"]:
                    raise ValueError("checkpoint must bind a real turn and state")
                position = ids.index(checkpoint["after"])
                if position <= previous:
                    raise ValueError("checkpoints must be chronological")
                previous = position
            for source in branch["allowed_sources"]:
                source_id, _, source_role = source.partition(":")
                if source_id not in ids or not source_role:
                    raise ValueError("source authority must bind a real turn")


def expanded_cells(matrix: dict[str, Any]) -> list[tuple[str, dict[str, Any], str]]:
    return [
        (f"{cell['id']}::{variant}", cell, variant)
        for cell in matrix["cells"]
        for variant in cell["variants"]
    ]


def eligible_local_turn_ids(cell: dict[str, Any], branch: dict[str, Any]) -> list[str]:
    """Select the same preselection local pool for every variant of a cell."""
    turns = branch["turns"]
    cutoff = next(
        index for index, turn in enumerate(turns) if turn[0] == cell["cutoff"]
    )
    first = 0
    if "summary_through" in cell:
        first = (
            next(
                index
                for index, turn in enumerate(turns)
                if turn[0] == cell["summary_through"]
            )
            + 1
        )
    eligible = turns[first:cutoff]
    user_positions = [index for index, turn in enumerate(eligible) if turn[1] == "user"]
    if len(user_positions) > 8:
        eligible = eligible[user_positions[-8] :]
    return [turn[0] for turn in eligible]


def validate_matrix(matrix: dict[str, Any], cases: dict[str, Any]) -> None:
    if matrix.get("schema_version") != 1:
        raise ValueError("unsupported natural-memory matrix schema")
    branches = _branches(cases)
    cells = matrix["cells"]
    if len({cell["id"] for cell in cells}) != len(cells):
        raise ValueError("matrix cell IDs must be unique")
    required_responses = 0
    required_mutations = 0
    for cell in cells:
        branch = branches.get((cell["arc"], cell["branch"]))
        if branch is None:
            raise ValueError(f"unknown branch for {cell['id']}")
        if cell["cutoff"] not in [turn[0] for turn in branch["turns"]]:
            raise ValueError(f"unknown chronological cutoff for {cell['id']}")
        if "summary_through" in cell and cell["summary_through"] not in [
            turn[0] for turn in branch["turns"]
        ]:
            raise ValueError(f"unknown summary boundary for {cell['id']}")
        if cell.get(
            "eligible_local_turn_ids", eligible_local_turn_ids(cell, branch)
        ) != eligible_local_turn_ids(cell, branch):
            raise ValueError("eligible local pool differs from frozen cutoff")
        if not cell["expected"] or not cell["forbidden"]:
            raise ValueError("every cell needs positive and negative criteria")
        if cell["kind"] == "required_mutation":
            required_mutations += 1
            if (
                cell["variants"] != ["native"]
                or cell["stop"] != "campaign_on_wrong_state"
            ):
                raise ValueError("required mutation classification changed")
        elif cell["kind"] in {"required_response", "diagnostic_summary"}:
            if cell["kind"] == "required_response":
                required_responses += 1
                if set(cell["variants"]) != SELECTABLE_VARIANTS:
                    raise ValueError("mandatory response must compare A and B")
            elif cell["variants"] != ["A", "A0", "B"]:
                raise ValueError("summary diagnostics require A/A0/B")
            if cell["stop"] != "candidate_on_quality_failure":
                raise ValueError("response quality must not stop the whole campaign")
        else:
            raise ValueError("unknown matrix cell kind")
    if required_mutations != 8 or required_responses != 8:
        raise ValueError("eight mutation and eight paired response groups are required")

    budgets = matrix["budgets"]
    generation = budgets["generation"]
    reviewer = budgets["reviewer"]
    if (
        generation["context_window"]
        - generation["output_reserve"]
        - generation["safety_margin"]
        - generation["tool_schema"]
        != generation["input_limit"]
    ):
        raise ValueError("generation input must reserve output, schema and safety")
    if (
        reviewer["context_window"]
        - reviewer["output_reserve"]
        - reviewer["safety_margin"]
        != reviewer["input_limit"]
    ):
        raise ValueError("reviewer input must reserve output and safety")
    if reviewer["candidate_reply_reserve"] < generation["output_reserve"]:
        raise ValueError("reviewer must reserve the full candidate reply")
    pressure = budgets["pressure"]
    if pressure["record_count"] not in budgets["eligible_record_grid"]:
        raise ValueError("pressure point must belong to the offline grid")
    if pressure["record_payload_tokens"] != (
        pressure["record_count"]
        * budgets["record_sizes_tokens"][pressure["size_class"]]
    ):
        raise ValueError("pressure records do not match frozen size")
    if not (
        pressure["generator_full_packet_min_tokens"] > generation["input_limit"]
        and pressure["reviewer_full_packet_max_tokens"] <= reviewer["input_limit"]
        and pressure["b_selective_packet_max_tokens"] <= generation["input_limit"]
    ):
        raise ValueError("pressure comparison is not mechanically distinguishable")

    schedule = matrix["live_request_schedule_proposed_not_authorized"]
    expanded = expanded_cells(matrix)
    if len(expanded) != schedule["turn_cells"]:
        raise ValueError("request schedule omits or adds turn cells")
    generation_cap = (
        len(expanded) * sum(schedule["per_turn_generation_cap"].values())
        + schedule["actual_compaction_calls"]
    )
    if generation_cap != schedule["maximum_reserved_generation"]:
        raise ValueError("generation schedule does not cover every call")
    if (
        generation_cap + schedule["unallocated_generation_headroom"]
        != schedule["generation_limit"]
    ):
        raise ValueError("generation cap accounting is incomplete")
    if sum(schedule["embedding_allocation"].values()) != schedule["embedding_limit"]:
        raise ValueError("embedding cap accounting is incomplete")
    assertion = matrix["positive_compaction_assertion"]
    branch = branches[(assertion["arc"], assertion["branch"])]
    turn_ids = [turn[0] for turn in branch["turns"]]
    if turn_ids.index(assertion["source_turn"]) >= turn_ids.index(
        assertion["probe_turn"]
    ):
        raise ValueError("compaction probe leaks future information")
    if assertion["source_turn"] not in assertion["raw_suffix_excludes"]:
        raise ValueError("positive compaction source must be outside raw suffix")
    if (
        not assertion["required_for_A_acceptance"]
        or not assertion["probe_excludes_answer"]
    ):
        raise ValueError("compaction must prove useful retained information")
