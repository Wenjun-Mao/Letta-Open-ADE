"""Current fresh-workspace session lifecycle; SQL-only erasure stays retired."""

import asyncio
from contextlib import asynccontextmanager

import pytest

from ade_api.features.agent_runtime import agent_studio_sessions as sessions
from ade_api.features.agent_runtime.agent_studio_sessions import PurposeSessionService
from ade_api.features.agent_runtime.contracts import (
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
    CreateEvaluationSessionRequest,
)
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.evaluation_sessions import EvaluationSessionService


class ControlledDatabase:
    workspace_id = "00000000-0000-0000-0000-000000000099"

    @property
    def engine(self):
        return self

    async def ensure_ready(self):
        pass

    @asynccontextmanager
    async def connect(self):
        yield object()

    @asynccontextmanager
    async def translated_errors(self):
        yield


def test_evaluation_session_translates_flat_creation_contract_to_atomic_plan():
    service = EvaluationSessionService(
        database=ControlledDatabase(), definitions=None, resources=None
    )
    captured = {}

    async def create(request):
        captured["request"] = request
        return {"conversation": {"purpose": "evaluation"}}

    service.sessions.create = create
    result = asyncio.run(
        service.create(
            CreateEvaluationSessionRequest(
                idempotency_key="evaluation-plan-1",
                title="Weather fixture",
                model_key="source::conversation",
                compaction_model_key="source::compaction",
                tool_names=["search_memory", "get_weather"],
                subject_external_key="fixture:subject-1",
            )
        )
    )
    request = captured["request"]
    assert result["conversation"]["purpose"] == "evaluation"
    assert request.new_definition.definition_key.startswith("evaluation_")
    assert request.new_definition.tool_names == ["search_memory", "get_weather"]
    assert request.new_definition.compaction_model_key == "source::compaction"
    assert request.new_subject.external_key == "fixture:subject-1"


def test_evaluation_session_binds_existing_cross_fixture_resources():
    service = EvaluationSessionService(
        database=ControlledDatabase(), definitions=None, resources=None
    )
    captured = {}

    async def create(request):
        captured["request"] = request
        return {}

    service.sessions.create = create
    asyncio.run(
        service.create(
            CreateEvaluationSessionRequest(
                idempotency_key="evaluation-plan-2",
                agent_definition_id="definition-version-1",
                memory_subject_id="subject-1",
            )
        )
    )
    request = captured["request"]
    assert request.agent_definition_id == "definition-version-1"
    assert request.new_definition is None
    assert request.memory_subject_id == "subject-1"
    assert request.new_subject is None


def test_agent_studio_rejects_evaluation_only_tools_before_provisioning(monkeypatch):
    service = PurposeSessionService(database=ControlledDatabase(), definitions=None)

    async def absent(*args, **kwargs):
        return None

    monkeypatch.setattr(sessions, "load_existing", absent)
    request = CreateAgentStudioSessionRequest(
        idempotency_key="wrong-purpose-tools",
        new_definition=CreateAgentDefinitionRequest(
            definition_key="weather_fixture",
            name="Weather fixture",
            model_key="source::conversation",
            compaction_model_key="source::compaction",
            tool_names=["get_weather"],
        ),
        new_subject=CreateMemorySubjectRequest(external_key="subject-1"),
    )
    with pytest.raises(RuntimeValidationError, match="not available for agent_studio"):
        asyncio.run(service.create(request))


def test_existing_definition_session_replays_through_current_lifecycle(monkeypatch):
    service = PurposeSessionService(database=ControlledDatabase(), definitions=None)
    request = CreateAgentStudioSessionRequest(
        idempotency_key="existing-definition-session",
        agent_definition_id="definition-version-1",
        new_subject=CreateMemorySubjectRequest(external_key="subject-1"),
    )
    existing = (
        {"id": "definition-version-1"},
        {
            "id": "subject-1",
            "external_key": "subject-1",
            "display_name": request.new_subject.display_name,
        },
        {"id": "conversation-1", "title": request.title, "purpose": "agent_studio"},
    )

    async def read_existing(connection, identity, **kwargs):
        assert kwargs["database"].workspace_id == ControlledDatabase.workspace_id
        return existing

    async def response(connection, session_id, resources, *, replayed):
        assert resources is existing
        return {"idempotent_replay": replayed}

    monkeypatch.setattr(sessions, "load_existing", read_existing)
    monkeypatch.setattr(sessions, "session_response", response)
    assert asyncio.run(service.create(request)) == {"idempotent_replay": True}


def test_evaluation_state_does_not_synchronously_read_native_memory():
    class Resources:
        async def get_conversation_state(self, conversation_id, **kwargs):
            assert kwargs["required_purpose"] == "evaluation"
            return {"id": conversation_id, "messages": []}

    service = EvaluationSessionService(
        database=ControlledDatabase(), definitions=None, resources=Resources()
    )

    async def get(conversation_id):
        return {"memory_subject": {"id": "subject-1"}, "latest_run": None}

    service.sessions.get = get
    result = asyncio.run(
        service.get_state("conversation-1", message_limit=200, before_sequence=None)
    )
    assert result["conversation"]["messages"] == []
    assert "memories" not in result
    assert not hasattr(service, "purge")
