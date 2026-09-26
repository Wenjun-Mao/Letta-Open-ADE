"""Frozen H1 limits and case separation for the isolated historical probe."""

from __future__ import annotations

import json
from pathlib import Path

from ade_api.features.agent_runtime.persistence import history, history_lineage


CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "history_recall"
    / "contract.json"
)
CASES = CONTRACT.with_name("cases.json")
RANKING_DEVELOPMENT = CONTRACT.with_name("ranking_development.json")


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
        assert case["query"]
        assert set(case["minimum_evidence"]) <= exchange_ids
    case_ids = [case["id"] for case in contract["cases"]]
    assert len(case_ids) == len(set(case_ids))
    scripts = json.loads(CASES.read_text())
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
