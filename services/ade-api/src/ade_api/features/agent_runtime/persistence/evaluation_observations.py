"""Private, bounded persistence readbacks; never a model or public API input."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection

from .metadata import (
    conversations,
    memory_entities,
    memory_facts,
    memory_revision_predecessors,
    memory_revision_sources,
    memory_revisions,
    memory_subjects,
    runs,
)

CONTRACT = "ade-private-evaluation-observations-v1"
MAX_ROWS = 512
MAX_SNAPSHOT_BYTES = 600_000


class ObservationLimit(Exception):
    """No partial state can be advertised as a complete observation."""


def _scalar(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    raise TypeError("Unsupported private observation value")


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=_scalar,
    ).encode()


def sealed(value: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(canonical(value))
    return {**normalized, "sha256": hashlib.sha256(canonical(normalized)).hexdigest()}


def observation_binding(run: dict, conversation: dict, definition: dict) -> dict:
    return {
        "run_id": str(run["id"]),
        "conversation_id": str(conversation["id"]),
        "definition_version_id": str(definition["id"]),
        "policy_binding": str(definition["memory_policy_version"]),
        "accepted_memory_generation": int(run["accepted_memory_generation"]),
        "scope": {
            "workspace": str(conversation["workspace_id"]),
            "subject": str(conversation["memory_subject_id"]),
            "purpose": str(conversation["purpose"]),
            "root": str(definition["agent_definition_id"]),
        },
    }


async def read_snapshot(connection: AsyncConnection, *, binding: dict) -> dict:
    """Caller owns RR transaction. All rows, not active/fact-associated projections.

    Memory is subject-wide, not character-root filtered. Activity retains only
    identities/statuses for the same subject, never other subjects' source text.
    """
    scope = binding["scope"]
    subject = (
        await connection.execute(
            select(memory_subjects.c.memory_generation).where(
                memory_subjects.c.id == scope["subject"],
                memory_subjects.c.workspace_id == scope["workspace"],
                memory_subjects.c.purpose == scope["purpose"],
            )
        )
    ).scalar_one()

    async def rows(statement):
        result = (await connection.execute(statement.limit(MAX_ROWS + 1))).mappings()
        values = [dict(row) for row in result]
        if len(values) > MAX_ROWS:
            raise ObservationLimit()
        return sorted(values, key=canonical)

    revisions = select(memory_revisions.c.id).where(
        memory_revisions.c.subject_id == scope["subject"],
        memory_revisions.c.workspace_id == scope["workspace"],
    )
    state = {"generation": int(subject)}
    for name, table in (
        ("facts", memory_facts),
        ("entities", memory_entities),
        ("revisions", memory_revisions),
    ):
        state[name] = await rows(
            select(table).where(
                table.c.subject_id == scope["subject"],
                table.c.workspace_id == scope["workspace"],
            )
        )
    for name, table in (
        ("sources", memory_revision_sources),
        ("predecessors", memory_revision_predecessors),
    ):
        state[name] = await rows(
            select(table).where(table.c.revision_id.in_(revisions))
        )
    activity = await rows(
        select(
            runs.c.id,
            runs.c.status,
            runs.c.attempt_count,
            runs.c.created_at,
            runs.c.started_at,
            runs.c.finished_at,
        )
        .join(conversations, conversations.c.id == runs.c.conversation_id)
        .where(
            conversations.c.memory_subject_id == scope["subject"],
            conversations.c.workspace_id == scope["workspace"],
            conversations.c.purpose == scope["purpose"],
            runs.c.workspace_id == scope["workspace"],
        )
    )
    result = {"status": "complete", "state": state, "subject_run_activity": activity}
    if len(canonical(result)) > MAX_SNAPSHOT_BYTES:
        raise ObservationLimit()
    return sealed(result)


async def observe_snapshot(connection: AsyncConnection, *, binding: dict) -> dict:
    # A savepoint also protects the mandatory turn snapshot from SQL failures.
    try:
        async with connection.begin_nested():
            return await read_snapshot(connection, binding=binding)
    except ObservationLimit:
        return {"status": "truncated"}
    except Exception:
        return {"status": "unavailable"}


def isolation_status(before: dict, after: dict, *, run_id: str, attempt: int) -> str:
    if before.get("status") != "complete" or after.get("status") != "complete":
        return "unavailable"
    other = []
    for snapshot in (before, after):
        activity = snapshot["subject_run_activity"]
        current = [row for row in activity if row["id"] == run_id]
        if len(current) != 1 or current[0]["attempt_count"] != attempt:
            return "attempt_mismatch"
        remaining = [row for row in activity if row["id"] != run_id]
        if any(row["status"] in {"pending", "running"} for row in remaining):
            return "overlapping_activity"
        other.append(remaining)
    return "isolated" if other[0] == other[1] else "overlapping_activity"


def observations(*, evidence: Any, after: dict) -> dict:
    before = evidence.persistence_before or {"status": "unavailable"}
    binding = evidence.observation_binding or {}
    return sealed(
        {
            "contract": CONTRACT,
            "binding": {**binding, "attempt": evidence.attempt},
            "before": before,
            "after": after,
            "isolation": isolation_status(
                before, after, run_id=evidence.run_id, attempt=evidence.attempt
            ),
            "history": evidence.history_observation or {"status": "unavailable"},
        }
    )
