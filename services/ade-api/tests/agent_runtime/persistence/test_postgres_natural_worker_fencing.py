"""Cancellation and lease loss fence a generated natural-memory candidate."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, update

import ade_api.features.agent_runtime.natural_attempt_evidence as evidence_module
import ade_api.features.agent_runtime.worker as worker_module
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
    conversation_leases,
    memory_revisions,
    messages,
    runs,
)
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.platform.settings import AdeApiSettings


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="exclusively owned disposable PostgreSQL database required"
)


@pytest.mark.parametrize("fault", ["cancel", "lease_lost"])
def test_natural_candidate_cannot_commit_after_ownership_is_lost(
    fault, tmp_path, monkeypatch, natural_worker_support
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
            agent_runtime_worker_id=f"natural-fence-{fault}",
        )
        catalog = natural_worker_support.catalog()
        transport_base = natural_worker_support.transport

        class HeldReviewerTransport(transport_base):
            def __init__(self) -> None:
                super().__init__(catalog)
                self.veto = False
                self.entered = asyncio.Event()
                self.release = asyncio.Event()

            async def chat_completion(self, payload, *, timeout_seconds):
                if payload["model"] == "fake::reviewer":
                    self.entered.set()
                    await self.release.wait()
                return await super().chat_completion(
                    payload, timeout_seconds=timeout_seconds
                )

        transport = HeldReviewerTransport()
        sessions = PurposeSessionService(
            database=database,
            definitions=natural_worker_support.definitions(catalog),
            purpose="evaluation",
            session_namespace=f"natural-fence-{fault}",
        )
        run_service = RunService(
            database=database,
            settings=settings,
            router_transport=transport,
            worker_health=natural_worker_support.ready_worker(),
        )
        worker = AgentRuntimeWorker(
            engine=engine, settings=settings, transport=transport
        )
        token = uuid4().hex[:12]
        try:
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
            assert not foreign_active, "fencing test requires an idle owned database"
            session = await sessions.create(
                CreateAgentStudioSessionRequest(
                    idempotency_key=f"natural-fence-{token}",
                    new_definition=CreateAgentDefinitionRequest(
                        definition_key=f"natural_fence_{token}",
                        name="Natural fencing test",
                        model_key="fake::conversation",
                        reviewer_model_key="fake::reviewer",
                        embedding_model_key="fake::retriever",
                        tool_names=[],
                    ),
                    new_subject=CreateMemorySubjectRequest(
                        external_key=f"natural-fence-{token}",
                        display_name="Synthetic user",
                    ),
                )
            )
            subject_id = session["memory_subject"]["id"]
            accepted = await run_service.accept_turn(
                session["conversation"]["id"],
                AcceptTurnRequest(
                    content="I live in Toronto.",
                    idempotency_key=f"turn-{token}",
                    timeout_seconds=30,
                    retry_count=0,
                ),
            )
            run_id = accepted["run_id"]
            task = asyncio.create_task(worker.process_once())
            async with asyncio.timeout(5):
                await transport.entered.wait()
            if fault == "cancel":
                requested = await run_service.cancel_run(run_id)
                assert requested["status"] == "running"
            else:
                async with engine.begin() as connection:
                    result = await connection.execute(
                        update(conversation_leases)
                        .where(conversation_leases.c.run_id == run_id)
                        .values(
                            lease_token=str(uuid4()),
                            expires_at=datetime.now(UTC) - timedelta(seconds=1),
                        )
                    )
                    assert result.rowcount == 1
            transport.release.set()
            async with asyncio.timeout(5):
                assert await task

            observed = await run_service.get_run(run_id)
            if fault == "lease_lost":
                assert observed["status"] == "running"
                # Recover the original run after its lease expires. Its single
                # attempt budget is exhausted; no fresh key or model call occurs.
                assert await worker.process_once()
                observed = await run_service.get_run(run_id)
                assert observed["error_code"] == "worker_lease_expired"
            else:
                assert observed["status"] == "cancelled"
            assert observed["status"] in {"cancelled", "failed"}
            async with engine.connect() as connection:
                subject = await MemoryRepository(connection).get_subject(subject_id)
                facts = await MemoryRepository(connection).list_facts(subject_id)
                assistant_ids = list(
                    (
                        await connection.execute(
                            select(messages.c.id).where(
                                messages.c.run_id == run_id,
                                messages.c.role == "assistant",
                            )
                        )
                    ).scalars()
                )
                revision_ids = list(
                    (
                        await connection.execute(
                            select(memory_revisions.c.id).where(
                                memory_revisions.c.run_id == run_id
                            )
                        )
                    ).scalars()
                )
            assert subject["memory_generation"] == 1
            assert facts == assistant_ids == revision_ids == []
            artifact = json.loads(
                (tmp_path / "artifacts" / run_id / "attempt-001.json").read_text()
            )
            assert artifact["candidate_visible_reply"] == "Okay, Toronto."
            assert artifact["terminal_readback"]["assistant_message_ids"] == []
            assert artifact["terminal_readback"]["revision_ids"] == []
            assert artifact["terminal_readback"]["outcome"] == (
                "confirmed_rejection" if fault == "cancel" else "unconfirmed"
            )
            assert transport.calls.count(("chat", "fake::conversation")) == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.parametrize("fault", ["before_commit", "after_commit", "artifact"])
def test_natural_commit_faults_use_authoritative_readback(
    fault, tmp_path, monkeypatch, natural_worker_support
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
            agent_runtime_worker_id=f"natural-commit-{fault}",
        )
        catalog = natural_worker_support.catalog()
        transport = natural_worker_support.transport(catalog)
        transport.veto = False
        sessions = PurposeSessionService(
            database=database,
            definitions=natural_worker_support.definitions(catalog),
            purpose="evaluation",
            session_namespace=f"natural-commit-{fault}",
        )
        run_service = RunService(
            database=database,
            settings=settings,
            router_transport=transport,
            worker_health=natural_worker_support.ready_worker(),
        )
        worker = AgentRuntimeWorker(
            engine=engine, settings=settings, transport=transport
        )
        token = uuid4().hex[:12]
        try:
            async with engine.connect() as connection:
                active = list(
                    (
                        await connection.execute(
                            select(runs.c.id).where(
                                runs.c.status.in_(("pending", "running"))
                            )
                        )
                    ).scalars()
                )
            assert not active, "commit fault test requires an idle owned database"
            session = await sessions.create(
                CreateAgentStudioSessionRequest(
                    idempotency_key=f"natural-commit-{token}",
                    new_definition=CreateAgentDefinitionRequest(
                        definition_key=f"natural_commit_{token}",
                        name="Natural commit fault test",
                        model_key="fake::conversation",
                        reviewer_model_key="fake::reviewer",
                        embedding_model_key="fake::retriever",
                        tool_names=[],
                    ),
                    new_subject=CreateMemorySubjectRequest(
                        external_key=f"natural-commit-{token}",
                        display_name="Synthetic user",
                    ),
                )
            )
            subject_id = session["memory_subject"]["id"]
            accepted = await run_service.accept_turn(
                session["conversation"]["id"],
                AcceptTurnRequest(
                    content="I live in Toronto.",
                    idempotency_key=f"turn-{token}",
                    timeout_seconds=30,
                    retry_count=0,
                ),
            )
            run_id = accepted["run_id"]
            original = worker.finalizer.commit_success

            async def faulty_commit(claim, attempt_id, result):
                if fault == "before_commit":
                    raise ConnectionError("synthetic pre-commit fault")
                await original(claim, attempt_id, result)
                if fault == "after_commit":
                    raise ConnectionError("synthetic lost commit acknowledgment")

            if fault != "artifact":
                monkeypatch.setattr(worker.finalizer, "commit_success", faulty_commit)
            else:

                async def fail_retention(_engine, _evidence):
                    raise OSError("synthetic artifact retention fault")

                monkeypatch.setattr(
                    worker_module, "retain_attempt_evidence", fail_retention
                )
            assert await worker.process_once()
            run = await run_service.get_run(run_id)
            async with engine.connect() as connection:
                subject = await MemoryRepository(connection).get_subject(subject_id)
                facts = await MemoryRepository(connection).list_facts(subject_id)
                assistant_ids = list(
                    (
                        await connection.execute(
                            select(messages.c.id).where(
                                messages.c.run_id == run_id,
                                messages.c.role == "assistant",
                            )
                        )
                    ).scalars()
                )
            committed = fault != "before_commit"
            assert run["status"] == ("succeeded" if committed else "failed")
            assert subject["memory_generation"] == (2 if committed else 1)
            assert len(facts) == len(assistant_ids) == int(committed)
            artifact_path = tmp_path / "artifacts" / run_id / "attempt-001.json"
            if fault == "artifact":
                assert not artifact_path.exists()
            else:
                artifact = json.loads(artifact_path.read_text())
                assert artifact["terminal_readback"]["outcome"] == (
                    "committed" if committed else "confirmed_rejection"
                )
                assert artifact["candidate_visible_reply"] == "Okay, Toronto."
            assert transport.calls.count(("chat", "fake::conversation")) == 1
            assert transport.calls.count(("chat", "fake::reviewer")) == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())
