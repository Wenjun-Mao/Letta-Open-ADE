"""H4's amended envelope carries both native arms through paired packets."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert, select

import ade_api.features.agent_runtime.natural_attempt_evidence as evidence_module
from ade_api.features.agent_runtime.agent_studio_sessions import PurposeSessionService
from ade_api.features.agent_runtime.contracts import (
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
)
from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.history_admission import HistoryProbe
from ade_api.features.agent_runtime.history_capacity import bind_history_probe_capacity
from ade_api.features.agent_runtime.history_native_rank import HISTORY_VECTOR_RECIPE
from ade_api.features.agent_runtime.natural_context import HISTORY_PROBE_POLICY
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    natural_review_request,
)
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.history import read_history_corpus
from ade_api.features.agent_runtime.persistence.memory import MemoryRepository
from ade_api.features.agent_runtime.persistence.metadata import (
    agent_definition_versions,
    conversations,
    memory_facts,
)
from ade_api.features.agent_runtime.resource_service import ResourceService
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.platform.settings import AdeApiSettings
from workflows.evals.character_memory_dev.history_h4_run import (
    QWEN_FINGERPRINT,
    _execute_cell,
)
import workflows.evals.character_memory_dev.history_h4_facts as fact_seed
from workflows.evals.character_memory_dev.history_h4_facts import (
    fixture_fact_created_at,
)
from workflows.evals.character_memory_dev.history_h4_seed import seed_history_case
from workflows.evals.character_memory_dev.natural_live_transport import (
    NaturalLiveTransport,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="isolated PostgreSQL H4 test database required"
)


class FakeProvider:
    def __init__(self, catalog: dict) -> None:
        self._catalog = catalog

    async def catalog(self, *, timeout_seconds):
        return self._catalog

    async def embeddings(self, payload, *, timeout_seconds):
        def vector(content: str) -> list[float]:
            digest = hashlib.sha256(content.encode()).digest()
            return [(digest[index % len(digest)] + 1) / 256 for index in range(1024)]

        return {
            "data": [
                {"index": index, "embedding": vector(content)}
                for index, content in enumerate(payload["input"])
            ]
        }

    async def chat_completion(self, payload, *, timeout_seconds):
        content = (
            json.dumps({"decisions": []})
            if payload.get("response_format")
            else "你说过是外婆教你包饺子。"
        )
        return {
            "id": "fake-h4",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
        }


@pytest.mark.parametrize("id_order", ["reversed", "random"])
def test_all_h4_pairs_keep_exact_base_packets_across_fact_id_orders(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    natural_worker_support,
    id_order: str,
) -> None:
    assert DATABASE_URL is not None
    monkeypatch.setenv("ADE_SOURCE_REVISION", "0" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "1" * 64)
    monkeypatch.setenv("ADE_NATURAL_MEMORY_CAPTURE", "1")
    monkeypatch.setattr(evidence_module, "ARTIFACT_ROOT", tmp_path / "attempts")

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        catalog = natural_worker_support.catalog()
        deepseek = catalog["items"][0]
        deepseek["model_key"] = "deepseek::deepseek-flash"
        deepseek["source_adapter"] = "deepseek_openai"
        deepseek["deployment"]["roles"] = ["conversation", "reviewer"]
        deepseek["deployment"]["fingerprint"]["context_settings"] = {
            "total_tokens": 16384,
            "max_output_tokens": 4096,
            "max_model_requests": 6,
            "reviewer_repair_count": 0,
        }
        retriever = catalog["items"][2]
        retriever["model_key"] = HISTORY_VECTOR_RECIPE["route"]
        retriever["deployment"]["fingerprint"].update(
            sha256=QWEN_FINGERPRINT,
            artifact_reference=HISTORY_VECTOR_RECIPE["artifact_reference"],
            artifact_revision=HISTORY_VECTOR_RECIPE["artifact_revision"],
            sampling_settings={"dimensions": 1024},
        )
        catalog = {"items": [deepseek, retriever]}
        base = natural_worker_support.definitions(catalog)

        class BoundDefinitions:
            async def prepare(self, request, *, purpose):
                prepared = await base.prepare(request, purpose=purpose)
                prepared["memory_policy_version"] = HISTORY_PROBE_POLICY
                return bind_history_probe_capacity(prepared)

        settings = AdeApiSettings(
            _env_file=None,
            agent_runtime_mode="development",
            agent_runtime_enabled=True,
            database_url=DATABASE_URL,
            agent_runtime_worker_id="h4-fake-pair",
        )
        transport = NaturalLiveTransport(
            FakeProvider(catalog),
            capture_dir=tmp_path / "raw",
            generation_model="deepseek::deepseek-flash",
            embedding_model=HISTORY_VECTOR_RECIPE["route"],
        )
        database = RuntimeDatabase(engine)
        sessions = PurposeSessionService(
            database=database,
            definitions=BoundDefinitions(),
            purpose="evaluation",
            session_namespace="h4-fake-pair",
        )
        service = RunService(
            database=database,
            settings=settings,
            router_transport=transport,
            worker_health=natural_worker_support.ready_worker(),
        )
        resources = ResourceService(database)
        workers = {
            arm: AgentRuntimeWorker(
                engine=engine,
                settings=settings,
                transport=transport,
                history_probe=HistoryProbe(
                    arm=arm,
                    **(
                        {
                            "ranking_recipe": "probe_local_qwen_cosine",
                            "expected_embedding_fingerprint": QWEN_FINGERPRINT,
                        }
                        if arm == "automatic_history"
                        else {}
                    ),
                ),
            )
            for arm in ("empty_history", "automatic_history")
        }
        cases = json.loads(
            Path(
                "workflows/evals/character_memory_dev/fixtures/history_recall/cases.json"
            ).read_text()
        )["cases"]
        run_prefix = uuid4().int & (((1 << 64) - 1) << 64)
        try:
            checked = []
            for case_index, case in enumerate(cases):
                results = []
                for arm_index, arm in enumerate(workers):
                    sequence = iter(range(1, 1000))
                    base_id = (
                        run_prefix + ((case_index + 1) << 32) + ((arm_index + 1) << 24)
                    )

                    def fixture_uuid() -> UUID:
                        offset = next(sequence)
                        return UUID(
                            int=base_id + (offset if arm_index == 0 else 1000 - offset)
                        )

                    with monkeypatch.context() as patch:
                        if id_order == "reversed":
                            patch.setattr(fact_seed, "uuid4", fixture_uuid)
                        result = await _execute_cell(
                            name=case["id"],
                            case=case,
                            target=case,
                            arm=arm,
                            sessions=sessions,
                            service=service,
                            resources=resources,
                            workers=workers,
                            engine=engine,
                            transport=transport,
                            output=tmp_path,
                            index=case_index * 2 + arm_index,
                        )
                    results.append(result)
                assert [result["status"] for result in results] == ["observed"] * 2, [
                    (case["id"], result.get("failure")) for result in results
                ]
                assert all(
                    result["target"]["status"] == "committed" for result in results
                )
                assert all(
                    result["target"]["base_packet"] is not None for result in results
                )
                assert (
                    results[0]["target"]["base_packet"]
                    == results[1]["target"]["base_packet"]
                ), case["id"]
                if len(case["facts"]) > 1:
                    fact_keys = [fact["id"] for fact in case["facts"]]
                    if id_order == "reversed":
                        first_ids = results[0]["setup"]["fact_ids"]
                        second_ids = results[1]["setup"]["fact_ids"]
                        assert (
                            UUID(first_ids[fact_keys[0]]).int
                            < UUID(first_ids[fact_keys[1]]).int
                        )
                        assert (
                            UUID(second_ids[fact_keys[0]]).int
                            > UUID(second_ids[fact_keys[1]]).int
                        )
                    async with engine.connect() as connection:
                        for result in results:
                            read = await MemoryRepository(connection).list_facts(
                                result["session"]["subject_id"]
                            )
                            assert [str(item["id"]) for item in read] == [
                                result["setup"]["fact_ids"][key] for key in fact_keys
                            ]
                if case["id"] == "removed_acknowledgment":
                    assert all(
                        not result["target"]["base_packet"]["reviewer_packet"][
                            "targets"
                        ]
                        for result in results
                    )
                if case["id"] == "h_only_referent":
                    assert all(
                        len(
                            result["target"]["base_packet"]["reviewer_packet"][
                                "related_identities"
                            ]
                        )
                        == 2
                        for result in results
                    )
                for result in results:
                    attempt = json.loads(
                        Path(result["target"]["attempt_artifact"]).read_text()
                    )
                    assert attempt["generation"]["input_limit"] == 11213
                    assert attempt["reviewer_request"]["max_tokens"] == 4096
                    assert (
                        attempt["reviewer_request"]["serialized_visible_token_estimate"]
                        <= 11469
                    )
                    assert any(
                        receipt["kind"] == "generation"
                        for receipt in result["target"]["provider_captures"]
                    )
                checked.append(case["id"])
            assert len(checked) == 11
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_fixture_timestamp_breaks_a_legitimate_source_time_tie(
    seed_m2_memory_resources,
) -> None:
    assert DATABASE_URL is not None
    exchange = {"same": {"assistant_at": "2026-09-01T12:01:01+00:00"}}
    transition = {"source": "same:user"}
    first = fixture_fact_created_at(transition, exchange, 0)
    second = fixture_fact_created_at(transition, exchange, 1)
    assert first < second
    assert (second - first).total_seconds() == 0.000001

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                high_id, low_id = (
                    str(UUID(int=uuid4().int | (1 << 127))),
                    str(UUID(int=uuid4().int & ((1 << 127) - 1))),
                )
                for fact_id, fact_type, created_at in (
                    (high_id, "person.current_location", first),
                    (low_id, "person.preference", second),
                ):
                    await connection.execute(
                        insert(memory_facts).values(
                            id=fact_id,
                            workspace_id=ids["workspace"],
                            subject_id=ids["subject_one"],
                            entity_id=ids["subject_one"],
                            normalized_key=fact_type,
                            fact_type=fact_type,
                            qualifier="drink"
                            if fact_type == "person.preference"
                            else None,
                            value="北京"
                            if fact_type == "person.current_location"
                            else "咖啡",
                            status="inactive",
                            version=1,
                            created_at=created_at,
                        )
                    )
            async with engine.connect() as connection:
                read = await MemoryRepository(connection).list_facts(ids["subject_one"])
            assert [str(fact["id"]) for fact in read] == [high_id, low_id]
            current = {"id": str(uuid4()), "role": "user", "content": "还成立吗？"}
            request = natural_review_request(
                model_key="deepseek::deepseek-flash",
                provider_adapter="deepseek_openai",
                current_user_message=current,
                source_messages=[current],
                facts=read,
                entities=[{"id": ids["subject_one"], "kind": "subject", "label": "H4"}],
                candidate_reply="不确定。",
                history_capable=True,
            )
            packet = json.loads(request["messages"][1]["content"])
            assert [target["fact_type"] for target in packet["targets"]] == [
                "person.current_location",
                "person.preference",
            ]
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_all_frozen_setups_have_exact_native_history_scope(
    natural_worker_support,
) -> None:
    assert DATABASE_URL is not None

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        catalog = natural_worker_support.catalog()
        catalog["items"][0]["model_key"] = "deepseek::deepseek-flash"
        catalog["items"][0]["deployment"]["roles"] = ["conversation", "reviewer"]
        qwen = catalog["items"][2]
        qwen["model_key"] = HISTORY_VECTOR_RECIPE["route"]
        qwen["deployment"]["fingerprint"].update(
            sha256=QWEN_FINGERPRINT,
            artifact_reference=HISTORY_VECTOR_RECIPE["artifact_reference"],
            artifact_revision=HISTORY_VECTOR_RECIPE["artifact_revision"],
            sampling_settings={"dimensions": 1024},
        )
        catalog["items"] = [catalog["items"][0], qwen]
        base = natural_worker_support.definitions(catalog)

        class BoundDefinitions:
            async def prepare(self, request, *, purpose):
                prepared = await base.prepare(request, purpose=purpose)
                prepared["memory_policy_version"] = HISTORY_PROBE_POLICY
                return prepared

        sessions = PurposeSessionService(
            database=RuntimeDatabase(engine),
            definitions=BoundDefinitions(),
            purpose="evaluation",
            session_namespace=f"h4-scope-{uuid4().hex}",
        )
        cases = json.loads(
            Path(
                "workflows/evals/character_memory_dev/fixtures/history_recall/cases.json"
            ).read_text()
        )["cases"]
        try:
            for index, case in enumerate(cases):
                token = uuid4().hex[:12]
                session = await sessions.create(
                    CreateAgentStudioSessionRequest(
                        idempotency_key=f"h4-scope-{token}",
                        title=f"H4 scope {case['id']}",
                        new_definition=CreateAgentDefinitionRequest(
                            definition_key=f"h4scope_{index}_{token}",
                            name="H4 scope",
                            model_key="deepseek::deepseek-flash",
                            reviewer_model_key="deepseek::deepseek-flash",
                            embedding_model_key=HISTORY_VECTOR_RECIPE["route"],
                            tool_names=["search_memory"],
                        ),
                        new_subject=CreateMemorySubjectRequest(
                            external_key=f"h4scope-{token}",
                            display_name="H4 scope",
                        ),
                    )
                )
                seeded = await seed_history_case(
                    engine,
                    session,
                    case=case,
                    token=token,
                    transport=FakeProvider(catalog),
                    embedding_model=HISTORY_VECTOR_RECIPE["route"],
                )
                async with engine.connect() as connection:
                    target = (
                        await connection.execute(
                            select(
                                conversations.c.workspace_id,
                                conversations.c.memory_subject_id,
                                agent_definition_versions.c.agent_definition_id,
                            )
                            .join(
                                agent_definition_versions,
                                conversations.c.agent_definition_version_id
                                == agent_definition_versions.c.id,
                            )
                            .where(conversations.c.id == seeded.target_conversation_id)
                        )
                    ).one()
                    corpus = await read_history_corpus(
                        connection,
                        workspace_id=str(target[0]),
                        subject_id=str(target[1]),
                        purpose="evaluation",
                        definition_root_id=str(target[2]),
                        current_run_id=str(uuid4()),
                    )
                expected = 0 if case["id"] == "isolation" else len(case["setup"])
                assert len(corpus["exchanges"]) == expected, case["id"]
                assert corpus["omitted"] == {
                    "capacity_at_least": 0,
                    "content": 0,
                    "annotation": 0,
                }
        finally:
            await engine.dispose()

    asyncio.run(scenario())
