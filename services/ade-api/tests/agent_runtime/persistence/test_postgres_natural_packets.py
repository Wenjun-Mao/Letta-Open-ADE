"""Serialized A/A0/B pressure packets through the real service and worker path.

All historical state is labelled synthetic setup in an exclusively owned local DB.
The fake router proves packet admission and commit plumbing, not model usefulness.
"""

from __future__ import annotations

import hashlib
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import insert, select, update

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
    conversations,
    memory_entities,
    memory_facts,
    memory_revision_sources,
    memory_revisions,
    memory_subjects,
    messages,
    runs,
)
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.platform.settings import AdeApiSettings


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="isolated PostgreSQL natural packet database required"
)


class PacketTransport:
    def __init__(self, catalog: dict) -> None:
        self._catalog = catalog
        self.calls: list[str] = []

    async def catalog(self, *, timeout_seconds):
        return self._catalog

    async def embeddings(self, payload, *, timeout_seconds):
        self.calls.append("embedding")
        return {
            "data": [
                {"index": index, "embedding": [1.0, 0.0, 0.0]}
                for index, _ in enumerate(payload["input"])
            ]
        }

    async def chat_completion(self, payload, *, timeout_seconds):
        model = payload["model"]
        self.calls.append(model)
        content = (
            "Roxy is your Husky."
            if model == "fake::conversation"
            else json.dumps({"proposals": [], "claim_dispositions": []})
        )
        return {
            "id": f"packet-{uuid4()}",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
        }


async def seed_pressure_state(engine, session: dict, *, token: str) -> None:
    """Insert complete prior exchanges and source-backed unrelated facts as setup."""

    subject = session["memory_subject"]
    conversation = session["conversation"]
    subject_id = subject["id"]
    conversation_id = conversation["id"]
    setup_run_id = str(uuid4())
    values = [f"unrelated-{index:02d}-" + "x" * 15 for index in range(48)]
    source_lines = [
        f"For topic-{index:03d} I prefer {value}." for index, value in enumerate(values)
    ]
    source_content = "\n".join(source_lines)
    source_id = str(uuid4())
    setup_conversation_id = str(uuid4())
    async with engine.begin() as connection:
        workspace_id = (
            await connection.execute(
                select(memory_subjects.c.workspace_id).where(
                    memory_subjects.c.id == subject_id
                )
            )
        ).scalar_one()
        entity_id = (
            await connection.execute(
                select(memory_entities.c.id).where(
                    memory_entities.c.subject_id == subject_id,
                    memory_entities.c.kind == "subject",
                )
            )
        ).scalar_one()
        await connection.execute(
            insert(conversations).values(
                id=setup_conversation_id,
                workspace_id=workspace_id,
                agent_definition_version_id=conversation["agent_definition_id"],
                memory_subject_id=subject_id,
                title="Synthetic fact setup source",
                purpose="evaluation",
            )
        )
        await connection.execute(
            insert(runs).values(
                id=setup_run_id,
                workspace_id=workspace_id,
                conversation_id=setup_conversation_id,
                idempotency_key=f"setup-{token}",
                request_hash=hashlib.sha256(token.encode()).hexdigest(),
                status="succeeded",
                qualification_state="unqualified",
                accepted_runtime_mode="development",
                timeout_seconds=30,
                retry_count=0,
                accepted_conversation_version=1,
                accepted_memory_generation=1,
                attempt_count=1,
            )
        )
        prior = [
            ("user", "My dog Roxy is a Husky."),
            ("assistant", "Roxy is your Husky."),
            ("user", "I am asking about Roxy again."),
            ("assistant", "I remember Roxy."),
        ]
        for sequence, (role, content) in enumerate(prior, start=1):
            await connection.execute(
                insert(messages).values(
                    id=str(uuid4()),
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    sequence=sequence,
                    role=role,
                    content=content,
                    content_sha256=hashlib.sha256(content.encode()).hexdigest(),
                    run_id=setup_run_id,
                )
            )
        await connection.execute(
            insert(messages).values(
                id=source_id,
                workspace_id=workspace_id,
                conversation_id=setup_conversation_id,
                sequence=1,
                role="user",
                content=source_content,
                content_sha256=hashlib.sha256(source_content.encode()).hexdigest(),
                run_id=setup_run_id,
            )
        )
        # A separate source conversation keeps the probe's local suffix paired.
        source_offset = 0
        for index in range(48):
            fact_id, revision_id = str(uuid4()), str(uuid4())
            value = values[index]
            source_line = source_lines[index]
            await connection.execute(
                insert(memory_facts).values(
                    id=fact_id,
                    workspace_id=workspace_id,
                    subject_id=subject_id,
                    entity_id=entity_id,
                    normalized_key=f"person.preference|subject|{index:03d}",
                    fact_type="person.preference",
                    qualifier=f"topic-{index:03d}",
                    value=value,
                    status="inactive" if index % 3 == 0 else "active",
                    assertion_schema_version=2,
                    version=1,
                )
            )
            await connection.execute(
                insert(memory_revisions).values(
                    id=revision_id,
                    fact_id=fact_id,
                    workspace_id=workspace_id,
                    subject_id=subject_id,
                    operation="add",
                    fact_version=1,
                    value=value,
                    run_id=setup_run_id,
                )
            )
            await connection.execute(
                insert(memory_revision_sources).values(
                    id=str(uuid4()),
                    revision_id=revision_id,
                    message_id=source_id,
                    start_char=source_offset,
                    end_char=source_offset + len(source_line),
                    quote=source_line,
                    message_sha256=hashlib.sha256(source_content.encode()).hexdigest(),
                    authority_role="user_assertion",
                )
            )
            await connection.execute(
                update(memory_facts)
                .where(memory_facts.c.id == fact_id)
                .values(current_revision_id=revision_id)
            )
            source_offset += len(source_line) + 1
        await connection.execute(
            update(memory_subjects)
            .where(memory_subjects.c.id == subject_id)
            .values(memory_generation=2)
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
                    f"natural-user-assertions-v2-{request.definition_key.rsplit('_', 1)[-1]}"
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
                        "current_memory_targets"
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
                        target["version"],
                    )
                    for target in json.loads(
                        item["reviewer_request"]["messages"][1]["content"]
                    )["current_memory_targets"]
                )
                for item in artifacts.values()
            ]
            assert target_views[0] == target_views[1] == target_views[2]
            assert all(
                item["generation_requests"][0]["messages"]
                == item["generation"]["messages"]
                for item in artifacts.values()
            )
            assert all(
                item["provider_request_counts"]["conversation"] == 1
                and item["provider_request_counts"]["reviewer"] == 1
                and item["provider_request_counts"]["retrieval_query"] == 1
                for item in artifacts.values()
            )
        finally:
            await engine.dispose()

    import asyncio

    asyncio.run(scenario())
