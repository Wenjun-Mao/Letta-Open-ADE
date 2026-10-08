"""A late fault rolls back real summary, dialogue and indexed memory writes."""

from __future__ import annotations

import asyncio
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import select

from ade_api.features.agent_runtime.contracts import (
    AcceptTurnRequest,
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
)
from ade_api.features.agent_runtime.persistence.conversations import (
    ConversationRepository,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    conversation_summaries,
    conversations,
    memory_embeddings,
    memory_entities,
    memory_facts,
    memory_revisions,
    memory_revision_sources,
    memory_subjects,
    messages,
    run_attempts,
    run_events,
    runs,
    summary_sources,
)
from workflows.evals.character_memory_dev.natural_packet_support import (
    SummaryTransport,
    seed_complete_history,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="owned disposable PostgreSQL required"
)


class UpdatingSummaryTransport(SummaryTransport):
    async def chat_completion(self, payload, *, timeout_seconds):
        if payload["model"] == "fake::reviewer":
            self.calls.append("reviewer")
            return {
                "id": "rollback-review",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "decisions": [
                                        {
                                            "kind": "subject_add",
                                            "fact_type": "person.current_location",
                                            "value": "Toronto",
                                            "evidence": {
                                                "mode": "direct",
                                                "current_quote": "I live in Toronto",
                                            },
                                        }
                                    ]
                                }
                            ),
                        },
                    }
                ],
            }
        return await super().chat_completion(payload, timeout_seconds=timeout_seconds)


def test_summary_staged_before_fault_rolls_back_the_whole_success_bundle(
    monkeypatch, compaction_packet_runtime
):
    assert DATABASE_URL is not None
    monkeypatch.setenv("ADE_SOURCE_REVISION", "0" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "1" * 64)
    runtime = compaction_packet_runtime(
        DATABASE_URL, transport_type=UpdatingSummaryTransport
    )
    engine, worker, service = runtime.engine, runtime.worker, runtime.service
    original = ConversationRepository.create_compaction
    staged = []

    async def scenario():
        token = uuid4().hex[:12]
        try:
            async with engine.connect() as connection:
                assert not (
                    await connection.execute(
                        select(runs.c.id).where(
                            runs.c.status.in_(("pending", "running"))
                        )
                    )
                ).all()
            session = await runtime.sessions.create(
                CreateAgentStudioSessionRequest(
                    idempotency_key=f"rollback-{token}",
                    new_definition=CreateAgentDefinitionRequest(
                        definition_key=f"rollback_{token}_a",
                        name="Synthetic rollback",
                        model_key="fake::conversation",
                        reviewer_model_key="fake::reviewer",
                        embedding_model_key="fake::retriever",
                        tool_names=[],
                    ),
                    new_subject=CreateMemorySubjectRequest(
                        external_key=f"rollback-{token}", display_name="Synthetic user"
                    ),
                )
            )
            conversation_id = session["conversation"]["id"]
            subject_id = session["memory_subject"]["id"]
            history = await seed_complete_history(engine, session, token=token)
            accepted = await service.accept_turn(
                conversation_id,
                AcceptTurnRequest(
                    content="I live in Toronto.",
                    idempotency_key=f"turn-{token}",
                    timeout_seconds=30,
                    retry_count=0,
                ),
            )
            run_id = accepted["run_id"]

            async def snapshot(connection):
                result = {}
                for table, condition in [
                    (messages, messages.c.conversation_id == conversation_id),
                    (conversations, conversations.c.id == conversation_id),
                    (memory_subjects, memory_subjects.c.id == subject_id),
                    (memory_entities, memory_entities.c.subject_id == subject_id),
                    (memory_facts, memory_facts.c.subject_id == subject_id),
                    (memory_revisions, memory_revisions.c.subject_id == subject_id),
                    (
                        memory_revision_sources,
                        memory_revision_sources.c.revision_id.in_(
                            select(memory_revisions.c.id).where(
                                memory_revisions.c.subject_id == subject_id
                            )
                        ),
                    ),
                    (memory_embeddings, memory_embeddings.c.subject_id == subject_id),
                    (
                        conversation_summaries,
                        conversation_summaries.c.conversation_id == conversation_id,
                    ),
                    (
                        summary_sources,
                        summary_sources.c.summary_id.in_(
                            select(conversation_summaries.c.id).where(
                                conversation_summaries.c.conversation_id
                                == conversation_id
                            )
                        ),
                    ),
                ]:
                    result[table.name] = [
                        dict(row)
                        for row in (
                            await connection.execute(
                                select(table)
                                .where(condition)
                                .order_by(*table.primary_key.columns)
                            )
                        ).mappings()
                    ]
                return result

            async with engine.connect() as connection:
                before = await snapshot(connection)
            assert len(before["messages"]) == len(history) + 1

            async def stage_then_fail(repository, **kwargs):
                summary = await original(repository, **kwargs)
                connection = repository._connection
                inside = await snapshot(connection)
                assert len(inside["conversation_summaries"]) == 1
                assert len(inside["summary_sources"]) == 58
                assert len(inside["messages"]) == len(before["messages"]) + 1
                assert (
                    len(inside["memory_facts"])
                    == len(inside["memory_revisions"])
                    == len(inside["memory_embeddings"])
                    == 1
                )
                staged.append(str(summary["id"]))
                raise OSError("synthetic late compaction transaction failure")

            monkeypatch.setattr(
                ConversationRepository, "create_compaction", stage_then_fail
            )
            assert await worker.process_once()
            assert len(staged) == 1, (
                "the real SQL writes must precede the injected failure"
            )
            observed = await service.get_run(run_id)
            assert observed["status"] == "failed"
            assert observed["attempt_count"] == 1
            assert runtime.transport.calls.count("compaction") == 1
            # A new connection reads authoritative state after transaction rollback.
            async with engine.connect() as connection:
                assert await snapshot(connection) == before
                event_rows = (
                    (
                        await connection.execute(
                            select(run_events.c.event_type, run_events.c.payload).where(
                                run_events.c.run_id == run_id
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
                event_types = {row["event_type"] for row in event_rows}
                attempts = (
                    (
                        await connection.execute(
                            select(run_attempts.c.status).where(
                                run_attempts.c.run_id == run_id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
            assert "run.failed" in event_types
            assert not event_types & {
                "context.built",
                "memory.proposed",
                "memory.committed",
                "summary.committed",
                "run.completed",
            }
            message_events = [
                row["payload"]
                for row in event_rows
                if row["event_type"] == "message.committed"
            ]
            assert len(message_events) == 1
            assert message_events[0]["role"] == "user"
            assert attempts == ["failed"]
        finally:
            await engine.dispose()

    asyncio.run(scenario())
