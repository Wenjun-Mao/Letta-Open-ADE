"""Aggregate retained outbound dispatch observations by ADE request ID."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


def dispatch_counts(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Count local attempts, never infer billing or manufacture a missing start.

    Copies of one trace event across API/worker artifacts share request_id. A
    terminal without a retained start makes coverage incomplete; a start without
    a terminal is unresolved. Catalog discovery is excluded from model usage.
    """

    starts: dict[str, dict[str, Any]] = {}
    terminals: dict[str, str] = {}
    incomplete = False
    for event in events:
        event_type = event.get("event_type") or event.get("type")
        payload = event.get("payload") or {}
        if not isinstance(payload, dict):
            incomplete = True
            continue
        request_id = payload.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            if event_type in {
                "model.request.started",
                "model.response.completed",
                "model.request.failed",
                "model.request.cancelled",
            }:
                incomplete = True
            continue
        if payload.get("operation") == "catalog":
            continue
        if event_type == "model.request.started":
            prior = starts.setdefault(request_id, payload)
            if prior != payload:
                incomplete = True
        elif event_type in {
            "model.response.completed",
            "model.request.failed",
            "model.request.cancelled",
        }:
            prior_terminal = terminals.setdefault(request_id, event_type)
            if prior_terminal != event_type:
                incomplete = True
    grouped: dict[tuple[str, str, str], dict[str, int]] = defaultdict(
        lambda: {"attempted": 0, "completed": 0, "failed": 0, "unresolved": 0}
    )
    for request_id, start in starts.items():
        key = (
            str(start.get("operation") or "unknown"),
            str(start.get("model_key") or "unknown"),
            str(start.get("stage") or "unknown"),
        )
        counts = grouped[key]
        counts["attempted"] += 1
        terminal = terminals.get(request_id)
        if terminal == "model.response.completed":
            counts["completed"] += 1
        elif terminal in {"model.request.failed", "model.request.cancelled"}:
            counts["failed"] += 1
        else:
            counts["unresolved"] += 1
    incomplete |= bool(terminals.keys() - starts.keys())
    return {
        "complete": not incomplete,
        "groups": [
            {"operation": key[0], "model": key[1], "stage": key[2], **counts}
            for key, counts in sorted(grouped.items())
        ],
    }
