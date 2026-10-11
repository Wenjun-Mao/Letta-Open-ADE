"""Fail-closed qualification of Hindsight's source-pinned rerank trace."""

from __future__ import annotations

import math
from typing import Any

from .hindsight_eval_contracts import EvaluationError


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def qualify_reranking(trace: dict, result_ids: list[str]) -> None:
    """Require complete cross-encoder scoring for every selected candidate.

    `rrf_merged` is pre-prefilter and can be reordered by boost logic before the
    cap. The trace does not expose that exact selected set, so require the full
    declared candidate count and unique reranked IDs drawn from the merged set.
    """
    merged = trace.get("rrf_merged")
    ranked = trace.get("reranked")
    summary = trace.get("summary")
    metrics = summary.get("phase_metrics") if isinstance(summary, dict) else None
    if not isinstance(merged, list) or not isinstance(ranked, list) or not isinstance(metrics, list):
        raise EvaluationError("recall_rerank_trace_invalid")
    rerank_metrics = [
        item for item in metrics
        if isinstance(item, dict) and item.get("phase_name") == "reranking"
    ]
    if len(rerank_metrics) != 1:
        raise EvaluationError("recall_rerank_incomplete")
    details = rerank_metrics[0].get("details")
    if not isinstance(details, dict) or details.get("reranker_type") != "cross-encoder":
        raise EvaluationError("recall_rerank_incomplete")
    count = details.get("candidates_reranked")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise EvaluationError("recall_rerank_trace_invalid")
    if not merged:
        summary_count = summary.get("results_returned")
        if count != 0 or ranked or result_ids or summary_count != 0:
            raise EvaluationError("recall_rerank_incomplete")
        return

    prefilters = [
        item for item in metrics
        if isinstance(item, dict) and item.get("phase_name") == "rerank_prefilter"
    ]
    if len(prefilters) > 1:
        raise EvaluationError("recall_rerank_trace_invalid")
    merged_ids = [entry.get("node_id") if isinstance(entry, dict) else None for entry in merged]
    if any(not isinstance(node_id, str) or not node_id for node_id in merged_ids) or len(set(merged_ids)) != len(merged_ids):
        raise EvaluationError("recall_rerank_trace_invalid")
    kept = len(merged)
    if prefilters:
        trim = prefilters[0].get("details")
        if not isinstance(trim, dict):
            raise EvaluationError("recall_rerank_trace_invalid")
        k, d = trim.get("kept"), trim.get("dropped")
        if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in (k, d)) or k + d != len(merged):
            raise EvaluationError("recall_rerank_trace_invalid")
        kept = k
    if count != kept:
        raise EvaluationError("recall_rerank_incomplete")
    returned_ids: list[str] = []
    for entry in ranked:
        if not isinstance(entry, dict) or not isinstance(entry.get("node_id"), str):
            raise EvaluationError("recall_rerank_trace_invalid")
        node_id = entry["node_id"]
        components = entry.get("score_components")
        if not isinstance(components, dict):
            raise EvaluationError("recall_rerank_trace_invalid")
        raw = components.get("cross_encoder_score")
        normalized = components.get("cross_encoder_score_normalized")
        if not _finite_number(raw) or not _finite_number(normalized):
            raise EvaluationError("recall_rerank_trace_invalid")
        # An exact (0, 0) pair is the pinned timeout/passthrough sentinel.
        # A finite nonzero logit with normalization underflow to zero is valid.
        if raw == 0 and normalized == 0:
            raise EvaluationError("recall_rerank_incomplete")
        returned_ids.append(node_id)
    if len(returned_ids) != count or len(returned_ids) != len(set(returned_ids)) or not set(returned_ids).issubset(set(merged_ids)):
        raise EvaluationError("recall_rerank_trace_invalid")
    summary_count = summary.get("results_returned")
    if not isinstance(summary_count, int) or isinstance(summary_count, bool) or summary_count != len(result_ids):
        raise EvaluationError("recall_rerank_trace_invalid")
    if len(result_ids) != len(set(result_ids)) or not set(result_ids).issubset(set(returned_ids)):
        raise EvaluationError("recall_rerank_trace_invalid")
