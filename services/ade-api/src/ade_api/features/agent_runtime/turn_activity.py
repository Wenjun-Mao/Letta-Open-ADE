"""Readback of retained per-turn observations; no billing or causal claims."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .request_counts import dispatch_counts


def conversation_activity(
    runs: list[dict[str, Any]],
    events: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    attempts_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_run[str(event["run_id"])].append(event)
    for attempt in attempts:
        attempts_by_run[str(attempt["run_id"])].append(attempt)

    summaries = []
    for run in runs:
        run_id = str(run["id"])
        observed = by_run[run_id]
        outcomes = attempts_by_run[run_id]
        terminal = next(
            (
                event
                for event in reversed(observed)
                if event["event_type"] == "run.completed"
            ),
            None,
        )
        terminal_counts = (
            (terminal.get("payload") or {}).get("dispatch_counts") if terminal else None
        )
        starts_by_attempt = {
            event.get("attempt")
            for event in observed
            if event["event_type"] == "model.request.started"
        }
        # A final-attempt receipt covers genuine zero dispatches. Earlier failed
        # attempts require retained starts; old or lost traces remain partial.
        covered = (
            isinstance(terminal_counts, dict)
            and terminal_counts.get("complete") is True
        )
        if covered:
            expected_final = sum(
                group.get("attempted", 0) for group in terminal_counts.get("groups", [])
            )
            retained_final = len(
                {
                    (event.get("payload") or {}).get("request_id")
                    for event in observed
                    if event["event_type"] == "model.request.started"
                    and event.get("attempt") == terminal.get("attempt")
                    and (event.get("payload") or {}).get("operation") != "catalog"
                }
            )
            covered = expected_final == retained_final
        covered = covered and all(
            attempt["attempt_number"] in starts_by_attempt
            for attempt in outcomes
            if attempt["status"] != "succeeded"
        )
        counts = dispatch_counts(observed, observation_incomplete=not covered)
        provider = {"generation": 0, "compaction": 0, "other": 0}
        for group in counts["groups"]:
            if group["stage"] == "conversation":
                category = "generation"
            elif group["stage"] == "compaction":
                category = "compaction"
            else:
                category = "other"
            provider[category] += group["attempted"]

        tools: dict[str, dict[str, int]] = {}
        calls: dict[tuple[int | None, str], dict[str, Any]] = {}
        for event in observed:
            if event["event_type"] not in {
                "tool.call.requested",
                "tool.call.completed",
            }:
                continue
            payload = event.get("payload") or {}
            name, call_id = payload.get("name"), payload.get("call_id")
            if not isinstance(name, str) or not isinstance(call_id, str):
                continue
            key = (event.get("attempt"), call_id)
            call = calls.setdefault(key, {"name": name, "outcome": "unresolved"})
            if event["event_type"] == "tool.call.completed":
                call["outcome"] = (
                    "succeeded" if payload.get("succeeded") is True else "failed"
                )
        for call in calls.values():
            result = tools.setdefault(
                call["name"], {"succeeded": 0, "failed": 0, "unresolved": 0}
            )
            result[call["outcome"]] += 1

        context = next(
            (
                event.get("payload") or {}
                for event in reversed(observed)
                if event["event_type"] == "context.built"
            ),
            None,
        )
        summaries.append(
            {
                "run_id": run_id,
                "status": run["status"],
                "provider": provider,
                "provider_complete": counts["complete"],
                "provider_observed": bool(
                    counts["groups"] or terminal_counts is not None
                ),
                "tools": [
                    {"name": name, **value} for name, value in sorted(tools.items())
                ],
                "tools_complete": terminal is not None
                and len(outcomes) == 1
                and all(call["outcome"] != "unresolved" for call in calls.values()),
                "context": {
                    "current_chat": context.get("current_chat") if context else None,
                    "automatic_memory_ids": context.get("automatic_memory_ids")
                    if context
                    else None,
                    "tool_memory_ids": context.get("tool_memory_ids")
                    if context
                    else None,
                },
            }
        )
    return summaries
