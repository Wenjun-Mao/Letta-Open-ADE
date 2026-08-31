from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest

from ade_api.features.agent_runtime_v3 import preview_session_service
from ade_api.features.agent_runtime_v3.contracts import CreatePreviewSessionRequest
from ade_api.features.agent_runtime_v3.database_boundary import DEFAULT_WORKSPACE_ID
from ade_api.features.agent_runtime_v3.errors import IdempotencyConflict
from ade_api.features.agent_runtime_v3.preview_session_service import (
    PreviewSessionService,
)


NOW = datetime(2026, 8, 30, tzinfo=UTC)


class _State:
    in_transaction = False
    definition: dict[str, Any] | None = None
    subject: dict[str, Any] | None = None
    conversation: dict[str, Any] | None = None


class _Connection:
    async def execute(self, _statement: Any) -> None:
        return None


class _ConnectionContext:
    def __init__(self, state: _State, *, transaction: bool) -> None:
        self.state = state
        self.transaction = transaction

    async def __aenter__(self) -> _Connection:
        self.state.in_transaction = self.transaction
        return _Connection()

    async def __aexit__(self, *_: object) -> None:
        self.state.in_transaction = False


class _Engine:
    def __init__(self, state: _State) -> None:
        self.state = state

    def connect(self) -> _ConnectionContext:
        return _ConnectionContext(self.state, transaction=False)

    def begin(self) -> _ConnectionContext:
        return _ConnectionContext(self.state, transaction=True)


class _Database:
    def __init__(self, state: _State) -> None:
        self.state = state
        self.engine = _Engine(state)

    async def ensure_ready(self) -> None:
        return None

    async def ensure_workspace(self, _connection: object) -> None:
        assert self.state.in_transaction

    @asynccontextmanager
    async def translated_errors(self):
        yield


class _Definitions:
    prepare_calls = 0

    async def prepare(self, request: object) -> dict[str, Any]:
        self.prepare_calls += 1
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


def _repositories(monkeypatch: pytest.MonkeyPatch, state: _State) -> None:
    class Definitions:
        def __init__(self, _connection: object) -> None:
            pass

        async def find(self, _resource_id: str):
            return state.definition

        async def create_next(self, workspace_id: str, payload: dict[str, Any]):
            assert state.in_transaction
            state.definition = {
                **payload,
                "workspace_id": workspace_id,
                "version": 1,
                "created_at": NOW,
            }
            return state.definition

    class Memories:
        def __init__(self, _connection: object) -> None:
            pass

        async def find_subject(self, _resource_id: str):
            return state.subject

        async def create_subject(self, payload: dict[str, Any]):
            assert state.in_transaction
            state.subject = {**payload, "created_at": NOW}
            return state.subject

        async def create_entity(self, payload: dict[str, Any]):
            assert state.in_transaction
            return {**payload, "created_at": NOW}

    class Conversations:
        def __init__(self, _connection: object) -> None:
            pass

        async def find(self, _resource_id: str):
            return state.conversation

        async def create(self, payload: dict[str, Any]):
            assert state.in_transaction
            state.conversation = {**payload, "version": 1, "created_at": NOW}
            return state.conversation

    monkeypatch.setattr(
        preview_session_service, "DefinitionVersionRepository", Definitions
    )
    monkeypatch.setattr(preview_session_service, "MemoryRepository", Memories)
    monkeypatch.setattr(
        preview_session_service, "ConversationRepository", Conversations
    )


def _request(*, name: str = "Preview") -> CreatePreviewSessionRequest:
    return CreatePreviewSessionRequest(
        idempotency_key="stable-session-key",
        name=name,
        subject_display_name="Zhang Wei",
        model_key="dgx_vllm::qwen",
        reviewer_model_key="dgx_vllm::qwen",
        embedding_model_key="dgx_embedding::qwen",
    )


def test_preview_session_creates_all_resources_atomically_and_replays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _State()
    _repositories(monkeypatch, state)
    definitions = _Definitions()
    service = PreviewSessionService(
        database=_Database(state),
        definitions=definitions,
    )

    created = asyncio.run(service.create(_request()))
    replayed = asyncio.run(service.create(_request()))

    assert created["idempotent_replay"] is False
    assert replayed["idempotent_replay"] is True
    assert replayed["session_id"] == created["session_id"]
    assert definitions.prepare_calls == 1
    assert created["agent_definition"]["tool_names"] == ["search_memory"]
    assert (
        created["memory_subject"]["id"] == created["conversation"]["memory_subject_id"]
    )
    assert state.definition is not None
    assert state.definition["workspace_id"] == DEFAULT_WORKSPACE_ID


def test_preview_session_rejects_reused_key_for_changed_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _State()
    _repositories(monkeypatch, state)
    definitions = _Definitions()
    service = PreviewSessionService(
        database=_Database(state),
        definitions=definitions,
    )
    asyncio.run(service.create(_request()))

    with pytest.raises(IdempotencyConflict, match="different definition"):
        asyncio.run(service.create(_request(name="Changed")))

    assert definitions.prepare_calls == 1
