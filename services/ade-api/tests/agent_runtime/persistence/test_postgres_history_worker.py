"""H3 no-write completion fences against source loss and deadline expiry."""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import SQLAlchemyError

import ade_api.features.agent_runtime.history_attempt as history_attempt_module
from ade_api.features.agent_runtime.agent_studio_sessions import PurposeSessionService
from ade_api.features.agent_runtime.contracts import (
    AcceptTurnRequest,
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
)
from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.history_admission import HistoryProbe
from ade_api.features.agent_runtime.history_native_rank import HISTORY_EMBEDDING_ROUTE
from ade_api.features.agent_runtime.natural_context import HISTORY_PROBE_POLICY
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.memory import MemoryRepository
from ade_api.features.agent_runtime.persistence.metadata import (
    conversations,
    memory_revisions,
    messages,
    run_attempts,
    runs,
)
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.platform.settings import AdeApiSettings
from workflows.evals.character_memory_dev.history_reader_test_support import (
    assistant,
    require_disposable_database_url,
    turn,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="disposable PostgreSQL history test database required"
)


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "native_qwen",
        "empty_arm",
        "purge_before_generation",
        "hash_before_generation",
        "deadline_before_generation",
        "unavailable_before_generation",
        "purge_before_continuation",
        "purge_before_review",
        "hash_before_review",
        "unavailable_before_review",
        "h_conflict_first",
        "h_conflict_last",
        "cancel_at_review",
        "purge_after_review",
        "deadline_after_review",
    ],
)
def test_no_write_history_finalization_is_atomic(
    fault: str, natural_worker_support, monkeypatch
) -> None:
    assert DATABASE_URL is not None
    require_disposable_database_url(DATABASE_URL)
    monkeypatch.setenv("ADE_SOURCE_REVISION", "0" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "1" * 64)

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        database = RuntimeDatabase(engine)
        settings = AdeApiSettings(
            _env_file=None,
            agent_runtime_mode="development",
            agent_runtime_enabled=True,
            database_url=DATABASE_URL,
            agent_runtime_worker_id=f"history-h3-{fault}",
        )
        catalog = natural_worker_support.catalog()
        if fault == "native_qwen":
            retriever = next(
                item
                for item in catalog["items"]
                if "retriever" in item["deployment"]["roles"]
            )
            retriever["model_key"] = HISTORY_EMBEDDING_ROUTE
            retriever["deployment"]["fingerprint"]["sampling_settings"][
                "dimensions"
            ] = 1024

        class ProbeDefinitions(natural_worker_support.definitions):
            async def prepare(self, request, *, purpose):
                prepared = await super().prepare(request, purpose=purpose)
                prepared["memory_policy_version"] = HISTORY_PROBE_POLICY
                return prepared

        class ProbeTransport(natural_worker_support.transport):
            old_assistant_id: str | None = None
            target_run_id: str | None = None

            async def embeddings(self, payload, *, timeout_seconds):
                if fault == "native_qwen":
                    self.calls.append(("embeddings", payload["model"]))
                    assert payload["model"] == HISTORY_EMBEDDING_ROUTE
                    return {
                        "data": [
                            {"index": index, "embedding": [1.0] * 1024}
                            for index, _ in enumerate(payload["input"])
                        ]
                    }
                return await super().embeddings(
                    payload, timeout_seconds=timeout_seconds
                )

            async def chat_completion(self, payload, *, timeout_seconds):
                if payload["model"] == "fake::conversation" and fault in {
                    "purge_before_continuation",
                    "purge_before_review",
                    "hash_before_review",
                }:
                    self.calls.append(("chat", "fake::conversation"))
                    assert self.old_assistant_id is not None
                    async with engine.begin() as connection:
                        if fault == "hash_before_review":
                            await connection.execute(
                                update(messages)
                                .where(messages.c.id == self.old_assistant_id)
                                .values(content="tampered")
                            )
                        else:
                            await connection.execute(
                                delete(messages).where(
                                    messages.c.id == self.old_assistant_id
                                )
                            )
                    if fault == "purge_before_continuation":
                        return {
                            "id": "fake-tool-request",
                            "choices": [
                                {
                                    "finish_reason": "tool_calls",
                                    "message": {
                                        "role": "assistant",
                                        "tool_calls": [
                                            {
                                                "id": "call-1",
                                                "type": "function",
                                                "function": {
                                                    "name": "search_memory",
                                                    "arguments": '{"query":"Toronto","limit":1}',
                                                },
                                            }
                                        ],
                                    },
                                }
                            ],
                        }
                    return {
                        "id": "fake-conversation",
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {
                                    "role": "assistant",
                                    "content": "Okay, Toronto.",
                                },
                            }
                        ],
                    }
                if payload["model"] == "fake::reviewer":
                    self.calls.append(("chat", "fake::reviewer"))
                    packet = json.loads(payload["messages"][1]["content"])
                    assert len(packet["history"]) == int(
                        fault
                        not in {
                            "empty_arm",
                            "purge_before_generation",
                            "unavailable_before_generation",
                        }
                    )
                    if packet["history"]:
                        assert packet["history"][0]["messages"][0]["handle"] == "H1"
                    if fault == "purge_after_review":
                        assert self.old_assistant_id is not None
                        async with engine.begin() as connection:
                            await connection.execute(
                                delete(messages).where(
                                    messages.c.id == self.old_assistant_id
                                )
                            )
                    if fault == "cancel_at_review":
                        assert self.target_run_id is not None
                        await run_service.cancel_run(self.target_run_id)
                    decisions = []
                    if fault in {"h_conflict_first", "h_conflict_last"}:
                        conflict = {
                            "kind": "conflict",
                            "current_quote": "I live in Toronto",
                            "candidate_reply_quote": "Toronto",
                            "history": {
                                "handle": "H1",
                                "quote": "早上我喜欢咖啡。",
                            },
                        }
                        write = {
                            "kind": "subject_add",
                            "fact_type": "person.current_location",
                            "value": "Toronto",
                            "evidence": {
                                "mode": "direct",
                                "current_quote": "I live in Toronto",
                            },
                        }
                        decisions = (
                            [conflict, write]
                            if fault == "h_conflict_first"
                            else [write, conflict]
                        )
                    return {
                        "id": "fake-reviewer",
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {
                                    "content": json.dumps({"decisions": decisions})
                                },
                            }
                        ],
                    }
                return await super().chat_completion(
                    payload, timeout_seconds=timeout_seconds
                )

        transport = ProbeTransport(catalog)
        sessions = PurposeSessionService(
            database=database,
            definitions=ProbeDefinitions(catalog),
            purpose="evaluation",
            session_namespace=f"history-h3-{fault}",
        )
        run_service = RunService(
            database=database,
            settings=settings,
            router_transport=transport,
            worker_health=natural_worker_support.ready_worker(),
        )
        old_run_id = ""
        probe = (
            HistoryProbe(arm="empty_history")
            if fault == "empty_arm"
            else HistoryProbe(
                arm="automatic_history", ranking_recipe="probe_local_qwen_cosine"
            )
            if fault == "native_qwen"
            else HistoryProbe(
                arm="automatic_history",
                select_run_ids=lambda corpus, _current, _local: [old_run_id],
            )
        )
        worker = AgentRuntimeWorker(
            engine=engine,
            settings=settings,
            transport=transport,
            history_probe=probe,
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
            assert not active, "history worker test requires an idle owned database"
            session = await sessions.create(
                CreateAgentStudioSessionRequest(
                    idempotency_key=f"history-h3-{token}",
                    new_definition=CreateAgentDefinitionRequest(
                        definition_key=f"history_h3_{token}",
                        name="History H3 test",
                        model_key="fake::conversation",
                        reviewer_model_key="fake::reviewer",
                        embedding_model_key=(
                            HISTORY_EMBEDDING_ROUTE
                            if fault == "native_qwen"
                            else "fake::retriever"
                        ),
                        tool_names=(
                            ["search_memory"]
                            if fault == "purge_before_continuation"
                            else []
                        ),
                    ),
                    new_subject=CreateMemorySubjectRequest(
                        external_key=f"history-h3-{token}",
                        display_name="Synthetic user",
                    ),
                )
            )
            current_conversation_id = session["conversation"]["id"]
            subject_id = session["memory_subject"]["id"]
            async with engine.begin() as connection:
                source = (
                    (
                        await connection.execute(
                            select(conversations).where(
                                conversations.c.id == current_conversation_id
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                old_conversation_id = str(uuid4())
                await connection.execute(
                    insert(conversations).values(
                        id=old_conversation_id,
                        workspace_id=source["workspace_id"],
                        agent_definition_version_id=source[
                            "agent_definition_version_id"
                        ],
                        memory_subject_id=subject_id,
                        purpose="evaluation",
                        archived_at="2026-01-01T00:00:00Z",
                    )
                )
                old = await turn(
                    connection,
                    source["workspace_id"],
                    old_conversation_id,
                    "早上我喜欢咖啡。",
                )
                old_run_id = old["run_id"]
                transport.old_assistant_id = await assistant(
                    connection,
                    source["workspace_id"],
                    old_conversation_id,
                    old,
                    "我记住你那时说的话。",
                )
            accepted = await run_service.accept_turn(
                current_conversation_id,
                AcceptTurnRequest(
                    content="I live in Toronto.",
                    idempotency_key=f"target-{token}",
                    timeout_seconds=30,
                    retry_count=0,
                ),
            )
            run_id = accepted["run_id"]
            transport.target_run_id = run_id
            if fault == "deadline_before_generation":
                original_authorize = (
                    history_attempt_module.HistoryAttempt.authorize_request
                )

                async def expired_before_generation(self, payload):
                    self.deadline = time.monotonic() - 1
                    await original_authorize(self, payload)

                monkeypatch.setattr(
                    history_attempt_module.HistoryAttempt,
                    "authorize_request",
                    expired_before_generation,
                )
            if fault in {
                "purge_before_generation",
                "hash_before_generation",
                "unavailable_before_generation",
                "unavailable_before_review",
            }:
                original_check = history_attempt_module.validate_history_before_dispatch
                check_count = 0

                async def inject_check_fault(*args, **kwargs):
                    nonlocal check_count
                    check_count += 1
                    if fault == "unavailable_before_review" and check_count == 2:
                        raise SQLAlchemyError("synthetic history read unavailable")
                    if fault == "unavailable_before_generation" and check_count == 1:
                        raise SQLAlchemyError("synthetic history read unavailable")
                    if check_count == 1 and fault in {
                        "purge_before_generation",
                        "hash_before_generation",
                    }:
                        async with engine.begin() as connection:
                            if fault == "hash_before_generation":
                                await connection.execute(
                                    update(messages)
                                    .where(messages.c.id == transport.old_assistant_id)
                                    .values(content="tampered")
                                )
                            else:
                                await connection.execute(
                                    delete(messages).where(
                                        messages.c.id == transport.old_assistant_id
                                    )
                                )
                    return await original_check(*args, **kwargs)

                monkeypatch.setattr(
                    history_attempt_module,
                    "validate_history_before_dispatch",
                    inject_check_fault,
                )
            if fault == "deadline_after_review":
                original = worker.finalizer.commit_success

                async def expired(claim, attempt_id, result, *, trace=None):
                    await original(
                        claim,
                        attempt_id,
                        replace(result, history_deadline=time.monotonic() - 1),
                        trace=trace,
                    )

                worker.finalizer.commit_success = expired  # type: ignore[method-assign]
            assert await worker.process_once()
            observed = await run_service.get_run(run_id)
            async with engine.connect() as connection:
                subject = await MemoryRepository(connection).get_subject(subject_id)
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
                outcomes = list(
                    (
                        await connection.execute(
                            select(run_attempts.c.provider_outcome).where(
                                run_attempts.c.run_id == run_id
                            )
                        )
                    ).scalars()
                )
            committed = fault in {
                "none",
                "native_qwen",
                "empty_arm",
                "purge_before_generation",
                "unavailable_before_generation",
            }
            assert observed["status"] == (
                "succeeded"
                if committed
                else "cancelled"
                if fault == "cancel_at_review"
                else "failed"
            )
            assert len(assistant_ids) == int(committed)
            assert revision_ids == []
            assert subject["memory_generation"] == 1
            assert transport.calls.count(("chat", "fake::conversation")) == int(
                fault not in {"hash_before_generation", "deadline_before_generation"}
            )
            assert transport.calls.count(("chat", "fake::reviewer")) == int(
                fault
                not in {
                    "hash_before_generation",
                    "deadline_before_generation",
                    "purge_before_continuation",
                    "purge_before_review",
                    "hash_before_review",
                    "unavailable_before_review",
                }
            )
            if fault == "native_qwen":
                # One existing fact query, then document and query dispatches.
                assert (
                    transport.calls.count(("embeddings", HISTORY_EMBEDDING_ROUTE)) == 3
                )
            if committed:
                assert outcomes[0]["history_probe_status"] == (
                    "purged"
                    if fault == "purge_before_generation"
                    else "unavailable"
                    if fault == "unavailable_before_generation"
                    else "empty"
                    if fault == "empty_arm"
                    else "admitted"
                )
        finally:
            await engine.dispose()

    asyncio.run(scenario())
