import math

import pytest

from ade_api.features.agent_runtime.hindsight_eval_contracts import EvaluationError
from ade_api.features.agent_runtime.hindsight_eval_trace import qualify_reranking


def trace(ids=("a",), *, scores=None, count=None, prefilter=None, results=None):
    scores = {node_id: (0.7, 0.8) for node_id in ids} if scores is None else scores
    metrics = [{
        "phase_name": "reranking", "duration_seconds": 0.1,
        "details": {"reranker_type": "cross-encoder", "candidates_reranked": len(ids) if count is None else count},
    }]
    merged = list(ids)
    if prefilter:
        metrics.insert(0, {"phase_name": "rerank_prefilter", "duration_seconds": 0.0, "details": prefilter})
    return {
        "rrf_merged": [{"node_id": node_id} for node_id in merged],
        "reranked": [{
            "node_id": node_id,
            "score_components": {
                "cross_encoder_score": scores[node_id][0],
                "cross_encoder_score_normalized": scores[node_id][1],
            },
        } for node_id in scores],
        "summary": {"phase_metrics": metrics, "results_returned": len(scores) if results is None else len(results)},
    }


def test_empty_requires_trace_proof_of_zero_candidates():
    qualify_reranking(trace(ids=()), [])
    with pytest.raises(EvaluationError, match="recall_rerank_incomplete"):
        qualify_reranking(trace(ids=(), count=1), [])


@pytest.mark.parametrize("scores", [
    {"a": (0, 0)}, {"a": (math.nan, 0.2)}, {"a": (0.2, math.inf)},
])
def test_unscored_or_nonfinite_candidate_rejected(scores):
    with pytest.raises(EvaluationError):
        qualify_reranking(trace(scores=scores), ["a"])


def test_negative_finite_logit_with_normalization_underflow_is_scored():
    qualify_reranking(trace(scores={"a": (-1200.0, 0.0)}), ["a"])


def test_candidate_count_and_identity_must_match_selected_set():
    with pytest.raises(EvaluationError, match="recall_rerank_incomplete"):
        qualify_reranking(trace(count=0), ["a"])
    candidate = trace()
    candidate["reranked"][0]["node_id"] = "other"
    with pytest.raises(EvaluationError, match="recall_rerank_trace_invalid"):
        qualify_reranking(candidate, ["a"])
    candidate = trace(ids=("a", "a"))
    with pytest.raises(EvaluationError, match="recall_rerank_trace_invalid"):
        qualify_reranking(candidate, ["a", "a"])


def test_prefilter_count_explains_pre_filter_rrf_candidates():
    candidate = trace(ids=("a", "b"), scores={"a": (0.7, 0.8)}, count=1,
                      prefilter={"kept": 1, "dropped": 1})
    qualify_reranking(candidate, ["a"])
    candidate["summary"]["phase_metrics"][0]["details"]["dropped"] = 0
    with pytest.raises(EvaluationError, match="recall_rerank_trace_invalid"):
        qualify_reranking(candidate, ["a"])


def test_missing_ranked_tail_and_unselected_result_are_rejected():
    candidate = trace(ids=("a", "b"), scores={"a": (0.7, 0.8)})
    with pytest.raises(EvaluationError, match="recall_rerank_trace_invalid"):
        qualify_reranking(candidate, ["a"])
    candidate = trace()
    with pytest.raises(EvaluationError, match="recall_rerank_trace_invalid"):
        qualify_reranking(candidate, ["unknown"])


def test_zero_candidate_trace_cannot_claim_recall_results():
    with pytest.raises(EvaluationError):
        qualify_reranking(trace(ids=()), ["fact"])
