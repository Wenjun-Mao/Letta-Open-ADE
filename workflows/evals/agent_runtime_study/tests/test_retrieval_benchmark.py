from __future__ import annotations

from workflows.evals.agent_runtime_study.retrieval_benchmark import (
    run_retrieval_benchmark,
)


def test_fact_plus_episode_retrieval_materially_improves_mixed_recall() -> None:
    result = run_retrieval_benchmark()
    assert result["fact_only"]["recall"] == 0.4
    assert result["fact_plus_episode"]["recall"] == 0.8
    cross_lingual = next(
        row
        for row in result["fact_plus_episode"]["rows"]
        if row["case_key"] == "cross_lingual_museum"
    )
    assert cross_lingual["pass"] is False
    assert result["materially_improves"] is True
    assert result["recommendation"] == "retain_optional_episode_contract"
