from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .client import SseEvent
from .contracts import (
    EventObservation,
    FactObservation,
    ToolObservation,
    TurnObservation,
    observation_instance,
    score_observations,
)


TERMINAL_EVENT_TYPES = frozenset({"run.completed", "run.failed", "run.cancelled"})
SUCCESS_REQUIRED_EVENTS = frozenset(
    {
        "run.started",
        "model.request",
        "model.response",
        "memory.review.request",
        "memory.reviewed",
        "message.committed",
        "run.completed",
    }
)


@dataclass(frozen=True)
class NormalizedCase:
    score: dict[str, Any]
    turns: tuple[Any, ...]
    events: tuple[Any, ...]
    tools: tuple[Any, ...]
    facts: tuple[Any, ...]
    infrastructure: dict[str, Any]


def normalize_case(
    *,
    case: object,
    turns: list[dict[str, Any]],
    subject_facts: dict[str, list[dict[str, Any]]],
) -> NormalizedCase:
    turn_observations: list[Any] = []
    event_observations: list[Any] = []
    tool_observations: list[Any] = []
    failures: list[dict[str, Any]] = []
    statuses: list[str] = []

    for item in turns:
        run = item["run"]
        run_id = _required(run, "id")
        status = str(run.get("status") or "unknown")
        statuses.append(status)
        assistant_content = _assistant_content(item.get("conversation_state") or {})
        turn_observations.append(
            observation_instance(
                TurnObservation,
                {
                    "case_key": str(getattr(case, "key")),
                    "conversation_key": str(item["conversation_key"]),
                    "run_id": run_id,
                    "status": status,
                    "assistant_content": assistant_content,
                    "attempt_count": int(run.get("attempt_count") or 0),
                },
            )
        )
        normalized_events, normalized_tools, run_failures = _normalize_run_events(
            run_id, item.get("events") or (), status
        )
        event_observations.extend(normalized_events)
        tool_observations.extend(normalized_tools)
        failures.extend(run_failures)

    fact_observations = tuple(
        observation_instance(
            FactObservation,
            {"subject_key": subject_key, "facts": tuple(facts)},
        )
        for subject_key, facts in sorted(subject_facts.items())
    )
    facts_by_subject = {
        subject_key: tuple(
            item for item in fact_observations if _subject_key(item) == subject_key
        )
        for subject_key in subject_facts
    }
    turns_by_conversation: dict[str, tuple[Any, ...]] = {}
    for conversation_key in {str(item["conversation_key"]) for item in turns}:
        turns_by_conversation[conversation_key] = tuple(
            item
            for item in turn_observations
            if getattr(item, "conversation_key", None) == conversation_key
        )
    events_by_run = _group_by_run(event_observations)
    tools_by_run = _group_by_run(tool_observations)
    observations = {
        "turns": tuple(turn_observations),
        "events": tuple(event_observations),
        "tools": tuple(tool_observations),
        "facts": fact_observations,
        "facts_by_subject": facts_by_subject,
        "turns_by_conversation": turns_by_conversation,
        "events_by_run": events_by_run,
        "tools_by_run": tools_by_run,
        "failures": tuple(failures),
    }
    score = score_observations(case, observations)
    return NormalizedCase(
        score=score,
        turns=tuple(turn_observations),
        events=tuple(event_observations),
        tools=tuple(tool_observations),
        facts=fact_observations,
        infrastructure={
            "failures": failures,
            "terminal_statuses": statuses,
            "all_terminal": all(
                status in {"succeeded", "failed", "cancelled"} for status in statuses
            ),
        },
    )


def _normalize_run_events(
    run_id: str, events: tuple[SseEvent, ...] | list[SseEvent], status: str
) -> tuple[list[Any], list[Any], list[dict[str, Any]]]:
    normalized: list[Any] = []
    tools: list[Any] = []
    failures: list[dict[str, Any]] = []
    event_types: list[str] = []
    last_sequence = 0
    for event in events:
        payload = dict(event.data.get("payload") or {})
        actual_run_id = str(event.data.get("run_id") or "")
        sequence = int(event.data.get("sequence") or 0)
        event_type = str(event.data.get("type") or event.event_type)
        event_types.append(event_type)
        if actual_run_id != run_id:
            failures.append({"kind": "event_run_mismatch", "pass": False})
        if sequence != last_sequence + 1:
            failures.append(
                {"kind": "event_sequence", "pass": False, "sequence": sequence}
            )
        last_sequence = sequence
        normalized.append(
            observation_instance(
                EventObservation,
                {
                    "run_id": run_id,
                    "sequence": sequence,
                    "event_type": event_type,
                    "attempt": event.data.get("attempt"),
                    "payload": payload,
                },
            )
        )
        if event_type == "tool.result":
            tools.append(
                observation_instance(
                    ToolObservation,
                    {
                        "run_id": run_id,
                        "name": str(
                            payload.get("name") or payload.get("tool_name") or ""
                        ),
                        "succeeded": bool(
                            payload.get("succeeded", payload.get("ok", False))
                        ),
                        "payload": payload,
                    },
                )
            )
    if status == "succeeded":
        missing = sorted(SUCCESS_REQUIRED_EVENTS - set(event_types))
        if missing:
            failures.append(
                {"kind": "required_events", "pass": False, "missing": missing}
            )
        if "run.failed" in event_types or "run.cancelled" in event_types:
            failures.append({"kind": "terminal_event_conflict", "pass": False})
        if "message.committed" in event_types and "memory.reviewed" not in event_types:
            failures.append({"kind": "reviewer_atomicity", "pass": False})
    elif not any(item in TERMINAL_EVENT_TYPES for item in event_types):
        failures.append(
            {"kind": "terminal_event_missing", "pass": False, "status": status}
        )
    return normalized, tools, failures


def _assistant_content(state: dict[str, Any]) -> str:
    messages = state.get("messages")
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") == "assistant":
            return str(message.get("content") or "")
    return ""


def _group_by_run(items: list[Any]) -> dict[str, tuple[Any, ...]]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    for item in items:
        grouped[str(getattr(item, "run_id", ""))].append(item)
    return {key: tuple(value) for key, value in grouped.items()}


def _required(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"run response is missing {key}")
    return value


def _subject_key(value: object) -> str:
    return str(getattr(value, "subject_key", ""))
