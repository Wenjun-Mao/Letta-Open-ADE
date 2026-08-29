from __future__ import annotations

from typing import Any
from uuid import uuid4

from .persistence.runs import RunRepository


TERMINAL_RUN_STATUSES = frozenset({"succeeded", "failed", "cancelled"})


async def append_run_event(
    repository: RunRepository,
    *,
    run_id: str,
    event_type: str,
    payload: dict[str, Any],
    attempt: int | None = None,
    causation_id: str | None = None,
    visibility: str = "operator",
) -> dict[str, Any]:
    return await repository.append_ordered_event(
        event_id=str(uuid4()),
        run_id=run_id,
        event_type=event_type,
        correlation_id=run_id,
        payload=payload,
        attempt=attempt,
        causation_id=causation_id,
        visibility=visibility,
        outbox_id=str(uuid4()),
    )


def event_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "schema_version": int(row["schema_version"]),
        "run_id": str(row["run_id"]),
        "sequence": int(row["sequence"]),
        "attempt": row.get("attempt"),
        "type": str(row["event_type"]),
        "occurred_at": row["occurred_at"],
        "correlation_id": str(row["correlation_id"]),
        "causation_id": (str(row["causation_id"]) if row.get("causation_id") else None),
        "visibility": str(row["visibility"]),
        "payload": dict(row.get("payload") or {}),
    }
