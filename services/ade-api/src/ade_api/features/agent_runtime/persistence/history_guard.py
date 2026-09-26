"""Fresh source authorization for an already admitted historical packet."""

from __future__ import annotations

import hashlib
import asyncio
import time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection

from ..errors import RuntimeValidationError
from .history_lineage import read_history_annotations
from .metadata import (
    agent_definition_versions,
    conversations,
    memory_subjects,
    messages,
    runs,
)


def _integrity_failure() -> RuntimeValidationError:
    return RuntimeValidationError(
        "Admitted historical evidence is no longer verifiable",
        detail_code="natural_history_integrity",
    )


async def validate_admitted_history(
    connection: AsyncConnection,
    *,
    exchanges: list[dict[str, Any]],
    workspace_id: str,
    subject_id: str,
    purpose: str,
    definition_root_id: str,
    current_run_id: str,
) -> set[str]:
    """Return only genuinely absent windows; altered or cross-scope rows are fatal.

    The caller decides whether an absent window may be omitted before first
    exposure. The same result is fatal after exposure and during finalization.
    """
    if not exchanges:
        return set()
    ids = [
        str(message["id"]) for exchange in exchanges for message in exchange["messages"]
    ]
    if len(ids) != len(set(ids)):
        raise _integrity_failure()
    rows = (
        (
            await connection.execute(
                select(
                    messages.c.id.label("message_id"),
                    messages.c.run_id,
                    messages.c.conversation_id,
                    messages.c.workspace_id.label("message_workspace_id"),
                    messages.c.role,
                    messages.c.content,
                    messages.c.content_sha256,
                    messages.c.sequence,
                    runs.c.status.label("run_status"),
                    runs.c.workspace_id.label("run_workspace_id"),
                    conversations.c.workspace_id.label("conversation_workspace_id"),
                    conversations.c.memory_subject_id,
                    conversations.c.purpose.label("conversation_purpose"),
                    agent_definition_versions.c.id.label("definition_version_id"),
                    agent_definition_versions.c.agent_definition_id,
                    agent_definition_versions.c.workspace_id.label(
                        "definition_workspace_id"
                    ),
                    agent_definition_versions.c.purpose.label("definition_purpose"),
                    memory_subjects.c.workspace_id.label("subject_workspace_id"),
                    memory_subjects.c.purpose.label("subject_purpose"),
                )
                .select_from(messages)
                .join(runs, runs.c.id == messages.c.run_id)
                .join(conversations, conversations.c.id == messages.c.conversation_id)
                .join(
                    agent_definition_versions,
                    agent_definition_versions.c.id
                    == conversations.c.agent_definition_version_id,
                )
                .join(
                    memory_subjects,
                    memory_subjects.c.id == conversations.c.memory_subject_id,
                )
                .where(messages.c.id.in_(ids))
            )
        )
        .mappings()
        .all()
    )
    by_id = {str(row["message_id"]): row for row in rows}
    missing: set[str] = set()
    for exchange in exchanges:
        source_run_id = str(exchange["run_id"])
        source_messages = exchange["messages"]
        if source_run_id == current_run_id or len(source_messages) != 2:
            raise _integrity_failure()
        present = [by_id.get(str(message["id"])) for message in source_messages]
        if [message["role"] for message in source_messages] != ["user", "assistant"]:
            raise _integrity_failure()
        for message, row in zip(source_messages, present, strict=True):
            if row is None:
                continue
            content = str(row["content"])
            digest = hashlib.sha256(content.encode()).hexdigest()
            if (
                str(row["run_id"]) != source_run_id
                or str(row["conversation_id"]) != str(exchange["conversation_id"])
                or str(row["definition_version_id"])
                != str(exchange["definition_version_id"])
                or row["run_status"] != "succeeded"
                or str(row["message_workspace_id"]) != workspace_id
                or str(row["run_workspace_id"]) != workspace_id
                or str(row["conversation_workspace_id"]) != workspace_id
                or str(row["definition_workspace_id"]) != workspace_id
                or str(row["subject_workspace_id"]) != workspace_id
                or str(row["memory_subject_id"]) != subject_id
                or row["conversation_purpose"] != purpose
                or row["definition_purpose"] != purpose
                or row["subject_purpose"] != purpose
                or str(row["agent_definition_id"]) != definition_root_id
                or row["role"] != message["role"]
                or int(row["sequence"]) != int(message["sequence"])
                or content != message["content"]
                or digest != row["content_sha256"]
                or digest != message["content_sha256"]
            ):
                raise _integrity_failure()
        if any(row is None for row in present):
            missing.add(source_run_id)
            continue
        count = await connection.scalar(
            select(func.count())
            .select_from(messages)
            .where(messages.c.run_id == source_run_id)
        )
        if count != 2 or int(source_messages[0]["sequence"]) >= int(
            source_messages[1]["sequence"]
        ):
            raise _integrity_failure()
        annotations = await read_history_annotations(
            connection,
            exchange,
            workspace_id=workspace_id,
            subject_id=subject_id,
            purpose=purpose,
        )
        if annotations != exchange["annotations"]:
            raise _integrity_failure()
    return missing


async def validate_history_before_dispatch(
    connection: AsyncConnection,
    *,
    exchanges: list[dict[str, Any]],
    workspace_id: str,
    subject_id: str,
    purpose: str,
    definition_root_id: str,
    current_run_id: str,
    accepted_memory_generation: int,
) -> set[str]:
    """One fresh authorization contract for generation and corpus embeddings."""
    generation = await connection.scalar(
        select(memory_subjects.c.memory_generation).where(
            memory_subjects.c.id == subject_id,
            memory_subjects.c.workspace_id == workspace_id,
        )
    )
    if generation != accepted_memory_generation:
        raise RuntimeValidationError(
            "Subject memory changed before history exposure",
            detail_code="natural_history_stale_generation",
        )
    return await validate_admitted_history(
        connection,
        exchanges=exchanges,
        workspace_id=workspace_id,
        subject_id=subject_id,
        purpose=purpose,
        definition_root_id=definition_root_id,
        current_run_id=current_run_id,
    )


async def validate_history_at_commit(
    connection: AsyncConnection,
    *,
    exchanges: tuple[dict[str, Any], ...],
    deadline: float | None,
    conversation: dict[str, Any],
    subject_id: str,
    current_run_id: str,
) -> None:
    """Bound only the new check by the successful attempt's absolute deadline."""
    if not exchanges:
        return
    if deadline is None:
        raise _integrity_failure()
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RuntimeValidationError(
            "History finalization exceeded the attempt deadline",
            detail_code="natural_history_timeout",
        )

    async def check() -> set[str]:
        definition_root_id = await connection.scalar(
            select(agent_definition_versions.c.agent_definition_id).where(
                agent_definition_versions.c.id
                == conversation["agent_definition_version_id"]
            )
        )
        if definition_root_id is None:
            raise _integrity_failure()
        return await validate_admitted_history(
            connection,
            exchanges=list(exchanges),
            workspace_id=str(conversation["workspace_id"]),
            subject_id=subject_id,
            purpose=str(conversation["purpose"]),
            definition_root_id=str(definition_root_id),
            current_run_id=current_run_id,
        )

    try:
        missing = await asyncio.wait_for(check(), timeout=remaining)
    except (TimeoutError, asyncio.TimeoutError) as exc:
        raise RuntimeValidationError(
            "History finalization timed out",
            detail_code="natural_history_timeout",
        ) from exc
    except SQLAlchemyError as exc:
        raise RuntimeValidationError(
            "History finalization could not validate sources",
            detail_code="natural_history_unavailable",
        ) from exc
    if missing:
        raise RuntimeValidationError(
            "Admitted historical source was removed before commit",
            detail_code="natural_history_missing",
        )
