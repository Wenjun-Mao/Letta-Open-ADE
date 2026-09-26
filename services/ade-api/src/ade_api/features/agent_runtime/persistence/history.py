"""Bounded historical exchanges read inside the accepted turn's snapshot."""

from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.orm import aliased

from ..errors import RuntimeValidationError
from .history_lineage import read_history_annotations, source_message
from .metadata import (
    agent_definition_versions,
    agent_definitions,
    conversations,
    memory_subjects,
    messages,
    runs,
)

MAX_EXCHANGES = 128
MAX_MESSAGE_CHARS = 12_000


async def read_history_corpus(
    connection: AsyncConnection,
    *,
    workspace_id: str,
    subject_id: str,
    purpose: str,
    definition_root_id: str,
    current_run_id: str,
) -> dict[str, Any]:
    """Read completed same-character exchanges; caller owns the RR snapshot."""
    user = aliased(messages, name="history_user")
    assistant = aliased(messages, name="history_assistant")
    rows = (
        (
            await connection.execute(
                select(
                    runs.c.id.label("run_id"),
                    conversations.c.id.label("conversation_id"),
                    conversations.c.archived_at,
                    agent_definition_versions.c.id.label("definition_version_id"),
                    user.c.id.label("user_id"),
                    user.c.content.label("user_content"),
                    user.c.content_sha256.label("user_sha256"),
                    user.c.created_at.label("user_created_at"),
                    user.c.sequence.label("user_sequence"),
                    assistant.c.id.label("assistant_id"),
                    assistant.c.content.label("assistant_content"),
                    assistant.c.content_sha256.label("assistant_sha256"),
                    assistant.c.created_at.label("assistant_created_at"),
                    assistant.c.sequence.label("assistant_sequence"),
                )
                .select_from(runs)
                .join(conversations, conversations.c.id == runs.c.conversation_id)
                .join(
                    agent_definition_versions,
                    agent_definition_versions.c.id
                    == conversations.c.agent_definition_version_id,
                )
                .join(
                    agent_definitions,
                    agent_definitions.c.id
                    == agent_definition_versions.c.agent_definition_id,
                )
                .join(
                    memory_subjects,
                    memory_subjects.c.id == conversations.c.memory_subject_id,
                )
                .join(
                    user,
                    and_(
                        user.c.run_id == runs.c.id,
                        user.c.role == "user",
                        user.c.conversation_id == conversations.c.id,
                    ),
                )
                .join(
                    assistant,
                    and_(
                        assistant.c.run_id == runs.c.id,
                        assistant.c.role == "assistant",
                        assistant.c.conversation_id == conversations.c.id,
                    ),
                )
                .where(
                    runs.c.status == "succeeded",
                    runs.c.id != current_run_id,
                    runs.c.workspace_id == workspace_id,
                    conversations.c.workspace_id == workspace_id,
                    conversations.c.memory_subject_id == subject_id,
                    conversations.c.purpose == purpose,
                    memory_subjects.c.workspace_id == workspace_id,
                    memory_subjects.c.purpose == purpose,
                    agent_definition_versions.c.workspace_id == workspace_id,
                    agent_definition_versions.c.purpose == purpose,
                    agent_definition_versions.c.agent_definition_id
                    == definition_root_id,
                    agent_definitions.c.workspace_id == workspace_id,
                    agent_definitions.c.purpose == purpose,
                    user.c.workspace_id == workspace_id,
                    assistant.c.workspace_id == workspace_id,
                    user.c.sequence < assistant.c.sequence,
                    select(func.count())
                    .select_from(messages)
                    .where(messages.c.run_id == runs.c.id)
                    .correlate(runs)
                    .scalar_subquery()
                    == 2,
                )
                .order_by(assistant.c.created_at.desc(), assistant.c.id.desc())
                .limit(MAX_EXCHANGES + 1)
            )
        )
        .mappings()
        .all()
    )
    exchanges, omitted = (
        [],
        {
            "capacity_at_least": int(len(rows) > MAX_EXCHANGES),
            "content": 0,
            "annotation": 0,
        },
    )
    for row in rows[:MAX_EXCHANGES]:
        source = dict(row)
        exchange = {
            "run_id": str(source["run_id"]),
            "conversation_id": str(source["conversation_id"]),
            "definition_version_id": str(source["definition_version_id"]),
            "archived": source["archived_at"] is not None,
            "messages": [
                source_message(source, "user"),
                source_message(source, "assistant"),
            ],
        }
        if any(
            len(message["content"]) > MAX_MESSAGE_CHARS
            for message in exchange["messages"]
        ):
            omitted["content"] += 1
            continue
        for message in exchange["messages"]:
            if (
                hashlib.sha256(message["content"].encode()).hexdigest()
                != message["content_sha256"]
            ):
                raise RuntimeValidationError(
                    "historical message failed integrity check"
                )
        annotations = await read_history_annotations(
            connection,
            exchange,
            workspace_id=workspace_id,
            subject_id=subject_id,
            purpose=purpose,
        )
        if annotations is None:
            omitted["annotation"] += 1
            continue
        exchange["annotations"] = annotations
        exchanges.append(exchange)
    return {"exchanges": exchanges, "omitted": omitted}
