from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .client import SseEvent
from .contracts import (
    EventObservation,
    FactObservation,
    ToolObservation,
    TurnObservation,
    score_observations,
)


TERMINAL_EVENT_TYPES = frozenset({"run.completed", "run.failed", "run.cancelled"})
SUCCESS_REQUIRED_EVENTS = frozenset(
    {
        "run.started",
        "message.committed",
        "run.completed",
    }
)
MODEL_ROLES = ("conversation", "reviewer")


@dataclass(frozen=True)
class RecordedTurn:
    case_key: str
    conversation_key: str
    run_id: str
    attempt_count: int
    observation: TurnObservation


@dataclass(frozen=True)
class RecordedEvent:
    event_id: str
    run_id: str
    sequence: int
    event_type: str
    attempt: int | None
    correlation_id: str
    causation_id: str | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class RecordedTool:
    run_id: str
    name: str
    succeeded: bool
    payload: dict[str, Any]


@dataclass(frozen=True)
class RecordedFact:
    subject_key: str
    fact_id: str
    observation: FactObservation


@dataclass(frozen=True)
class NormalizedCase:
    score: dict[str, Any]
    turns: tuple[RecordedTurn, ...]
    events: tuple[RecordedEvent, ...]
    tools: tuple[RecordedTool, ...]
    facts: tuple[RecordedFact, ...]
    infrastructure: dict[str, Any]


def normalize_case(
    *,
    case: object,
    turns: list[dict[str, Any]],
    subject_facts: dict[str, list[dict[str, Any]]],
    auxiliary_turns: list[dict[str, Any]] | None = None,
) -> NormalizedCase:
    turn_records: list[RecordedTurn] = []
    event_records: list[RecordedEvent] = []
    tool_records: list[RecordedTool] = []
    failures: list[dict[str, Any]] = []
    statuses: list[str] = []

    staged_turns = [(False, item) for item in (auxiliary_turns or [])] + [
        (True, item) for item in turns
    ]
    for scoreable, item in staged_turns:
        run = item["run"]
        run_id = _required(run, "id")
        status = str(run.get("status") or "unknown")
        statuses.append(status)
        (
            run_events,
            run_tools,
            score_events,
            score_tools,
            run_failures,
            usage,
        ) = _normalize_run_events(run_id, item.get("events") or (), status)
        event_records.extend(run_events)
        tool_records.extend(run_tools)
        failures.extend(run_failures)
        if not scoreable:
            continue
        assistant_content = _assistant_content(item.get("conversation_state") or {})
        turn_records.append(
            RecordedTurn(
                case_key=str(getattr(case, "key")),
                conversation_key=str(item["conversation_key"]),
                run_id=run_id,
                attempt_count=int(run.get("attempt_count") or 0),
                observation=TurnObservation(
                    status=status,
                    assistant_text=assistant_content or None,
                    candidate_assistant_text=assistant_content or None,
                    events=tuple(score_events),
                    tools=tuple(score_tools),
                    usage=usage,
                    elapsed_seconds=_elapsed_seconds(run),
                ),
            )
        )

    fact_records = tuple(
        RecordedFact(
            subject_key=subject_key,
            fact_id=str(fact.get("id") or ""),
            observation=FactObservation(
                key=str(fact.get("key") or fact.get("normalized_key") or ""),
                value=str(fact.get("value") or ""),
            ),
        )
        for subject_key, facts in sorted(subject_facts.items())
        for fact in facts
        if str(fact.get("value") or "").strip()
    )
    facts_by_subject = {
        subject_key: tuple(
            record.observation
            for record in fact_records
            if record.subject_key == subject_key
        )
        for subject_key in subject_facts
    }
    results_by_conversation = {
        conversation_key: tuple(
            record.observation
            for record in turn_records
            if record.conversation_key == conversation_key
        )
        for conversation_key in {record.conversation_key for record in turn_records}
    }
    score = score_observations(
        case=case,
        facts_by_subject=facts_by_subject,
        results_by_conversation=results_by_conversation,
    )
    return NormalizedCase(
        score=score,
        turns=tuple(turn_records),
        events=tuple(event_records),
        tools=tuple(tool_records),
        facts=fact_records,
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
) -> tuple[
    list[RecordedEvent],
    list[RecordedTool],
    list[EventObservation],
    list[ToolObservation],
    list[dict[str, Any]],
    dict[str, int],
]:
    recorded_events: list[RecordedEvent] = []
    recorded_tools: list[RecordedTool] = []
    score_events: list[EventObservation] = []
    score_tools: list[ToolObservation] = []
    failures: list[dict[str, Any]] = []
    event_types: list[str] = []
    model_events: set[tuple[str, str]] = set()
    usage: dict[str, int] = {}
    last_sequence = 0
    seen_event_ids: set[str] = set()
    for event in events:
        payload = dict(event.data.get("payload") or {})
        actual_run_id = str(event.data.get("run_id") or "")
        event_id = str(event.data.get("id") or event.event_id or "")
        correlation_id = str(event.data.get("correlation_id") or "")
        causation_id = (
            str(event.data["causation_id"]) if event.data.get("causation_id") else None
        )
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
        if not event_id or event_id in seen_event_ids:
            failures.append({"kind": "event_identity", "pass": False})
        if correlation_id != run_id:
            failures.append({"kind": "event_correlation", "pass": False})
        if causation_id is not None and causation_id not in seen_event_ids:
            failures.append({"kind": "event_causation", "pass": False})
        if event_id:
            seen_event_ids.add(event_id)
        recorded_events.append(
            RecordedEvent(
                event_id=event_id,
                run_id=run_id,
                sequence=sequence,
                event_type=event_type,
                attempt=_optional_int(event.data.get("attempt")),
                correlation_id=correlation_id,
                causation_id=causation_id,
                payload=payload,
            )
        )
        canonical_type = _canonical_event_type(event_type, payload)
        if canonical_type:
            score_events.append(EventObservation(type=canonical_type))
        if event_type in {"model.request.started", "model.response.completed"}:
            role = str(payload.get("role") or "")
            model_events.add((role, event_type))
        if event_type == "tool.call.completed":
            name = str(payload.get("name") or payload.get("tool_name") or "")
            succeeded = payload.get("succeeded", True) is True
            recorded_tools.append(
                RecordedTool(
                    run_id=run_id,
                    name=name,
                    succeeded=succeeded,
                    payload=payload,
                )
            )
            score_tools.append(ToolObservation(name=name, succeeded=succeeded))
        if event_type == "run.completed":
            usage = _usage(payload.get("usage"))

    if status == "succeeded":
        missing = sorted(SUCCESS_REQUIRED_EVENTS - set(event_types))
        if missing:
            failures.append(
                {"kind": "required_events", "pass": False, "missing": missing}
            )
        for role in MODEL_ROLES:
            missing_model_events = [
                event_type
                for event_type in ("model.request.started", "model.response.completed")
                if (role, event_type) not in model_events
            ]
            if missing_model_events:
                failures.append(
                    {
                        "kind": "required_model_events",
                        "pass": False,
                        "role": role,
                        "missing": missing_model_events,
                    }
                )
        if "run.failed" in event_types or "run.cancelled" in event_types:
            failures.append({"kind": "terminal_event_conflict", "pass": False})
    elif not any(item in TERMINAL_EVENT_TYPES for item in event_types):
        failures.append(
            {"kind": "terminal_event_missing", "pass": False, "status": status}
        )
    return (
        recorded_events,
        recorded_tools,
        score_events,
        score_tools,
        failures,
        usage,
    )


def _canonical_event_type(event_type: str, payload: dict[str, Any]) -> str:
    if event_type == "model.request.started":
        if payload.get("role") == "reviewer":
            return "memory.review.request"
        return "model.request"
    if event_type == "model.response.completed":
        return "model.response"
    return event_type


def _usage(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): int(item)
        for key, item in value.items()
        if isinstance(item, int) and not isinstance(item, bool)
    }


def _assistant_content(state: dict[str, Any]) -> str:
    messages = state.get("messages")
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") == "assistant":
            return str(message.get("content") or "")
    return ""


def _elapsed_seconds(run: dict[str, Any]) -> float:
    started = _datetime(run.get("started_at"))
    finished = _datetime(run.get("finished_at"))
    if started is None or finished is None:
        return 0.0
    return max(0.0, (finished - started).total_seconds())


def _datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _required(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"run response is missing {key}")
    return value
