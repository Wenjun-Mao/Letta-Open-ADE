from __future__ import annotations

import asyncio
import os
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from ade_api.features.agent_runtime_v3 import preview_session_service
from ade_api.features.agent_runtime_v3.contracts import CreatePreviewSessionRequest
from ade_api.features.agent_runtime_v3.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime_v3.persistence.conversations import (
    ConversationRepository as RealConversationRepository,
)
from ade_api.features.agent_runtime_v3.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime_v3.persistence.metadata import (
    agent_definition_versions,
    conversations,
    memory_entities,
    memory_subjects,
)
from ade_api.features.agent_runtime_v3.preview_session_service import (
    PreviewSessionService,
    _PreviewIdentity,
    _preview_identity,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="ADE_TEST_DATABASE_URL is required for PostgreSQL transaction tests",
)


class _PreparedDefinitions:
    async def prepare(self, request: object) -> dict[str, Any]:
        return {
            "definition_key": request.definition_key,
            "name": request.name,
            "model_key": request.model_key,
            "reviewer_model_key": request.reviewer_model_key,
            "embedding_model_key": request.embedding_model_key,
            "prompt_key": request.prompt_key,
            "prompt_sha256": "a" * 64,
            "prompt_content": "prompt",
            "persona_key": request.persona_key,
            "persona_sha256": "b" * 64,
            "persona_content": "persona",
            "tool_names": list(request.tool_names),
            "memory_policy_version": "typed-user-facts-v1",
            "qualification_state": "unqualified",
            "deployment_snapshot": [],
        }


class _ForcedRollback(RuntimeError):
    pass


def _request(idempotency_key: str) -> CreatePreviewSessionRequest:
    return CreatePreviewSessionRequest(
        idempotency_key=idempotency_key,
        name="PostgreSQL preview contract",
        subject_display_name="Zhang Wei",
        model_key="dgx_vllm::qwen",
        reviewer_model_key="dgx_vllm::qwen",
        embedding_model_key="dgx_embedding::qwen",
    )


async def _resource_counts(
    engine: AsyncEngine,
    identity: _PreviewIdentity,
) -> dict[str, int]:
    async with engine.connect() as connection:
        return {
            "definition": int(
                await connection.scalar(
                    select(func.count())
                    .select_from(agent_definition_versions)
                    .where(agent_definition_versions.c.id == identity.definition_id)
                )
                or 0
            ),
            "subject": int(
                await connection.scalar(
                    select(func.count())
                    .select_from(memory_subjects)
                    .where(memory_subjects.c.id == identity.subject_id)
                )
                or 0
            ),
            "entity": int(
                await connection.scalar(
                    select(func.count())
                    .select_from(memory_entities)
                    .where(memory_entities.c.id == identity.subject_id)
                )
                or 0
            ),
            "conversation": int(
                await connection.scalar(
                    select(func.count())
                    .select_from(conversations)
                    .where(conversations.c.id == identity.conversation_id)
                )
                or 0
            ),
        }


async def _cleanup(engine: AsyncEngine, identity: _PreviewIdentity) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            delete(conversations).where(conversations.c.id == identity.conversation_id)
        )
        await connection.execute(
            delete(memory_entities).where(memory_entities.c.id == identity.subject_id)
        )
        await connection.execute(
            delete(memory_subjects).where(memory_subjects.c.id == identity.subject_id)
        )
        await connection.execute(
            delete(agent_definition_versions).where(
                agent_definition_versions.c.id == identity.definition_id
            )
        )


def test_preview_session_serializes_concurrent_idempotent_creates() -> None:
    assert DATABASE_URL is not None

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        request = _request(f"preview-concurrency-{uuid4()}")
        identity = _preview_identity(request.idempotency_key)
        service = PreviewSessionService(
            database=RuntimeDatabase(engine),
            definitions=_PreparedDefinitions(),
        )
        try:
            results = await asyncio.gather(
                service.create(request),
                service.create(request),
            )

            assert sorted(result["idempotent_replay"] for result in results) == [
                False,
                True,
            ]
            assert {result["session_id"] for result in results} == {identity.session_id}
            assert await _resource_counts(engine, identity) == {
                "definition": 1,
                "subject": 1,
                "entity": 1,
                "conversation": 1,
            }
        finally:
            await _cleanup(engine, identity)
            await engine.dispose()

    asyncio.run(scenario())


def test_preview_session_rolls_back_every_resource_on_late_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert DATABASE_URL is not None

    class _FailingConversationRepository:
        def __init__(self, connection: AsyncConnection) -> None:
            self._delegate = RealConversationRepository(connection)

        async def find(self, conversation_id: str) -> dict[str, Any] | None:
            return await self._delegate.find(conversation_id)

        async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
            raise _ForcedRollback("forced after definition and subject writes")

    monkeypatch.setattr(
        preview_session_service,
        "ConversationRepository",
        _FailingConversationRepository,
    )

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        request = _request(f"preview-rollback-{uuid4()}")
        identity = _preview_identity(request.idempotency_key)
        service = PreviewSessionService(
            database=RuntimeDatabase(engine),
            definitions=_PreparedDefinitions(),
        )
        try:
            with pytest.raises(_ForcedRollback, match="forced after"):
                await service.create(request)

            assert await _resource_counts(engine, identity) == {
                "definition": 0,
                "subject": 0,
                "entity": 0,
                "conversation": 0,
            }
        finally:
            await _cleanup(engine, identity)
            await engine.dispose()

    asyncio.run(scenario())
