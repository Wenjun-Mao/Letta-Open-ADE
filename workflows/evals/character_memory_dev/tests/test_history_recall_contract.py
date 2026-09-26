"""Frozen H1 limits and case separation for the isolated historical probe."""

from __future__ import annotations

import json
import hashlib
from copy import deepcopy
from pathlib import Path

import pytest

from ade_api.features.agent_runtime.persistence import history, history_lineage
from workflows.evals.character_memory_dev.history_fixture_contract import (
    validate_history_cases,
)
from workflows.evals.character_memory_dev.history_ranking import TOP_K


CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "history_recall"
    / "contract.json"
)
CASES = CONTRACT.with_name("cases.json")
RANKING_DEVELOPMENT = CONTRACT.with_name("ranking_development.json")
TARGET_ATTRIBUTION_SCHEDULE = CONTRACT.with_name("target_attribution_diagnostic.json")


def test_frozen_reader_limits_and_scoring_sets() -> None:
    contract = json.loads(CONTRACT.read_text())
    corpus = contract["corpus"]
    assert corpus["max_complete_exchanges"] == history.MAX_EXCHANGES
    assert corpus["max_chars_per_message"] == history.MAX_MESSAGE_CHARS
    assert (
        corpus["max_source_links_per_exchange"]
        == history_lineage.MAX_LINKS_PER_EXCHANGE
    )
    assert (
        corpus["max_revisions_per_linked_fact"]
        == history_lineage.MAX_REVISIONS_PER_FACT
    )
    assert (
        corpus["max_predecessor_edges_per_linked_fact"]
        == history_lineage.MAX_EDGES_PER_FACT
    )

    ranking = contract["ranking"]
    assert set(ranking["development_cases"]).isdisjoint(ranking["held_out_cases"])
    development = json.loads(RANKING_DEVELOPMENT.read_text())
    assert [case["id"] for case in development["cases"]] == ranking["development_cases"]
    for case in development["cases"]:
        exchange_ids = {exchange["id"] for exchange in case["exchanges"]}
        assert len(exchange_ids) > TOP_K
        assert case["query"]
        assert set(case["minimum_evidence"]) <= exchange_ids
    case_ids = [case["id"] for case in contract["cases"]]
    assert len(case_ids) == len(set(case_ids))
    scripts = json.loads(CASES.read_text())
    validate_history_cases(contract, scripts)
    assert [case["id"] for case in scripts["cases"]] == case_ids
    for case in contract["cases"]:
        assert case["target"] and case["delta"] and case["must_not"]
        assert "minimum_evidence" in case
    for case in scripts["cases"]:
        setup_ids = [exchange["id"] for exchange in case["setup"]]
        assert len(set(setup_ids)) == len(setup_ids)
        assert all(
            exchange["user"] and exchange["assistant"] for exchange in case["setup"]
        )
        assert case["target"]["user"]
        assert all(
            source.split(":", 1)[0] in setup_ids for source in case["required_evidence"]
        )


def test_target_attribution_diagnostic_is_seven_fresh_native_turns() -> None:
    schedule = json.loads(TARGET_ATTRIBUTION_SCHEDULE.read_text())
    cases = {case["id"]: case for case in json.loads(CASES.read_text())["cases"]}
    assert (
        schedule["source_cases_sha256"]
        == hashlib.sha256(CASES.read_bytes()).hexdigest()
    )
    assert (
        schedule["h4_reviewer_amendment_sha256"]
        == hashlib.sha256(
            CONTRACT.with_name("h4_reviewer_amendment.json").read_bytes()
        ).hexdigest()
    )
    assert schedule["status"] == "offline-schedule-awaiting-director-review"
    assert schedule["arm"] == "automatic_history"
    trajectories = schedule["trajectories"]
    assert [len(item["turns"]) for item in trajectories] == [2, 2, 1, 2]
    assert all(item["isolated_subject"] for item in trajectories)
    assert [item["seed_case"] for item in trajectories] == [
        "h_only_referent",
        "h_only_referent",
        "h_only_referent",
        "removed_acknowledgment",
    ]
    assert (
        trajectories[0]["turns"][0]["user"]
        == cases["h_only_referent"]["target"]["user"]
    )
    assert (
        trajectories[1]["turns"][0]["user"]
        == cases["h_only_referent"]["target"]["user"]
    )
    assert (
        trajectories[3]["turns"][0]["user"]
        == cases["removed_acknowledgment"]["target"]["user"]
    )
    assert (
        trajectories[3]["turns"][1]["user"]
        == cases["removed_acknowledgment"]["followup"]["user"]
    )
    assert schedule["per_turn"]["retry_count"] == 0
    assert schedule["per_turn"]["reviewer_repairs"] == 0
    assert (
        schedule["routes"]["conversation_and_reviewer"]["model"]
        == "deepseek::deepseek-flash"
    )
    assert schedule["routes"]["history_and_fact_embeddings"]["dimensions"] == 1024


def test_fixture_guards_reject_invalid_lifecycle_and_missing_cells() -> None:
    contract = json.loads(CONTRACT.read_text())
    scripts = json.loads(CASES.read_text())
    invalid = deepcopy(scripts)
    invalid_case = next(
        case for case in invalid["cases"] if case["id"] == "invalidated_ended"
    )
    invalid_case["facts"][0]["transitions"][1]["operation"] = "revise"
    with pytest.raises(ValueError, match="invalid natural write"):
        validate_history_cases(contract, invalid)

    missing_control = deepcopy(scripts)
    missing_control["native_controls"].pop()
    with pytest.raises(ValueError, match="native control schedule"):
        validate_history_cases(contract, missing_control)

    missing_followup = deepcopy(scripts)
    next(
        case for case in missing_followup["cases"] if case["id"] == "h_only_referent"
    ).pop("followup")
    with pytest.raises(ValueError, match="follow-up schedule"):
        validate_history_cases(contract, missing_followup)

    wrong_scope = deepcopy(scripts)
    next(case for case in wrong_scope["cases"] if case["id"] == "isolation")[
        "required_evidence"
    ] = ["x1:user"]
    with pytest.raises(ValueError, match="crosses target scope"):
        validate_history_cases(contract, wrong_scope)
