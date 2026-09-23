"""Authoritative, boundary-checked source-message locators for fact revisions."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection

from ..errors import RuntimeValidationError
from .metadata import (
    conversations,
    memory_facts,
    memory_revision_sources,
    memory_revisions,
    memory_subjects,
    messages,
)


async def list_revision_sources(
    connection: AsyncConnection,
    revision_id: str,
    *,
    workspace_id: str | None = None,
    subject_id: str | None = None,
    purpose: str | None = None,
) -> list[dict[str, Any]]:
    result = await connection.execute(
        select(
            *memory_revision_sources.c,
            messages.c.conversation_id.label("conversation_id"),
            messages.c.sequence.label("message_sequence"),
            messages.c.workspace_id.label("source_workspace_id"),
            conversations.c.workspace_id.label("conversation_workspace_id"),
            conversations.c.memory_subject_id.label("conversation_subject_id"),
            conversations.c.purpose.label("conversation_purpose"),
            memory_revisions.c.workspace_id.label("revision_workspace_id"),
            memory_revisions.c.subject_id.label("revision_subject_id"),
            memory_facts.c.workspace_id.label("fact_workspace_id"),
            memory_facts.c.subject_id.label("fact_subject_id"),
            memory_subjects.c.workspace_id.label("subject_workspace_id"),
            memory_subjects.c.purpose.label("subject_purpose"),
        )
        .select_from(memory_revision_sources)
        .join(
            memory_revisions,
            memory_revisions.c.id == memory_revision_sources.c.revision_id,
        )
        .join(memory_facts, memory_facts.c.id == memory_revisions.c.fact_id)
        .join(messages, messages.c.id == memory_revision_sources.c.message_id)
        .join(conversations, conversations.c.id == messages.c.conversation_id)
        .join(memory_subjects, memory_subjects.c.id == memory_revisions.c.subject_id)
        .where(memory_revision_sources.c.revision_id == revision_id)
        .order_by(
            messages.c.sequence,
            memory_revision_sources.c.start_char,
            memory_revision_sources.c.id,
        )
    )
    sources = []
    for row in result.mappings():
        source = dict(row)
        owner_workspace = str(source["revision_workspace_id"])
        owner_subject = str(source["revision_subject_id"])
        owner_purpose = str(source["subject_purpose"])
        if (
            any(
                str(source[key]) != owner_workspace
                for key in (
                    "source_workspace_id",
                    "conversation_workspace_id",
                    "fact_workspace_id",
                    "subject_workspace_id",
                )
            )
            or any(
                str(source[key]) != owner_subject
                for key in ("conversation_subject_id", "fact_subject_id")
            )
            or source["conversation_purpose"] != owner_purpose
            or (workspace_id is not None and owner_workspace != workspace_id)
            or (subject_id is not None and owner_subject != subject_id)
            or (purpose is not None and owner_purpose != purpose)
        ):
            raise RuntimeValidationError(
                "memory source boundary does not match its fact"
            )
        sources.append(
            {
                key: source[key]
                for key in (
                    "id",
                    "revision_id",
                    "message_id",
                    "conversation_id",
                    "message_sequence",
                    "start_char",
                    "end_char",
                    "quote",
                    "message_sha256",
                )
            }
        )
    return sources
