"""Observation failures cannot alter worker outcomes or provider dispatches."""

import asyncio
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import text

import ade_api.features.agent_runtime.natural_attempt_evidence as evidence_module
import ade_api.features.agent_runtime.persistence.evaluation_observations as observations
from ade_api.features.agent_runtime.agent_studio_sessions import PurposeSessionService
from ade_api.features.agent_runtime.contracts import (
    AcceptTurnRequest,
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
)
from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.platform.settings import AdeApiSettings
from .story_continuity_support import require_owned_database

DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="fresh disposable PostgreSQL required"
)


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "before_sql",
        "after_sql",
        "row_limit",
        "byte_limit",
        "artifact_limit",
        "disabled",
    ],
)
def test_optional_observation_failure_preserves_success(
    tmp_path, monkeypatch, natural_worker_support, fault
):
    assert DATABASE_URL
    require_owned_database(DATABASE_URL)
    monkeypatch.setenv("ADE_SOURCE_REVISION", "0" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "1" * 64)
    monkeypatch.setenv(
        "ADE_NATURAL_MEMORY_CAPTURE", "0" if fault == "disabled" else "1"
    )
    monkeypatch.setattr(evidence_module, "ARTIFACT_ROOT", tmp_path / "captures")
    calls = []
    original = observations.read_snapshot

    async def observed(connection, *, binding):
        calls.append(binding)
        if (fault == "before_sql" and len(calls) == 1) or (
            fault == "after_sql" and len(calls) == 2
        ):
            await connection.execute(text("SELECT nonexistent_pc11_observation_column"))
        return await original(connection, binding=binding)

    monkeypatch.setattr(observations, "read_snapshot", observed)
    if fault == "row_limit":
        monkeypatch.setattr(observations, "MAX_ROWS", 0)
    if fault == "byte_limit":
        monkeypatch.setattr(observations, "MAX_SNAPSHOT_BYTES", 1)
    if fault == "artifact_limit":
        monkeypatch.setattr(evidence_module, "_MAX_ARTIFACT_BYTES", 1)

    async def scenario():
        engine = create_persistence_engine(DATABASE_URL)
        database = RuntimeDatabase(engine)
        catalog = natural_worker_support.catalog()
        transport = natural_worker_support.transport(catalog)
        transport.veto = False
        settings = AdeApiSettings(
            _env_file=None,
            database_url=DATABASE_URL,
            agent_runtime_enabled=True,
            agent_runtime_mode="development",
        )
        sessions = PurposeSessionService(
            database=database,
            definitions=natural_worker_support.definitions(catalog),
            purpose="evaluation",
            session_namespace="observation-worker",
        )
        service = RunService(
            database=database,
            settings=settings,
            router_transport=transport,
            worker_health=natural_worker_support.ready_worker(),
        )
        worker = AgentRuntimeWorker(
            engine=engine, settings=settings, transport=transport
        )
        token = uuid4().hex
        try:
            session = await sessions.create(
                CreateAgentStudioSessionRequest(
                    idempotency_key=token,
                    new_definition=CreateAgentDefinitionRequest(
                        definition_key=f"observation_{token}",
                        name="Observation fault check",
                        model_key="fake::conversation",
                        reviewer_model_key="fake::reviewer",
                        embedding_model_key="fake::retriever",
                        tool_names=[],
                    ),
                    new_subject=CreateMemorySubjectRequest(external_key=token),
                )
            )
            accepted = await service.accept_turn(
                session["conversation"]["id"],
                AcceptTurnRequest(
                    content="I live in Toronto.",
                    idempotency_key=token,
                    retry_count=0,
                    timeout_seconds=30,
                ),
            )
            transport.calls.clear()
            assert await worker.process_once()
            run = await service.get_run(accepted["run_id"])
            assert run["status"] == "succeeded"
            # Identical dispatches in every fault/disabled arm, no provider fallback.
            assert transport.calls == [
                ("catalog", ""),
                ("embeddings", "fake::retriever"),
                ("chat", "fake::conversation"),
                ("chat", "fake::reviewer"),
                ("embeddings", "fake::retriever"),
            ]
            path = tmp_path / "captures" / accepted["run_id"] / "attempt-001.json"
            if fault == "disabled":
                assert calls == []
                assert not path.exists()
                return
            assert len(calls) == 2
            if fault == "artifact_limit":
                assert not path.exists()
                return
            artifact = json.loads(path.read_bytes())
            assert artifact["schema_version"] == 1
            assert artifact["terminal_readback"]["outcome"] == "committed"
            observation = artifact["private_observations"]
            before_status = (
                "unavailable"
                if fault == "before_sql"
                else "truncated"
                if fault in {"row_limit", "byte_limit"}
                else "complete"
            )
            after_status = (
                "unavailable"
                if fault == "after_sql"
                else "truncated"
                if fault in {"row_limit", "byte_limit"}
                else "complete"
            )
            assert observation["before"]["status"] == before_status
            assert observation["after"]["status"] == after_status
            if fault == "none":
                assert observation["before"]["state"]["generation"] == 1
                assert observation["after"]["state"]["generation"] == 2
                assert len(observation["after"]["state"]["sources"]) == 1
                assert (
                    observation["after"]["state"]["sources"][0]["authority_role"]
                    == "user_assertion"
                )
                assert observation["history"]["status"] == "unavailable"
            else:
                assert observation["isolation"] == "unavailable"
            assert "nonexistent_pc11" not in path.read_text()
        finally:
            await engine.dispose()

    asyncio.run(scenario())
