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
    origin = (
        (
            await connection.execute(
                select(
                    memory_revisions.c.run_id,
                    memory_revisions.c.action_id,
                    memory_revisions.c.workspace_id,
                    memory_revisions.c.subject_id,
                    memory_facts.c.workspace_id.label("fact_workspace_id"),
                    memory_facts.c.subject_id.label("fact_subject_id"),
                    memory_subjects.c.purpose.label("subject_purpose"),
                )
                .join(memory_facts, memory_facts.c.id == memory_revisions.c.fact_id)
                .join(
                    memory_subjects,
                    memory_subjects.c.id == memory_revisions.c.subject_id,
                )
                .where(memory_revisions.c.id == revision_id)
            )
        )
        .mappings()
        .one_or_none()
    )
    if origin is None:
        raise RuntimeValidationError("memory revision does not exist")
    owner_workspace = str(origin["workspace_id"])
    owner_subject = str(origin["subject_id"])
    if (
        str(origin["fact_workspace_id"]) != owner_workspace
        or str(origin["fact_subject_id"]) != owner_subject
        or (workspace_id is not None and owner_workspace != workspace_id)
        or (subject_id is not None and owner_subject != subject_id)
        or (purpose is not None and origin["subject_purpose"] != purpose)
    ):
        raise RuntimeValidationError("memory revision boundary does not match its fact")
    current_message = None
    if origin["run_id"] is not None:
        current_message = (
            (
                await connection.execute(
                    select(messages.c.id, messages.c.sequence).where(
                        messages.c.run_id == origin["run_id"],
                        messages.c.role == "user",
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
    result = await connection.execute(
        select(
            *memory_revision_sources.c,
            messages.c.conversation_id.label("conversation_id"),
            messages.c.sequence.label("message_sequence"),
            messages.c.role.label("message_role"),
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
        authority = str(source["authority_role"])
        if (
            authority
            in {
                "user_assertion",
                "user_endorsement",
                "user_resolution",
                "user_antecedent",
            }
            and source["message_role"] != "user"
        ) or (
            authority == "assistant_referent" and source["message_role"] != "assistant"
        ):
            raise RuntimeValidationError(
                "memory source role does not match its message"
            )
        if authority in {"user_resolution", "user_antecedent"}:
            if current_message is None:
                raise RuntimeValidationError("new natural source lacks current run")
            if authority == "user_resolution" and str(source["message_id"]) != str(
                current_message["id"]
            ):
                raise RuntimeValidationError("resolution is not current authority")
            if authority == "user_antecedent" and int(
                source["message_sequence"]
            ) >= int(current_message["sequence"]):
                raise RuntimeValidationError("antecedent does not precede authority")
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
                    "authority_role",
                )
            }
        )
    if origin["action_id"] is not None and sources:
        raise RuntimeValidationError("operator action cannot cite a message source")
    if origin["run_id"] is not None and not any(
        source["authority_role"]
        in {"user_assertion", "user_endorsement", "user_resolution"}
        for source in sources
    ):
        raise RuntimeValidationError("run memory revision has no user authority")
    return sources
