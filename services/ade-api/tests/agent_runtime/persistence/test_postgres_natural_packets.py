"""Serialized A/A0/B pressure packets through the real service and worker path.

All historical state is labelled synthetic setup in an exclusively owned local DB.
The fake router proves packet admission and commit plumbing, not model usefulness.
"""

from __future__ import annotations

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
    conversation_leases,
    runs,
)
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.platform.settings import AdeApiSettings


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="isolated PostgreSQL natural packet database required"
)


from workflows.evals.character_memory_dev.natural_packet_support import (
    PacketTransport,
    seed_pressure_state,
)


def test_pressure_packets_are_real_worker_inputs(
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
            agent_runtime_worker_id="natural-packet-test",
        )
        catalog = natural_worker_support.catalog()
        for item in catalog["items"]:
            if item["model_key"] == "fake::conversation":
                item["deployment"]["fingerprint"]["context_settings"][
                    "total_tokens"
                ] = 4096
        transport = PacketTransport(catalog)
        base_definitions = natural_worker_support.definitions(catalog)

        class PacketDefinitions:
            async def prepare(self, request, *, purpose):
                prepared = await base_definitions.prepare(request, purpose=purpose)
                prepared["memory_policy_version"] = (
                    f"natural-user-assertions-v4-{request.definition_key.rsplit('_', 1)[-1]}"
                )
                prepared["prompt_content"] = "P" * 5310
                return prepared

        sessions = PurposeSessionService(
            database=RuntimeDatabase(engine),
            definitions=PacketDefinitions(),
            purpose="evaluation",
            session_namespace="natural-packet-test",
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
            active = (
                (
                    await connection.execute(
                        select(runs.c.id).where(
                            runs.c.status.in_(("pending", "running"))
                        )
                    )
                )
                .scalars()
                .all()
            )
        assert not active, (
            "packet test requires an exclusively idle disposable database"
        )
        artifacts = {}
        token = uuid4().hex[:12]
        try:
            for variant in ("a", "a0", "b"):
                session = await sessions.create(
                    CreateAgentStudioSessionRequest(
                        idempotency_key=f"packet-{token}-{variant}",
                        new_definition=CreateAgentDefinitionRequest(
                            definition_key=f"packet_{token}_{variant}",
                            name=f"Synthetic packet {variant}",
                            model_key="fake::conversation",
                            reviewer_model_key="fake::reviewer",
                            embedding_model_key="fake::retriever",
                            tool_names=[],
                        ),
                        new_subject=CreateMemorySubjectRequest(
                            external_key=f"packet-{token}-{variant}",
                            display_name="Synthetic packet subject",
                        ),
                    )
                )
                await seed_pressure_state(engine, session, token=f"{token}-{variant}")
                accepted = await service.accept_turn(
                    session["conversation"]["id"],
                    AcceptTurnRequest(
                        content="What breed is Roxy?",
                        idempotency_key=f"probe-{token}-{variant}",
                        timeout_seconds=30,
                        retry_count=0,
                    ),
                )
                async with engine.connect() as connection:
                    pending_lease = (
                        (
                            await connection.execute(
                                select(conversation_leases).where(
                                    conversation_leases.c.run_id == accepted["run_id"]
                                )
                            )
                        )
                        .mappings()
                        .one()
                    )
                assert pending_lease["holder_id"] == "pending"
                assert pending_lease["expires_at"] == pending_lease["acquired_at"]
                assert await worker.process_once()
                run = await service.get_run(accepted["run_id"])
                assert run["status"] == "succeeded", run
                artifacts[variant] = json.loads(
                    (
                        tmp_path / "artifacts" / accepted["run_id"] / "attempt-001.json"
                    ).read_text()
                )
            a, a0, b = (artifacts[key] for key in ("a", "a0", "b"))
            assert all(
                item["terminal_readback"]["outcome"] == "committed"
                for item in artifacts.values()
            )
            assert all(
                item["reviewer_request"]["serialized_visible_token_estimate"] <= 6759
                for item in artifacts.values()
            )
            assert all(
                len(item["reviewer_request"]["messages"]) == 2
                for item in artifacts.values()
            )
            assert all(
                [message["role"] for message in item["generation"]["source_messages"]]
                == ["user"]
                for item in (a, a0)
            )
            assert all(
                item["generation"]["source_messages"][0]["content"]
                == "What breed is Roxy?"
                for item in (a, a0)
            )
            assert a["generation"]["messages"] == a0["generation"]["messages"]
            assert [item["role"] for item in b["generation"]["source_messages"]] == [
                "user",
                "assistant",
                "user",
                "assistant",
                "user",
            ]
            assert all(
                item["generation"]["estimated_input_tokens"] <= 3072
                for item in artifacts.values()
            )
            assert b["generation"]["omitted_message_ids"] == []
            assert all(
                len(
                    json.loads(item["reviewer_request"]["messages"][1]["content"])[
                        "targets"
                    ]
                )
                == 48
                for item in artifacts.values()
            )
            target_views = [
                sorted(
                    (
                        target["fact_type"],
                        target["qualifier"],
                        target["value"],
                        target["status"],
                    )
                    for target in json.loads(
                        item["reviewer_request"]["messages"][1]["content"]
                    )["targets"]
                )
                for item in artifacts.values()
            ]
            assert target_views[0] == target_views[1] == target_views[2]
            assert all(
                item["generation_requests"][0]["messages"]
                == item["generation"]["messages"]
                for item in artifacts.values()
            )
            for item in artifacts.values():
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
            assert all(
                {
                    group["stage"]: group["attempted"]
                    for group in item["provider_request_counts"]["groups"]
                }.items()
                >= {"conversation": 1, "reviewer": 1, "retrieval_query": 1}.items()
                for item in artifacts.values()
            )
        finally:
            await engine.dispose()

    import asyncio

    asyncio.run(scenario())
