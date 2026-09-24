"""Real-worker A/A0/B packets for current, ended, invalidated and forgotten views."""

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
from workflows.evals.character_memory_dev.natural_packet_support import PacketTransport
from workflows.evals.character_memory_dev.natural_state_packet_support import (
    seed_state_packet,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="isolated PostgreSQL natural packet database required"
)


CASES = {
    "residence_visit": {
        "history": [
            ("I live in Toronto.", "Toronto is your home."),
            ("I am visiting Paris this weekend.", "You're visiting Paris."),
        ],
        "current": "Where should I walk nearby while visiting Paris?",
        "facts": [
            {
                "fact_type": "person.current_location",
                "value": "Toronto",
                "status": "active",
                "assertion": "I live in Toronto.",
                "index_prior": True,
            }
        ],
        "expected_status": "active",
    },
    "ended": {
        "history": [
            ("I am dating Xiao Wang.", "I hear you're dating Xiao Wang."),
            ("We broke up.", "I hear the relationship ended."),
        ],
        "current": "What could I do this weekend?",
        "facts": [
            {
                "fact_type": "relationship.person",
                "qualifier": "partner",
                "value": "Xiao Wang",
                "status": "inactive",
                "assertion": "I am dating Xiao Wang.",
                "transitions": [
                    {"operation": "end", "reason": "ended", "source": "We broke up."}
                ],
                "index_prior": True,
            }
        ],
        "expected_status": "inactive",
    },
    "invalidated": {
        "history": [
            ("I live in Beijing.", "I hear you're in Beijing."),
            ("That Beijing claim was wrong; I won't share my home.", "Understood."),
        ],
        "current": "What can we talk about?",
        "facts": [
            {
                "fact_type": "person.current_location",
                "value": "Beijing",
                "status": "inactive",
                "assertion": "I live in Beijing.",
                "transitions": [
                    {
                        "operation": "end",
                        "reason": "invalidated",
                        "source": "That Beijing claim was wrong; I won't share my home.",
                    }
                ],
                "index_prior": True,
            }
        ],
        "expected_status": "inactive",
    },
    "forgotten_old_summary": {
        "history": [
            ("I am dating Xiao Wang.", "I hear you're dating Xiao Wang."),
            (
                "We broke up; remove that relationship from saved memory.",
                "I hear the relationship ended and removal was requested.",
            ),
        ],
        "current": "What could I do this weekend?",
        "facts": [
            {
                "fact_type": "relationship.person",
                "qualifier": "partner",
                "value": "Xiao Wang",
                "status": "forgotten",
                "assertion": "I am dating Xiao Wang.",
                "transitions": [
                    {"operation": "end", "reason": "ended", "source": "We broke up."},
                    {
                        "operation": "forget",
                        "reason": "forgotten",
                        "source": "Remove that relationship from saved memory.",
                    },
                ],
                "index_prior": True,
            }
        ],
        "summary_content": "Old report: Xiao Wang is my current partner.",
        "expected_status": "forgotten",
    },
}


def test_lifecycle_and_narrative_packets_share_exact_reviewer_sources(
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
            agent_runtime_worker_id="natural-state-packet-test",
        )
        catalog = natural_worker_support.catalog()
        transport = PacketTransport(catalog)
        base_definitions = natural_worker_support.definitions(catalog)

        class PacketDefinitions:
            async def prepare(self, request, *, purpose):
                prepared = await base_definitions.prepare(request, purpose=purpose)
                prepared["memory_policy_version"] = (
                    "natural-user-assertions-v4-"
                    + request.definition_key.rsplit("_", 1)[-1]
                )
                return prepared

        sessions = PurposeSessionService(
            database=RuntimeDatabase(engine),
            definitions=PacketDefinitions(),
            purpose="evaluation",
            session_namespace="natural-state-packet-test",
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
        token = uuid4().hex[:12]
        packets = {}
        try:
            for case_name, case in CASES.items():
                packets[case_name] = {}
                for variant in ("a", "a0", "b"):
                    session = await sessions.create(
                        CreateAgentStudioSessionRequest(
                            idempotency_key=f"state-{token}-{case_name}-{variant}",
                            new_definition=CreateAgentDefinitionRequest(
                                definition_key=f"state_{token}_{case_name}_{variant}",
                                name=f"Synthetic {case_name} {variant}",
                                model_key="fake::conversation",
                                reviewer_model_key="fake::reviewer",
                                embedding_model_key="fake::retriever",
                                tool_names=[],
                            ),
                            new_subject=CreateMemorySubjectRequest(
                                external_key=f"state-{token}-{case_name}-{variant}",
                                display_name="Synthetic state subject",
                            ),
                        )
                    )
                    seeded = await seed_state_packet(
                        engine,
                        session,
                        token=f"{token}-{case_name}-{variant}",
                        history=case["history"],
                        facts=case["facts"],
                        summary_content=case.get("summary_content", ""),
                    )
                    if case.get("summary_content"):
                        async with engine.connect() as connection:
                            summary = (
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
                            source_ids = (
                                (
                                    await connection.execute(
                                        select(summary_sources.c.message_id).where(
                                            summary_sources.c.summary_id
                                            == summary["id"]
                                        )
                                    )
                                )
                                .scalars()
                                .all()
                            )
                        assert summary["through_sequence"] == 2
                        assert set(map(str, source_ids)) == set(
                            seeded["history_message_ids"][:2]
                        )
                    accepted = await service.accept_turn(
                        session["conversation"]["id"],
                        AcceptTurnRequest(
                            content=case["current"],
                            idempotency_key=f"probe-{token}-{case_name}-{variant}",
                            timeout_seconds=30,
                            retry_count=0,
                        ),
                    )
                    assert await worker.process_once()
                    assert (await service.get_run(accepted["run_id"]))[
                        "status"
                    ] == "succeeded"
                    item = json.loads(
                        (
                            tmp_path
                            / "artifacts"
                            / accepted["run_id"]
                            / "attempt-001.json"
                        ).read_text()
                    )
                    packets[case_name][variant] = item
                    fact_id = seeded["fact_ids"][0]
                    targets = json.loads(
                        item["reviewer_request"]["messages"][1]["content"]
                    )["targets"]
                    selected = item["generation"]["retrieved_fact_ids"]
                    if case["expected_status"] == "forgotten":
                        assert fact_id not in selected
                        assert all(
                            target["status"] != "forgotten" for target in targets
                        )
                    else:
                        assert fact_id in selected
                        assert any(
                            target["status"] == case["expected_status"]
                            for target in targets
                        )
                    assert item["terminal_readback"]["outcome"] == "committed"
                    assert item["terminal_readback"]["observed_memory_generation"] == 2
                    assert (
                        item["generation_requests"][0]["messages"]
                        == item["generation"]["messages"]
                    )
                    source = item["generation"]["source_messages"]
                    reviewer_source = json.loads(
                        item["reviewer_request"]["messages"][1]["content"]
                    )["context"]
                    assert [row["content"] for row in source[:-1]] == [
                        row["content"] for row in reviewer_source
                    ]
                    assert all(
                        request["serialized_visible_token_estimate"]
                        <= item["generation"]["input_limit"]
                        for request in item["generation_requests"]
                    )
            a, a0, b = (
                packets["forgotten_old_summary"][variant]
                for variant in ("a", "a0", "b")
            )
            summary_section = (
                "\n\nConversation summary (attributed, not certified current):\n"
                "Old report: Xiao Wang is my current partner."
            )
            assert (
                a["generation"]["messages"][0]["content"].replace(summary_section, "")
                == a0["generation"]["messages"][0]["content"]
            )
            assert a["generation"]["messages"][1:] == a0["generation"]["messages"][1:]
            assert (
                "Old report: Xiao Wang is my current partner."
                in a["generation"]["messages"][0]["content"]
            )
            assert (
                "Old report: Xiao Wang is my current partner."
                not in a0["generation"]["messages"][0]["content"]
            )
            assert (
                "Old report: Xiao Wang is my current partner."
                not in b["generation"]["messages"][0]["content"]
            )
            assert [row["role"] for row in a["generation"]["source_messages"]] == [
                row["role"] for row in a0["generation"]["source_messages"]
            ]
            assert (
                a["generation"]["source_messages"][-1]["content"]
                == CASES["forgotten_old_summary"]["current"]
            )
        finally:
            await engine.dispose()

    asyncio.run(scenario())
