"""Paired serialized packets with a real worker compaction call.

The router response is synthetic; this checks boundaries and provenance, not
whether a real model would preserve a particular memory in its summary.
"""

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
from ade_api.features.agent_runtime.persistence.metadata import (
    conversation_summaries,
    runs,
    summary_sources,
)
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.platform.settings import AdeApiSettings

from workflows.evals.character_memory_dev.natural_packet_support import (
    SummaryTransport,
    seed_complete_history,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="isolated PostgreSQL natural packet database required"
)


def test_paired_generated_summary_preserves_boundary_and_serialized_requests(
    tmp_path, monkeypatch, natural_worker_support
) -> None:
    assert DATABASE_URL is not None
    monkeypatch.setenv("ADE_NATURAL_MEMORY_CAPTURE", "1")
    monkeypatch.setenv("ADE_SOURCE_REVISION", "0" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "1" * 64)
    monkeypatch.setattr(evidence_module, "ARTIFACT_ROOT", tmp_path / "artifacts")

    async def scenario():
        engine = create_persistence_engine(DATABASE_URL)
        settings = AdeApiSettings(
            _env_file=None,
            agent_runtime_mode="development",
            agent_runtime_enabled=True,
            database_url=DATABASE_URL,
            agent_runtime_worker_id="natural-compaction-packet-test",
        )
        catalog = natural_worker_support.catalog()
        transport = SummaryTransport(catalog)
        base_definitions = natural_worker_support.definitions(catalog)

        class PacketDefinitions:
            async def prepare(self, request, *, purpose):
                prepared = await base_definitions.prepare(request, purpose=purpose)
                prepared["memory_policy_version"] = (
                    "natural-user-assertions-v3-"
                    + request.definition_key.rsplit("_", 1)[-1]
                )
                prepared["tool_names"] = list(request.tool_names)
                return prepared

        sessions = PurposeSessionService(
            database=RuntimeDatabase(engine),
            definitions=PacketDefinitions(),
            purpose="evaluation",
            session_namespace="natural-compaction-packet-test",
        )
        service = RunService(
            database=RuntimeDatabase(engine),
            settings=settings,
            router_transport=transport,
            worker_health=natural_worker_support.ready_worker(),
        )
        worker = AgentRuntimeWorker(
            engine=engine, settings=settings, transport=transport
        )
        async with engine.connect() as connection:
            assert (
                not (
                    await connection.execute(
                        select(runs.c.id).where(
                            runs.c.status.in_(("pending", "running"))
                        )
                    )
                )
                .scalars()
                .all()
            )
        artifacts = {}
        histories = {}
        token = uuid4().hex[:12]
        try:
            for variant in ("a", "a0", "b"):
                session = await sessions.create(
                    CreateAgentStudioSessionRequest(
                        idempotency_key=f"summary-{token}-{variant}",
                        new_definition=CreateAgentDefinitionRequest(
                            definition_key=f"summary_{token}_{variant}",
                            name=f"Synthetic summary {variant}",
                            model_key="fake::conversation",
                            reviewer_model_key="fake::reviewer",
                            embedding_model_key="fake::retriever",
                            tool_names=[],
                        ),
                        new_subject=CreateMemorySubjectRequest(
                            external_key=f"summary-{token}-{variant}",
                            display_name="Synthetic summary subject",
                        ),
                    )
                )
                histories[variant] = await seed_complete_history(
                    engine, session, token=f"{token}-{variant}"
                )
                accepted = await service.accept_turn(
                    session["conversation"]["id"],
                    AcceptTurnRequest(
                        content="Which interview opening did I choose?",
                        idempotency_key=f"probe-{token}-{variant}",
                        timeout_seconds=30,
                        retry_count=0,
                    ),
                )
                assert await worker.process_once()
                assert (await service.get_run(accepted["run_id"]))[
                    "status"
                ] == "succeeded"
                artifacts[variant] = json.loads(
                    (
                        tmp_path / "artifacts" / accepted["run_id"] / "attempt-001.json"
                    ).read_text()
                )
                if variant in ("a", "a0"):
                    async with engine.connect() as connection:
                        persisted_summary = (
                            (
                                await connection.execute(
                                    select(conversation_summaries).where(
                                        conversation_summaries.c.conversation_id
                                        == session["conversation"]["id"]
                                    )
                                )
                            )
                            .mappings()
                            .one()
                        )
                        persisted_sources = (
                            (
                                await connection.execute(
                                    select(summary_sources.c.message_id).where(
                                        summary_sources.c.summary_id
                                        == persisted_summary["id"]
                                    )
                                )
                            )
                            .scalars()
                            .all()
                        )
                    assert persisted_summary["through_sequence"] == 58
                    assert persisted_summary["content"] == (
                        "The user chose the afternoon 2pm product-role "
                        "opening instead of the morning operations role."
                    )
                    assert set(map(str, persisted_sources)) == set(
                        histories[variant][:58]
                    )
            tool_session = await sessions.create(
                CreateAgentStudioSessionRequest(
                    idempotency_key=f"tool-{token}",
                    new_definition=CreateAgentDefinitionRequest(
                        definition_key=f"tool_{token}_b",
                        name="Synthetic tool continuation",
                        model_key="fake::conversation",
                        reviewer_model_key="fake::reviewer",
                        embedding_model_key="fake::retriever",
                        tool_names=["search_memory"],
                    ),
                    new_subject=CreateMemorySubjectRequest(
                        external_key=f"tool-{token}",
                        display_name="Synthetic tool subject",
                    ),
                )
            )
            tool_accepted = await service.accept_turn(
                tool_session["conversation"]["id"],
                AcceptTurnRequest(
                    content="Search my memory for Roxy.",
                    idempotency_key=f"tool-probe-{token}",
                    timeout_seconds=30,
                    retry_count=0,
                ),
            )
            assert await worker.process_once()
            assert (await service.get_run(tool_accepted["run_id"]))[
                "status"
            ] == "succeeded"
            tool_artifact = json.loads(
                (
                    tmp_path
                    / "artifacts"
                    / tool_accepted["run_id"]
                    / "attempt-001.json"
                ).read_text()
            )
            a, a0, b = (artifacts[key] for key in ("a", "a0", "b"))
            for variant, item in artifacts.items():
                assert item["terminal_readback"]["outcome"] == "committed"
                assert (
                    item["generation_requests"][0]["messages"]
                    == item["generation"]["messages"]
                )
                assert (
                    item["generation"]["estimated_input_tokens"]
                    <= item["generation"]["input_limit"]
                )
                assert (
                    item["reviewer_request"]["serialized_visible_token_estimate"]
                    <= 6759
                )
                assert any(
                    group["stage"] == "reviewer" and group["attempted"] == 1
                    for group in item["provider_request_counts"]["groups"]
                )
                reviewer_packet = json.loads(
                    item["reviewer_request"]["messages"][1]["content"]
                )
                assert [row["content"] for row in reviewer_packet["context"]] == [
                    row["content"] for row in item["generation"]["source_messages"][:-1]
                ]
                assert all(
                    request["serialized_visible_token_estimate"]
                    <= item["generation"]["input_limit"]
                    for request in item["generation_requests"]
                )
            for item, variant in ((a, "a"), (a0, "a0")):
                result = item["compaction_result"]
                request = item["compaction_request"]
                assert result["summary_through_sequence"] == 58
                assert result["source_message_ids"] == histories[variant][:58]
                assert (
                    "afternoon 2pm product-role opening"
                    in json.loads(request["messages"][1]["content"])["new_messages"][0][
                        "content"
                    ]
                )
                assert (
                    json.loads(request["messages"][1]["content"])["new_messages"][-1][
                        "sequence"
                    ]
                    == 58
                )
                assert request["serialized_visible_token_estimate"] <= 6759
                assert any(
                    group["stage"] == "compaction" and group["attempted"] == 1
                    for group in item["provider_request_counts"]["groups"]
                )
                assert item["generation"]["source_messages"][0]["role"] == "user"
                assert len(item["generation"]["source_messages"]) == 11
            assert [
                (row["role"], row["content"])
                for row in a["generation"]["source_messages"]
            ] == [
                (row["role"], row["content"])
                for row in a0["generation"]["source_messages"]
            ]
            assert a["generation"]["omitted_message_ids"] == []
            assert a0["generation"]["omitted_message_ids"] == []
            a_messages = a["generation"]["messages"]
            a0_messages = a0["generation"]["messages"]
            summary_section = (
                "\n\nConversation summary (attributed, not certified current):\n"
                "The user chose the afternoon 2pm product-role opening "
                "instead of the morning operations role."
            )
            assert (
                a_messages[0]["content"].replace(summary_section, "")
                == a0_messages[0]["content"]
            )
            assert a_messages[1:] == a0_messages[1:]
            assert b["compaction_request"] == {"stage": "absent"}
            assert not any(
                group["stage"] == "compaction"
                for group in b["provider_request_counts"]["groups"]
            )
            assert len(b["generation"]["source_messages"]) <= 17
            assert "afternoon 2pm product-role opening" not in json.dumps(
                a["generation"]["source_messages"], ensure_ascii=False
            )
            a_reviewer_packet = json.loads(
                a["reviewer_request"]["messages"][1]["content"]
            )
            assert "afternoon 2pm product-role opening" not in json.dumps(
                a_reviewer_packet["context"], ensure_ascii=False
            )
            assert a_reviewer_packet["targets"] == []
            assert a["candidate_visible_reply"] == (
                "You chose the afternoon 2pm product-role opening."
            )
            assert "afternoon 2pm product-role opening" in a_messages[0]["content"]
            assert "afternoon 2pm product-role opening" not in a0_messages[0]["content"]
            assert (
                "afternoon 2pm product-role opening"
                not in b["generation"]["messages"][0]["content"]
            )
            assert a0["candidate_visible_reply"] == (
                "I don't have that choice in the supplied context."
            )
            assert b["candidate_visible_reply"] == a0["candidate_visible_reply"]
            first, continuation = tool_artifact["generation_requests"]
            assert (
                continuation["messages"][: len(first["messages"])] == first["messages"]
            )
            assert [message["role"] for message in continuation["messages"][-2:]] == [
                "assistant",
                "tool",
            ]
            assert continuation["messages"][-1]["tool_call_id"] == "synthetic-search-1"
            assert (
                continuation["serialized_visible_token_estimate"]
                <= tool_artifact["generation"]["input_limit"]
            )
            assert any(
                group["stage"] == "conversation" and group["attempted"] == 2
                for group in tool_artifact["provider_request_counts"]["groups"]
            )
            assert tool_artifact["terminal_readback"]["outcome"] == "committed"
            assert all(
                request["serialized_visible_token_estimate"]
                <= tool_artifact["generation"]["input_limit"]
                for request in tool_artifact["generation_requests"]
            )
            assert [
                row["content"]
                for row in json.loads(
                    tool_artifact["reviewer_request"]["messages"][1]["content"]
                )["context"]
            ] == [
                row["content"]
                for row in tool_artifact["generation"]["source_messages"][:-1]
            ]
        finally:
            await engine.dispose()

    asyncio.run(scenario())
