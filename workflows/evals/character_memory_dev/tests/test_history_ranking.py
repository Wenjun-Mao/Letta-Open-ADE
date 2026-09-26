"""Deterministic pressure checks before any Qwen ranking observation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from workflows.evals.character_memory_dev.history_ranking import (
    TOP_K,
    assess_rank,
    choose_ranker,
    cosine_score,
    document_text,
    query_text,
    rank_windows,
    vector_recipe_identity,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "history_recall"
    / "ranking_development.json"
)


def test_wrong_rank_order_loses_distant_qualification() -> None:
    case = next(
        item
        for item in json.loads(FIXTURE.read_text())["cases"]
        if item["id"] == "mandarin_paraphrase_concern"
    )
    exchanges = case["exchanges"]
    ids = [item["id"] for item in exchanges]
    assert len(ids) > TOP_K
    query = query_text(case["query"], [])
    assert "minimum_evidence" not in query
    assert "e1" not in query and "e2" not in query
    assert all(item["id"] not in document_text(item) for item in exchanges)

    bad_scores = {exchange_id: 0.8 for exchange_id in ids}
    bad_scores.update(e1=0.1, e2=0.2)
    bad = rank_windows(exchanges, bad_scores)
    assert assess_rank(ids, bad, case["minimum_evidence"]) == {
        "status": "ranking_miss",
        "admitted_irrelevant": 0,
        "missing": ["e1", "e2"],
        "topic_hit": False,
    }
    partial_scores = dict(bad_scores, e1=0.99)
    partial = rank_windows(exchanges, partial_scores)
    assert assess_rank(ids, partial, ["e1", "e2"])["status"] == "insufficient_evidence"
    good_scores = dict(bad_scores, e1=0.99, e2=0.98)
    good = rank_windows(exchanges, good_scores)
    assert {item["id"] for item in good} >= set(case["minimum_evidence"])
    assert assess_rank(ids, good, case["minimum_evidence"])["status"] == "sufficient"
    case["minimum_evidence"] = ["__EXPECTED_ID_DO_NOT_USE__"]
    assert query == query_text(case["query"], [])
    assert "__EXPECTED_ID_DO_NOT_USE__" not in query
    assert assess_rank(ids, good, ["missing-source"])["status"] == "corpus_miss"


def test_ties_and_nonmatch_risk_are_explicit() -> None:
    case = next(
        item
        for item in json.loads(FIXTURE.read_text())["cases"]
        if item["id"] == "unrelated_probe"
    )
    exchanges = case["exchanges"]
    scores = {item["id"]: 0.0 for item in exchanges}
    ranked = rank_windows(exchanges, scores)
    assert [item["id"] for item in ranked] == ["z10", "z9", "z8", "z7"]
    assert assess_rank([item["id"] for item in exchanges], ranked, []) == {
        "status": "irrelevant_admission",
        "admitted_irrelevant": TOP_K,
        "missing": [],
        "topic_hit": False,
    }


def test_least_complex_adequate_ranker_is_selected() -> None:
    sufficient = {"status": "sufficient", "admitted_irrelevant": 0}
    miss = {"status": "ranking_miss", "admitted_irrelevant": 0}
    unrelated = {"status": "irrelevant_admission", "admitted_irrelevant": TOP_K}
    observations = {
        "literal_token_match": {
            "coffee": sufficient,
            "concern": miss,
            "unrelated": unrelated,
        },
        "probe_local_qwen_cosine": {
            "coffee": sufficient,
            "concern": sufficient,
            "unrelated": unrelated,
        },
    }
    assert (
        choose_ranker(observations, ["coffee", "concern"], "unrelated")["selected"]
        == "probe_local_qwen_cosine"
    )
    observations["literal_token_match"]["concern"] = sufficient
    assert (
        choose_ranker(observations, ["coffee", "concern"], "unrelated")["selected"]
        == "literal_token_match"
    )
    observations["probe_local_qwen_cosine"]["concern"] = miss
    observations["literal_token_match"]["concern"] = miss
    assert (
        choose_ranker(observations, ["coffee", "concern"], "unrelated")["selected"]
        is None
    )


def test_probe_vector_identity_and_cosine_are_separate_from_fact_space() -> None:
    contract = json.loads(FIXTURE.with_name("contract.json").read_text())
    recipe = contract["ranking"]["semantic_vector_recipe"]
    assert recipe["dimensions"] == 1024
    assert "no fact-space instruction" in recipe["query_format"]
    documents = {"d1": "User: 早上咖啡\nAssistant: 好的"}
    original = vector_recipe_identity(recipe, documents)
    assert original != vector_recipe_identity(recipe, {"d1": documents["d1"] + "。"})
    assert original != vector_recipe_identity(dict(recipe, dimensions=768), documents)
    assert cosine_score([3.0, 0.0, 0.0], [2.0, 0.0, 0.0], dimensions=3) == 1.0
    with pytest.raises(ValueError, match="wrong dimension"):
        cosine_score([1.0], [1.0, 0.0], dimensions=2)
