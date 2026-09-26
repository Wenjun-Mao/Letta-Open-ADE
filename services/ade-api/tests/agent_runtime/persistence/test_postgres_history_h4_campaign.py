"""H4's frozen reviewer envelope rejects both native arms before generation."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

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
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.history import read_history_corpus
from ade_api.features.agent_runtime.persistence.metadata import (
    agent_definition_versions,
    conversations,
)
from ade_api.features.agent_runtime.resource_service import ResourceService
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.platform.settings import AdeApiSettings
from workflows.evals.character_memory_dev.history_h4_run import (
    QWEN_FINGERPRINT,
    _execute_cell,
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
        return {
            "data": [
                {"index": index, "embedding": [1.0] * 1024}
                for index, _ in enumerate(payload["input"])
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


def test_h4_pair_replays_archived_version_and_compares_base_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, natural_worker_support
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
        case = next(
            item
            for item in json.loads(
                Path(
                    "workflows/evals/character_memory_dev/fixtures/history_recall/cases.json"
                ).read_text()
            )["cases"]
            if item["id"] == "archived_version_recall"
        )
        try:
            results = [
                await _execute_cell(
                    name="archived_version_recall",
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
                    index=index,
                )
                for index, arm in enumerate(workers)
            ]
            assert [result["status"] for result in results] == ["rejected"] * 2, [
                result.get("failure") for result in results
            ]
            assert all(result["target"]["status"] == "rejected" for result in results)
            assert all(
                result["target"]["run"]["status"] == "failed" for result in results
            )
            assert all(result["target"]["base_packet"] is None for result in results)
            assert all(
                not any(
                    receipt["kind"] == "generation"
                    for receipt in result["target"]["provider_captures"]
                )
                for result in results
            )
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
