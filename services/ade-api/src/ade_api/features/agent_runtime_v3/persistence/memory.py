"""Repositories for subject-bound structured memory state."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import and_, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from .base import OptimisticLockError, fetch_one, values
from .metadata import (
    memory_embeddings,
    memory_entities,
    memory_facts,
    memory_revision_predecessors,
    memory_revision_sources,
    memory_revisions,
    memory_subjects,
)


class MemoryRepository:
    """Persist typed memory without allowing cross-workspace references."""

    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def create_subject(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            insert(memory_subjects)
            .values(**values(payload))
            .returning(*memory_subjects.c),
            "memory subject was not created",
        )

    async def get_subject(self, subject_id: str) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            select(memory_subjects).where(memory_subjects.c.id == subject_id),
            "memory subject does not exist",
        )

    async def lock_subject(self, subject_id: str) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            select(memory_subjects)
            .where(memory_subjects.c.id == subject_id)
            .with_for_update(),
            "memory subject does not exist",
        )

    async def create_entity(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            insert(memory_entities)
            .values(**values(payload))
            .returning(*memory_entities.c),
            "memory entity was not created",
        )

    async def list_entities(self, subject_id: str) -> list[dict[str, Any]]:
        result = await self._connection.execute(
            select(memory_entities)
            .where(memory_entities.c.subject_id == subject_id)
            .order_by(memory_entities.c.created_at, memory_entities.c.id)
        )
        return [dict(row) for row in result.mappings()]

    async def create_fact(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            insert(memory_facts).values(**values(payload)).returning(*memory_facts.c),
            "memory fact was not created",
        )

    async def get_fact(self, fact_id: str) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            select(memory_facts).where(memory_facts.c.id == fact_id),
            "memory fact does not exist",
        )

    async def list_active_facts(self, subject_id: str) -> list[dict[str, Any]]:
        result = await self._connection.execute(
            select(memory_facts)
            .where(
                and_(
                    memory_facts.c.subject_id == subject_id,
                    memory_facts.c.status == "active",
                )
            )
            .order_by(memory_facts.c.normalized_key)
        )
        return [dict(row) for row in result.mappings()]

    async def list_facts(self, subject_id: str) -> list[dict[str, Any]]:
        result = await self._connection.execute(
            select(memory_facts)
            .where(memory_facts.c.subject_id == subject_id)
            .order_by(memory_facts.c.created_at, memory_facts.c.id)
        )
        return [dict(row) for row in result.mappings()]

    async def list_revisions(self, fact_id: str) -> list[dict[str, Any]]:
        result = await self._connection.execute(
            select(memory_revisions)
            .where(memory_revisions.c.fact_id == fact_id)
            .order_by(memory_revisions.c.fact_version)
        )
        return [dict(row) for row in result.mappings()]

    async def list_revision_sources(self, revision_id: str) -> list[dict[str, Any]]:
        result = await self._connection.execute(
            select(memory_revision_sources)
            .where(memory_revision_sources.c.revision_id == revision_id)
            .order_by(
                memory_revision_sources.c.message_id,
                memory_revision_sources.c.start_char,
            )
        )
        return [dict(row) for row in result.mappings()]

    async def create_initial_revision(
        self,
        fact_payload: Mapping[str, Any],
        revision_payload: Mapping[str, Any],
        *,
        evidence: Sequence[Mapping[str, Any]],
        predecessor_revision_ids: Sequence[str] = (),
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Create the fact projection and its version-one source revision."""

        fact = values(fact_payload)
        if fact.get("version") != 1 or fact.get("current_revision_id") is not None:
            raise ValueError("a new fact must start at version one without a pointer")
        created_fact = await self.create_fact(fact)
        revision = values(revision_payload)
        if (
            revision.get("fact_id") != created_fact["id"]
            or revision.get("fact_version") != 1
        ):
            raise ValueError(
                "the initial revision must be version one for the new fact"
            )
        created_revision = await fetch_one(
            self._connection,
            insert(memory_revisions).values(**revision).returning(*memory_revisions.c),
            "memory revision was not created",
        )
        if evidence:
            await self._connection.execute(
                insert(memory_revision_sources),
                [dict(item, revision_id=created_revision["id"]) for item in evidence],
            )
        if predecessor_revision_ids:
            await self._connection.execute(
                insert(memory_revision_predecessors),
                [
                    {
                        "revision_id": created_revision["id"],
                        "predecessor_revision_id": predecessor_id,
                    }
                    for predecessor_id in predecessor_revision_ids
                ],
            )
        await self._connection.execute(
            update(memory_facts)
            .where(memory_facts.c.id == created_fact["id"])
            .values(current_revision_id=created_revision["id"])
        )
        created_fact["current_revision_id"] = created_revision["id"]
        return created_fact, created_revision

    async def create_revision(
        self,
        payload: Mapping[str, Any],
        *,
        expected_fact_version: int,
        next_fact_status: str,
        updated_at: datetime,
        predecessor_revision_ids: Sequence[str] = (),
        evidence: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        """Advance one fact and store its immutable revision in one transaction.

        The caller owns the surrounding transaction. Updating the projection first
        with its expected version prevents stale reviewer output from being applied.
        """

        revision = values(payload)
        fact_id = str(revision["fact_id"])
        revision_id = str(revision["id"])
        if revision.get("fact_version") != expected_fact_version + 1:
            raise ValueError(
                "memory revision must advance the expected fact version by one"
            )
        created = await fetch_one(
            self._connection,
            insert(memory_revisions).values(**revision).returning(*memory_revisions.c),
            "memory revision was not created",
        )
        update_result = await self._connection.execute(
            update(memory_facts)
            .where(
                and_(
                    memory_facts.c.id == fact_id,
                    memory_facts.c.version == expected_fact_version,
                )
            )
            .values(
                value=revision.get("value"),
                status=next_fact_status,
                version=expected_fact_version + 1,
                current_revision_id=revision_id,
                updated_at=updated_at,
            )
        )
        if update_result.rowcount != 1:
            raise OptimisticLockError(
                "memory fact changed before its revision could commit"
            )

        if predecessor_revision_ids:
            await self._connection.execute(
                insert(memory_revision_predecessors),
                [
                    {
                        "revision_id": revision_id,
                        "predecessor_revision_id": predecessor_id,
                    }
                    for predecessor_id in predecessor_revision_ids
                ],
            )
        if evidence:
            await self._connection.execute(
                insert(memory_revision_sources),
                [dict(item, revision_id=revision_id) for item in evidence],
            )
        return created

    async def supersede_facts(
        self,
        expected_versions: Mapping[str, int],
        *,
        updated_at: datetime,
    ) -> None:
        for fact_id, expected_version in expected_versions.items():
            result = await self._connection.execute(
                update(memory_facts)
                .where(
                    and_(
                        memory_facts.c.id == fact_id,
                        memory_facts.c.version == expected_version,
                        memory_facts.c.status == "active",
                    )
                )
                .values(status="superseded", updated_at=updated_at)
            )
            if result.rowcount != 1:
                raise OptimisticLockError(
                    "memory fact changed before merge could commit"
                )

    async def create_embedding(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            insert(memory_embeddings)
            .values(**values(payload))
            .returning(*memory_embeddings.c),
            "memory embedding was not created",
        )

    async def search_active_facts(
        self,
        *,
        subject_id: str,
        query_embedding: Sequence[float],
        model_fingerprint: str,
        retrieval_policy_version: str,
        limit: int,
        maximum_distance: float | None = None,
    ) -> list[dict[str, Any]]:
        distance = memory_embeddings.c.embedding.cosine_distance(
            list(query_embedding)
        ).label("distance")
        statement = (
            select(memory_facts, distance)
            .join(
                memory_embeddings,
                and_(
                    memory_embeddings.c.fact_id == memory_facts.c.id,
                    memory_embeddings.c.revision_id
                    == memory_facts.c.current_revision_id,
                ),
            )
            .where(
                and_(
                    memory_facts.c.subject_id == subject_id,
                    memory_facts.c.status == "active",
                    memory_embeddings.c.subject_id == subject_id,
                    memory_embeddings.c.model_fingerprint == model_fingerprint,
                    memory_embeddings.c.retrieval_policy_version
                    == retrieval_policy_version,
                )
            )
            .order_by(distance)
            .limit(max(1, min(20, int(limit))))
        )
        if maximum_distance is not None:
            statement = statement.where(distance <= maximum_distance)
        result = await self._connection.execute(statement)
        return [dict(row) for row in result.mappings()]
