"""Source-pinned native mechanical checks; no Character or Memory semantic scoring."""

import math


def has_processing_work(operation: dict) -> bool:
    if operation.get("status") == "processing":
        return True
    children = operation.get("child_operations")
    return (
        operation.get("status") == "pending"
        and isinstance(children, list)
        and any(
            isinstance(child, dict) and child.get("status") == "processing"
            for child in children
        )
    )


def require_document_source(document: dict, item: dict) -> None:
    if document.get("original_text") != item["content"]:
        raise ValueError("Native original source changed")
    params = document.get("retain_params")
    if not isinstance(params, dict) or params.get("context") != item["context"]:
        raise ValueError("Native antecedent attribution changed")


def require_full_chinese_reranking(recall: dict) -> int:
    trace = recall.get("trace")
    if not isinstance(trace, dict):
        raise ValueError("Native reranking trace missing")
    ranked, merged = trace.get("reranked"), trace.get("rrf_merged")
    summary = trace.get("summary")
    metrics = summary.get("phase_metrics") if isinstance(summary, dict) else None
    if (
        not isinstance(ranked, list)
        or not isinstance(merged, list)
        or not isinstance(metrics, list)
    ):
        raise ValueError("Native reranking trace invalid")
    reranking = [item for item in metrics if item.get("phase_name") == "reranking"]
    if len(reranking) != 1:
        raise ValueError("Native reranking metric missing")
    details = reranking[0].get("details", {})
    count = details.get("candidates_reranked")
    if (
        details.get("reranker_type") != "cross-encoder"
        or type(count) is not int
        or count <= 0
    ):
        raise ValueError(
            "A populated Chinese probe requires actual cross-encoder scoring"
        )
    prefilters = [
        item for item in metrics if item.get("phase_name") == "rerank_prefilter"
    ]
    if len(prefilters) > 1:
        raise ValueError("Ambiguous reranking prefilter")
    expected = len(merged)
    if prefilters:
        trim = prefilters[0].get("details", {})
        kept, dropped = trim.get("kept"), trim.get("dropped")
        if (
            type(kept) is not int
            or type(dropped) is not int
            or kept + dropped != len(merged)
        ):
            raise ValueError("Reranking prefilter counts differ")
        expected = kept
    if count != expected or len(ranked) != count:
        raise ValueError("Native reranking is incomplete")
    identities = set()
    candidates = {item.get("node_id") for item in merged}
    for item in ranked:
        identity = item.get("node_id")
        scores = item.get("score_components", {})
        pair = [
            scores.get("cross_encoder_score"),
            scores.get("cross_encoder_score_normalized"),
        ]
        if (
            identity in identities
            or identity not in candidates
            or not all(
                type(score) in {float, int} and math.isfinite(score) for score in pair
            )
            or pair == [0, 0]
        ):
            raise ValueError("Native cross-encoder scores missing or passed through")
        identities.add(identity)
    if any(item["id"] not in identities for item in recall.get("results", [])):
        raise ValueError("Returned memories are missing reranking evidence")
    return count
