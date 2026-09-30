"""Private omission accounting, independent of ranking and admission behavior."""

from __future__ import annotations

from typing import Any

from .history_admission import MAX_ADMITTED_WINDOWS


def history_observation(attempt: Any) -> dict:
    inventory = attempt.corpus.get("inventory")
    if attempt.probe.arm == "empty_history":
        return {
            "status": "not_read",
            "reason": "empty_history_arm",
            "candidates": [],
        }
    if inventory is None or attempt.status == "unavailable":
        return {"status": "unavailable", "candidates": []}
    admitted = {str(item["run_id"]) for item in attempt.admitted_exchanges}
    ranked = [str(item["run_id"]) for item in attempt.ranked_exchanges]
    candidates = []
    for candidate in inventory["candidates"]:
        run_id, reason = candidate["run_id"], candidate["reason"]
        if reason == "eligible":
            if run_id in admitted:
                reason = "admitted"
            elif run_id in attempt.purged_run_ids:
                reason = "purged_before_exposure"
            elif run_id in attempt.omitted_capacity:
                reason = "packet_capacity"
            elif run_id in ranked[MAX_ADMITTED_WINDOWS:]:
                reason = "top_k"
            else:
                reason = "selector_not_selected"
        candidates.append({"run_id": run_id, "reason": reason})
    return {
        **inventory,
        "candidates": candidates,
        "reader_omitted": dict(attempt.corpus.get("omitted", {})),
    }
