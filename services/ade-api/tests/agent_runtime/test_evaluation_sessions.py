from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import pytest

from ade_api.features.agent_runtime.agent_studio_sessions import (
    AgentStudioSessionService,
)
from ade_api.features.agent_runtime.contracts import (
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
    CreateEvaluationSessionRequest,
)
from ade_api.features.agent_runtime.errors import (
    RuntimeConflict,
    RuntimeValidationError,
)
import ade_api.features.agent_runtime.evaluation_sessions as evaluation_sessions
from ade_api.features.agent_runtime.evaluation_sessions import (
    EvaluationSessionService,
)


def test_evaluation_session_translates_flat_creation_contract_to_atomic_plan() -> None:
    service = EvaluationSessionService(database=None, definitions=None, resources=None)  # type: ignore[arg-type]
    captured = {}

    async def create(request):
        captured["request"] = request
        return {"conversation": {"purpose": "evaluation"}}

    service.sessions.create = create  # type: ignore[method-assign]
    result = asyncio.run(
        service.create(
            CreateEvaluationSessionRequest(
                idempotency_key="evaluation-plan-1",
                title="Weather fixture",
                model_key="source::conversation",
                reviewer_model_key="source::reviewer",
                embedding_model_key="source::embedding",
                tool_names=["search_memory", "get_weather"],
                subject_external_key="fixture:subject-1",
            )
        )
    )

    request = captured["request"]
    assert result["conversation"]["purpose"] == "evaluation"
    assert request.new_definition is not None
    assert request.new_definition.definition_key.startswith("evaluation_")
    assert request.new_definition.tool_names == ["search_memory", "get_weather"]
    assert request.new_subject is not None
    assert request.new_subject.external_key == "fixture:subject-1"


def test_evaluation_session_binds_existing_cross_fixture_resources() -> None:
    service = EvaluationSessionService(database=None, definitions=None, resources=None)  # type: ignore[arg-type]
    captured = {}

    async def create(request):
        captured["request"] = request
        return {}

    service.sessions.create = create  # type: ignore[method-assign]
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


def test_agent_studio_rejects_evaluation_only_tools() -> None:
    service = AgentStudioSessionService(database=None, definitions=None)  # type: ignore[arg-type]
    definition = CreateAgentDefinitionRequest(
        definition_key="weather_fixture",
        name="Weather fixture",
        model_key="source::conversation",
        reviewer_model_key="source::reviewer",
        embedding_model_key="source::embedding",
        tool_names=["get_weather"],
    )

    with pytest.raises(RuntimeValidationError, match="not available for agent_studio"):
        asyncio.run(service.create_definition(definition))


def test_existing_definition_session_creation_reaches_the_lifecycle_path() -> None:
    class _ReadyDatabase:
        async def ensure_ready(self) -> None:
            return None

    service = AgentStudioSessionService(
        database=_ReadyDatabase(),  # type: ignore[arg-type]
        definitions=None,  # type: ignore[arg-type]
    )
    request = CreateAgentStudioSessionRequest(
        idempotency_key="existing-definition-session",
        agent_definition_id="definition-version-1",
        new_subject=CreateMemorySubjectRequest(external_key="subject-1"),
    )
    existing = ({"id": "definition"}, {"id": "subject"}, {"id": "conversation"})

    async def read_existing(_identity, _request):
        return existing

    async def response(_session_id, resources, *, replayed):
        assert resources is existing
        return {"idempotent_replay": replayed}

    service._read_existing = read_existing  # type: ignore[method-assign]
    service._response = response  # type: ignore[method-assign]

    result = asyncio.run(service.create(request))

    assert result == {"idempotent_replay": True}


class _PurgeDatabase:
    class _Engine:
        @asynccontextmanager
        async def begin(self):
            yield object()

    engine = _Engine()

    async def ensure_ready(self) -> None:
        return None

    @asynccontextmanager
    async def translated_errors(self):
        yield


def test_evaluation_purge_is_idempotent_when_the_session_is_gone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ConversationRepository:
        def __init__(self, _connection):
            pass

        async def find(self, _conversation_id):
            return None

    monkeypatch.setattr(
        evaluation_sessions, "ConversationRepository", _ConversationRepository
    )
    service = EvaluationSessionService(
        database=_PurgeDatabase(),
        definitions=None,
        resources=None,  # type: ignore[arg-type]
    )

    result = asyncio.run(service.purge("evaluation-conversation-1"))

    assert result == {
        "conversation_id": "evaluation-conversation-1",
        "already_purged": True,
        "deleted_counts": {},
    }


def test_evaluation_purge_rejects_an_active_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation = {"id": "evaluation-conversation-1", "purpose": "evaluation"}

    class _ConversationRepository:
        def __init__(self, _connection):
            pass

        async def find(self, _conversation_id):
            return conversation

        async def get_for_update(self, _conversation_id):
            return conversation

    class _RunRepository:
        def __init__(self, _connection):
            pass

        async def active_for_conversation(self, _conversation_id):
            return {"id": "active-run"}

    monkeypatch.setattr(
        evaluation_sessions, "ConversationRepository", _ConversationRepository
    )
    monkeypatch.setattr(evaluation_sessions, "RunRepository", _RunRepository)
    service = EvaluationSessionService(
        database=_PurgeDatabase(),
        definitions=None,
        resources=None,  # type: ignore[arg-type]
    )

    with pytest.raises(RuntimeConflict, match="active run"):
        asyncio.run(service.purge("evaluation-conversation-1"))


def test_evaluation_purge_removes_run_owned_provenance_before_its_parents() -> None:
    class _Result:
        rowcount = 0

    class _Connection:
        def __init__(self) -> None:
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return _Result()

    connection = _Connection()

    asyncio.run(
        evaluation_sessions._delete_conversation_graph(
            connection, "evaluation-conversation-1"
        )
    )

    deleted_tables = [
        statement.table.name
        for statement in connection.statements
        if getattr(statement, "is_delete", False)
    ]
    assert deleted_tables.index("memory_revision_sources") < deleted_tables.index(
        "messages"
    )
    assert deleted_tables.index("memory_revision_predecessors") < deleted_tables.index(
        "memory_revisions"
    )
    assert deleted_tables.index("memory_embeddings") < deleted_tables.index(
        "memory_revisions"
    )
    assert deleted_tables.index("memory_revisions") < deleted_tables.index("runs")
    provenance_delete = next(
        statement
        for statement in connection.statements
        if getattr(statement, "is_delete", False)
        and statement.table.name == "memory_revision_sources"
    )
    assert "memory_revision_sources.message_id" in str(provenance_delete)
    assert "memory_revision_sources.revision_id" in str(provenance_delete)
    fact_pointer_update = next(
        statement
        for statement in connection.statements
        if getattr(statement, "is_update", False)
        and statement.table.name == "memory_facts"
    )
    assert connection.statements.index(fact_pointer_update) < next(
        index
        for index, statement in enumerate(connection.statements)
        if getattr(statement, "is_delete", False)
        and statement.table.name == "memory_revisions"
    )
