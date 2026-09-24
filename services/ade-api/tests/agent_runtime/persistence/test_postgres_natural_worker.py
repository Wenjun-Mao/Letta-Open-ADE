"""Fake-provider service-to-worker natural-memory failure path on real PostgreSQL."""

from __future__ import annotations

import asyncio
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import select

import ade_api.features.agent_runtime.natural_attempt_evidence as evidence_module
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
from ade_api.features.agent_runtime.persistence.memory import MemoryRepository
from ade_api.features.agent_runtime.persistence.metadata import (
    memory_revisions,
    messages,
    run_attempts,
    run_events,
    runs,
)
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.platform.settings import AdeApiSettings


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="isolated PostgreSQL natural worker database required"
)


def test_false_veto_and_success_have_distinct_authoritative_artifacts(
    tmp_path, monkeypatch, natural_worker_support
) -> None:
    assert DATABASE_URL is not None
    monkeypatch.setenv("ADE_NATURAL_MEMORY_CAPTURE", "1")
    monkeypatch.setenv("ADE_SOURCE_REVISION", "0" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "1" * 64)
    monkeypatch.setattr(evidence_module, "ARTIFACT_ROOT", tmp_path / "artifacts")

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        database = RuntimeDatabase(engine)
        settings = AdeApiSettings(
            _env_file=None,
            agent_runtime_mode="development",
            agent_runtime_enabled=True,
            database_url=DATABASE_URL,
            agent_runtime_worker_id="natural-fake-test",
        )
        catalog = natural_worker_support.catalog()
        transport = natural_worker_support.transport(catalog)
        sessions = PurposeSessionService(
            database=database,
            definitions=natural_worker_support.definitions(catalog),
            purpose="evaluation",
            session_namespace="natural-fake-test",
        )
        run_service = RunService(
            database=database,
            settings=settings,
            router_transport=transport,  # type: ignore[arg-type]
            worker_health=natural_worker_support.ready_worker(),
        )
        worker = AgentRuntimeWorker(
            engine=engine,
            settings=settings,
            transport=transport,  # type: ignore[arg-type]
        )

        async with engine.connect() as connection:
            foreign_active = list(
                (
                    await connection.execute(
                        select(runs.c.id).where(
                            runs.c.status.in_(("pending", "running"))
                        )
                    )
                ).scalars()
            )
        assert not foreign_active, (
            "natural worker integration requires an exclusively owned disposable "
            "database with no pending or running foreign work"
        )

        async def process_target(run_id: str) -> dict:
            assert await worker.process_once()
            result = await run_service.get_run(run_id)
            assert result["status"] in {"succeeded", "failed", "cancelled"}, (
                "worker did not terminally process its sole eligible run"
            )
            return result

        token = uuid4().hex[:12]
        try:
            session = await sessions.create(
                CreateAgentStudioSessionRequest(
                    idempotency_key=f"natural-fake-{token}",
                    new_definition=CreateAgentDefinitionRequest(
                        definition_key=f"natural_fake_{token}",
                        name="Natural fake test",
                        model_key="fake::conversation",
                        reviewer_model_key="fake::reviewer",
                        embedding_model_key="fake::retriever",
                        tool_names=[],
                    ),
                    new_subject=CreateMemorySubjectRequest(
                        external_key=f"natural-fake-{token}",
                        display_name="Synthetic user",
                    ),
                )
            )
            conversation_id = session["conversation"]["id"]
            subject_id = session["memory_subject"]["id"]
            accepted = await run_service.accept_turn(
                conversation_id,
                AcceptTurnRequest(
                    content="I live in Toronto.",
                    idempotency_key=f"turn-{token}",
                    timeout_seconds=30,
                    retry_count=0,
                ),
            )
            run = await process_target(accepted["run_id"])
            assert run["status"] == "failed"
            assert run["error_code"] == "runtime_validation_error"
            async with engine.connect() as connection:
                subject = await MemoryRepository(connection).get_subject(subject_id)
                facts = await MemoryRepository(connection).list_facts(subject_id)
                rows = (
                    (
                        await connection.execute(
                            select(messages.c.role).where(
                                messages.c.run_id == accepted["run_id"]
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                revision_ids = (
                    (
                        await connection.execute(
                            select(memory_revisions.c.id).where(
                                memory_revisions.c.run_id == accepted["run_id"]
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                attempts = (
                    (
                        await connection.execute(
                            select(run_attempts.c.status).where(
                                run_attempts.c.run_id == accepted["run_id"]
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                failure_details = (
                    (
                        await connection.execute(
                            select(run_events.c.payload).where(
                                run_events.c.run_id == accepted["run_id"],
                                run_events.c.event_type == "run.failed",
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
            assert subject["memory_generation"] == 1
            assert facts == []
            assert rows == ["user"]
            assert revision_ids == []
            assert attempts == ["failed"]
            assert (
                failure_details[0]["error_detail_code"]
                == "natural_memory_reply_conflict"
            )
            artifact = json.loads(
                (
                    tmp_path / "artifacts" / accepted["run_id"] / "attempt-001.json"
                ).read_text()
            )
            assert artifact["terminal_readback"]["outcome"] == "confirmed_rejection"
            assert (
                artifact["terminal_readback"]["candidate_commit"]
                == "uncommitted_undelivered"
            )
            assert artifact["candidate_visible_reply"] == "Okay, Toronto."
            assert (
                artifact["reviewer_decision"]["claim_dispositions"][0]["outcome"]
                == "contradiction"
            )
            assert artifact["reviewer_request"]["messages"][0]["role"] == "system"
            assert (
                "I live in Toronto."
                in artifact["reviewer_request"]["messages"][1]["content"]
            )
            assert artifact["reviewer_request"]["serialized_visible_token_estimate"] > 0
            assert (
                artifact["generation_requests"][0]["messages"][-1]["content"]
                == "I live in Toronto."
            )
            assert artifact["provider_request_counts"]["conversation"] == 1
            assert artifact["provider_request_counts"]["reviewer"] == 1

            transport.veto = False
            successful = await sessions.create(
                CreateAgentStudioSessionRequest(
                    idempotency_key=f"natural-success-{token}",
                    new_definition=CreateAgentDefinitionRequest(
                        definition_key=f"natural_success_{token}",
                        name="Natural success test",
                        model_key="fake::conversation",
                        reviewer_model_key="fake::reviewer",
                        embedding_model_key="fake::retriever",
                        tool_names=[],
                    ),
                    new_subject=CreateMemorySubjectRequest(
                        external_key=f"natural-success-{token}",
                        display_name="Second synthetic user",
                    ),
                )
            )
            success_subject_id = successful["memory_subject"]["id"]
            success_run = await run_service.accept_turn(
                successful["conversation"]["id"],
                AcceptTurnRequest(
                    content="I live in Toronto.",
                    idempotency_key=f"success-turn-{token}",
                    timeout_seconds=30,
                    retry_count=0,
                ),
            )
            assert (await process_target(success_run["run_id"]))[
                "status"
            ] == "succeeded"
            async with engine.connect() as connection:
                success_subject = await MemoryRepository(connection).get_subject(
                    success_subject_id
                )
                success_facts = await MemoryRepository(connection).list_facts(
                    success_subject_id
                )
            assert success_subject["memory_generation"] == 2
            assert len(success_facts) == 1
            assert success_facts[0]["value"] == "Toronto"
            success_artifact = json.loads(
                (
                    tmp_path / "artifacts" / success_run["run_id"] / "attempt-001.json"
                ).read_text()
            )
            assert success_artifact["terminal_readback"]["outcome"] == "committed"
            assert (
                success_artifact["terminal_readback"]["candidate_commit"]
                == "committed_visible_message"
            )
            assert success_artifact["embedding_stage"] == {"count": 1, "dimensions": 3}
            assert success_artifact["provider_request_counts"]["memory_embeddings"] == 1

            transport.fail_after_review = True
            transport.reviewed = False
            failed_embedding = await sessions.create(
                CreateAgentStudioSessionRequest(
                    idempotency_key=f"natural-embedding-{token}",
                    new_definition=CreateAgentDefinitionRequest(
                        definition_key=f"natural_embedding_{token}",
                        name="Natural embedding failure test",
                        model_key="fake::conversation",
                        reviewer_model_key="fake::reviewer",
                        embedding_model_key="fake::retriever",
                        tool_names=[],
                    ),
                    new_subject=CreateMemorySubjectRequest(
                        external_key=f"natural-embedding-{token}",
                        display_name="Third synthetic user",
                    ),
                )
            )
            embedding_subject_id = failed_embedding["memory_subject"]["id"]
            embedding_run = await run_service.accept_turn(
                failed_embedding["conversation"]["id"],
                AcceptTurnRequest(
                    content="I live in Toronto.",
                    idempotency_key=f"embedding-turn-{token}",
                    timeout_seconds=30,
                    retry_count=0,
                ),
            )
            assert (await process_target(embedding_run["run_id"]))["status"] == "failed"
            async with engine.connect() as connection:
                embedding_subject = await MemoryRepository(connection).get_subject(
                    embedding_subject_id
                )
                embedding_facts = await MemoryRepository(connection).list_facts(
                    embedding_subject_id
                )
                embedding_assistant_ids = list(
                    (
                        await connection.execute(
                            select(messages.c.id).where(
                                messages.c.run_id == embedding_run["run_id"],
                                messages.c.role == "assistant",
                            )
                        )
                    ).scalars()
                )
            assert embedding_subject["memory_generation"] == 1
            assert embedding_facts == []
            assert embedding_assistant_ids == []
            embedding_artifact = json.loads(
                (
                    tmp_path
                    / "artifacts"
                    / embedding_run["run_id"]
                    / "attempt-001.json"
                ).read_text()
            )
            assert embedding_artifact["terminal_readback"]["outcome"] == (
                "confirmed_rejection"
            )
            assert (
                embedding_artifact["reviewer_decision"]["claim_dispositions"][0][
                    "outcome"
                ]
                == "allow"
            )
            assert embedding_artifact["embedding_stage"] == {"stage": "absent"}
            assert (
                embedding_artifact["provider_request_counts"]["memory_embeddings"] == 1
            )
        finally:
            await engine.dispose()

    asyncio.run(scenario())
