"""Repositories for immutable conversation history and summaries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import and_, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from .base import NotFoundError, fetch_one, values
from .metadata import conversations, conversation_summaries, messages, summary_sources


class ConversationRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def create(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            insert(conversations).values(**values(payload)).returning(*conversations.c),
            "conversation was not created",
        )

    async def get(self, conversation_id: str) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            select(conversations).where(conversations.c.id == conversation_id),
            "conversation does not exist",
        )

    async def get_for_update(self, conversation_id: str) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            select(conversations)
            .where(conversations.c.id == conversation_id)
            .with_for_update(),
            "conversation does not exist",
        )

    async def advance_version(self, conversation_id: str, expected_version: int) -> int:
        result = await self._connection.execute(
            update(conversations)
            .where(
                and_(
                    conversations.c.id == conversation_id,
                    conversations.c.version == expected_version,
                )
            )
            .values(version=expected_version + 1)
            .returning(conversations.c.version)
        )
        version = result.scalar_one_or_none()
        if version is None:
            raise NotFoundError("conversation version changed before commit")
        return int(version)

    async def append_message(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Append the next immutable message while holding the conversation row lock."""

        message = values(payload)
        conversation_id = str(message["conversation_id"])
        locked = await self._connection.execute(
            select(conversations.c.id)
            .where(conversations.c.id == conversation_id)
            .with_for_update()
        )
        if locked.scalar_one_or_none() is None:
            raise NotFoundError("conversation does not exist")
        sequence = await self._connection.scalar(
            select(func.coalesce(func.max(messages.c.sequence), 0) + 1).where(
                messages.c.conversation_id == conversation_id
            )
        )
        message["sequence"] = int(sequence)
        return await fetch_one(
            self._connection,
            insert(messages).values(**message).returning(*messages.c),
            "message was not created",
        )

    async def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        result = await self._connection.execute(
            select(messages)
            .where(messages.c.conversation_id == conversation_id)
            .order_by(messages.c.sequence)
        )
        return [dict(row) for row in result.mappings()]

    async def latest_summary(self, conversation_id: str) -> dict[str, Any] | None:
        result = await self._connection.execute(
            select(conversation_summaries)
            .where(conversation_summaries.c.conversation_id == conversation_id)
            .order_by(conversation_summaries.c.version.desc())
            .limit(1)
        )
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    async def create_summary(
        self, payload: Mapping[str, Any], source_message_ids: Sequence[str]
    ) -> dict[str, Any]:
        summary = await fetch_one(
            self._connection,
            insert(conversation_summaries)
            .values(**values(payload))
            .returning(*conversation_summaries.c),
            "conversation summary was not created",
        )
        if source_message_ids:
            await self._connection.execute(
                insert(summary_sources),
                [
                    {"summary_id": summary["id"], "message_id": message_id}
                    for message_id in source_message_ids
                ],
            )
        return summary
