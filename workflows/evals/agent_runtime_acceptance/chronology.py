"""Read-only stage timeline from evidence already captured by an acceptance case."""

from __future__ import annotations

from typing import Any


STAGE_EVENTS = {
    "context": {
        "context.built",
        "tool.call.requested",
        "tool.call.completed",
    },
    "generation": {"message.committed"},
    "extraction_and_validation": {"memory.proposed"},
    "storage": {"memory.committed"},
    "provider": {
        "model.request.started",
        "model.response.completed",
        "model.request.failed",
        "model.request.cancelled",
    },
}


def case_chronology(case: Any) -> list[dict[str, Any]]:
    """Annotate each scored turn without inferring that an unobserved stage failed."""
    events_by_run: dict[str, list[Any]] = {}
    for event in case.events:
        events_by_run.setdefault(str(event.run_id), []).append(event)
    result = []
    for turn in case.turns:
        observed = sorted(
            events_by_run.get(str(turn.run_id), ()), key=lambda event: event.sequence
        )
        result.append(
            {
                "conversation_key": turn.conversation_key,
                "run_id": turn.run_id,
                "status": turn.observation.status,
                "stages": {
                    stage: [
                        {"sequence": event.sequence, "event_type": event.event_type}
                        for event in observed
                        if event.event_type in event_types
                        or (
                            event.event_type
                            in {"model.request.started", "model.response.completed"}
                            and event.payload.get("role")
                            == (
                                "reviewer"
                                if stage == "extraction_and_validation"
                                else "conversation"
                            )
                            and stage in {"generation", "extraction_and_validation"}
                        )
                    ]
                    for stage, event_types in STAGE_EVENTS.items()
                },
                "event_order": [event.event_type for event in observed],
            }
        )
    return result
