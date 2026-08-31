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

    async def find(self, conversation_id: str) -> dict[str, Any] | None:
        result = await self._connection.execute(
            select(conversations).where(conversations.c.id == conversation_id)
        )
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

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

    async def list_summary_source_message_ids(self, summary_id: str) -> list[str]:
        """Return summary sources in the immutable conversation order."""

        result = await self._connection.execute(
            select(summary_sources.c.message_id)
            .join(messages, messages.c.id == summary_sources.c.message_id)
            .where(summary_sources.c.summary_id == summary_id)
            .order_by(messages.c.sequence)
        )
        return [str(value) for value in result.scalars()]

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

    async def create_compaction(
        self,
        *,
        payload: Mapping[str, Any],
        source_message_ids: Sequence[str],
        expected_summary_version: int,
        expected_previous_summary_id: str | None,
    ) -> dict[str, Any]:
        """Persist one model summary with a reconstructable contiguous prefix.

        The caller holds the enclosing terminal-run transaction. This method
        validates the summary chain before its inserts so an invalid source range
        rolls back the assistant, memory, summary, and terminal state together.
        """

        summary_payload = values(payload)
        conversation_id = str(summary_payload["conversation_id"])
        current = await self.latest_summary(conversation_id)
        current_version = int(current["version"]) if current else 0
        current_id = str(current["id"]) if current else None
        current_through = int(current["through_sequence"]) if current else 0
        if (
            current_version != expected_summary_version
            or current_id != expected_previous_summary_id
        ):
            raise NotFoundError("conversation summary changed before compaction")
        if int(summary_payload["version"]) != current_version + 1:
            raise ValueError("conversation summary version must advance by one")
        through_sequence = int(summary_payload["through_sequence"])
        if through_sequence <= current_through:
            raise ValueError("conversation compaction must advance its source boundary")
        if summary_payload.get("previous_summary_id") != current_id:
            raise ValueError("conversation compaction previous summary does not match")
        history = await self.list_messages(conversation_id)
        expected_sources = tuple(
            str(message["id"])
            for message in history
            if int(message["sequence"]) <= through_sequence
        )
        if tuple(source_message_ids) != expected_sources:
            raise ValueError("summary sources must cover a contiguous history prefix")
        return await self.create_summary(summary_payload, source_message_ids)
