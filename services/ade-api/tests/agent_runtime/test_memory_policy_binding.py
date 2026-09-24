"""Fresh sends use the current binding; historical replay is unchanged."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from ade_api.features.agent_runtime.contracts import AcceptTurnRequest
from ade_api.features.agent_runtime.database_boundary import DEFAULT_WORKSPACE_ID
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.memory_policy_binding import (
    TYPED_MEMORY_POLICY_VERSION,
    require_executable_memory_policy,
)
from ade_api.features.agent_runtime.run_service import RunService, _turn_request_hash
from ade_api.features.agent_runtime.turn_execution import TurnExecution
import ade_api.features.agent_runtime.run_service as run_service_module


def test_only_current_typed_and_registered_natural_bindings_execute() -> None:
    require_executable_memory_policy(TYPED_MEMORY_POLICY_VERSION)
    require_executable_memory_policy("natural-user-assertions-v4-b")
    for binding in ("typed-user-facts-v1", "natural-user-assertions-v3-b", "unknown"):
        with pytest.raises(RuntimeValidationError) as error:
            require_executable_memory_policy(binding)
        assert error.value.detail_code == "obsolete_memory_policy_binding"


@pytest.mark.parametrize(
    "binding", ["typed-user-facts-v1", "natural-user-assertions-v3-b"]
)
@pytest.mark.parametrize("replay", [False, True])
def test_admission_rejects_old_binding_after_historical_replay_check(
    monkeypatch: pytest.MonkeyPatch, replay: bool, binding: str
) -> None:
    request = AcceptTurnRequest(content="hello", idempotency_key="turn-1")
    conversation = {
        "id": "conversation-1",
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "memory_subject_id": "subject-1",
        "agent_definition_version_id": "definition-1",
        "version": 2,
        "purpose": "development",
    }
    definition = {
        "id": "definition-1",
        "version": 1,
        "memory_policy_version": binding,
        "deployment_snapshot": [],
        "tool_names": [],
    }
    prior = (
        {
            "id": "run-1",
            "status": "succeeded",
            "accepted_conversation_version": 1,
            "accepted_runtime_mode": "development",
            "request_hash": _turn_request_hash(
                request, {**conversation, "version": 1}, definition
            ),
        }
        if replay
        else None
    )

    class Database:
        @property
        def engine(self):
            return self

        async def ensure_ready(self):
            return None

        @asynccontextmanager
        async def translated_errors(self):
            yield

        @asynccontextmanager
        async def connect(self):
            yield object()

    class Conversations:
        def __init__(self, _connection):
            pass

        async def get(self, _conversation_id):
            return conversation

    class Runs:
        def __init__(self, _connection):
            pass

        async def get_by_idempotency(self, _conversation_id, _key):
            return prior

    class Memory:
        def __init__(self, _connection):
            pass

        async def get_subject(self, _subject_id):
            return {"workspace_id": DEFAULT_WORKSPACE_ID}

    class Definitions:
        def __init__(self, _connection):
            pass

        async def get(self, _definition_id):
            return definition

    class Transport:
        async def catalog(self, **_kwargs):
            raise AssertionError("obsolete binding must not reach provider dispatch")

    monkeypatch.setattr(run_service_module, "ConversationRepository", Conversations)
    monkeypatch.setattr(run_service_module, "RunRepository", Runs)
    monkeypatch.setattr(run_service_module, "MemoryRepository", Memory)
    monkeypatch.setattr(run_service_module, "DefinitionVersionRepository", Definitions)
    service = RunService(
        database=Database(),
        settings=SimpleNamespace(agent_runtime_mode="development"),
        router_transport=Transport(),
        worker_health=object(),
    )
    if replay:
        result = asyncio.run(service.accept_turn("conversation-1", request))
        assert result["run_id"] == "run-1"
        assert result["idempotent_replay"] is True
    else:
        with pytest.raises(RuntimeValidationError) as error:
            asyncio.run(service.accept_turn("conversation-1", request))
        assert error.value.detail_code == "obsolete_memory_policy_binding"


@pytest.mark.parametrize(
    "binding", ["typed-user-facts-v1", "natural-user-assertions-v3-b"]
)
def test_worker_rejects_old_binding_before_provider_dispatch(
    monkeypatch: pytest.MonkeyPatch, binding: str
) -> None:
    execution = TurnExecution(
        engine=None,
        transport=None,
        settings=SimpleNamespace(agent_runtime_mode="development"),
    )

    async def load_state(_run):
        return {
            "definition": {"memory_policy_version": binding},
            "conversation": {"purpose": "development"},
        }

    monkeypatch.setattr(execution, "_load_state", load_state)
    with pytest.raises(RuntimeValidationError) as error:
        asyncio.run(execution.execute({"id": "run-1"}, deadline=999, trace=object()))
    assert error.value.detail_code == "obsolete_memory_policy_binding"
