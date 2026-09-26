"""Chronological fresh-fixture mechanics against disposable PostgreSQL."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path

import pytest
from sqlalchemy import select

import ade_api.features.agent_runtime.natural_attempt_evidence as evidence_module
from ade_api.features.agent_runtime.agent_studio_sessions import PurposeSessionService
from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.history_admission import HistoryProbe
from ade_api.features.agent_runtime.history_capacity import bind_history_probe_capacity
from ade_api.features.agent_runtime.history_native_rank import HISTORY_VECTOR_RECIPE
from ade_api.features.agent_runtime.natural_context import HISTORY_PROBE_POLICY
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.metadata import conversations, messages
from ade_api.features.agent_runtime.resource_service import ResourceService
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.platform.settings import AdeApiSettings
from workflows.evals.character_memory_dev.history_fresh_conversations import (
    execute_fresh_trajectory,
    frozen_fresh_schedule,
)
from workflows.evals.character_memory_dev.history_h4_run import QWEN_FINGERPRINT
from workflows.evals.character_memory_dev.history_target_diagnostic_run import (
    GENERATION_BINDING,
    fact_state,
)
from workflows.evals.character_memory_dev.natural_live_results import sha256_file
from workflows.evals.character_memory_dev.natural_live_transport import (
    NaturalLiveTransport,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="exclusively owned disposable PostgreSQL required"
)


class ScriptedProvider:
    def __init__(self, catalog: dict) -> None:
        self.catalog_result = catalog
        self.assistant_number = 0

    async def catalog(self, *, timeout_seconds):
        return self.catalog_result

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
        if payload.get("response_format"):
            packet = json.loads(payload["messages"][1]["content"])
            current = packet["current_user"]["content"]
            decisions = []
            if current == "刚搬到温哥华了，我现在住在这边。":
                decisions = [
                    {
                        "kind": "subject_add",
                        "fact_type": "person.current_location",
                        "qualifier": None,
                        "value": "温哥华",
                        "evidence": {"mode": "direct", "current_quote": current},
                    }
                ]
            elif current.startswith("跟你更新一下，我现在搬到渥太华了"):
                target = next(
                    item["handle"]
                    for item in packet["targets"]
                    if item["fact_type"] == "person.current_location"
                )
                decisions = [
                    {
                        "kind": "revise",
                        "target": target,
                        "reason": "supersede",
                        "value": "渥太华",
                        "evidence": {"mode": "direct", "current_quote": current},
                    }
                ]
            elif current == "我最喜欢听的音乐是爵士乐。":
                decisions = [
                    {
                        "kind": "subject_add",
                        "fact_type": "person.preference",
                        "qualifier": "music",
                        "value": "爵士乐",
                        "evidence": {"mode": "direct", "current_quote": current},
                    }
                ]
            content = json.dumps({"decisions": decisions}, ensure_ascii=False)
        else:
            self.assistant_number += 1
            content = f"native fake assistant {self.assistant_number}"
        return {
            "id": "scripted-fresh-conversations",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
        }


def test_fresh_sessions_archive_and_actual_assistant_history(
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
        chat = catalog["items"][0]
        chat["model_key"] = "deepseek::deepseek-flash"
        chat["source_adapter"] = "deepseek_openai"
        chat["deployment"]["roles"] = ["conversation", "reviewer"]
        chat["deployment"]["fingerprint"]["context_settings"] = {
            "total_tokens": 16384,
            "max_output_tokens": 4096,
            "max_model_requests": 6,
            "reviewer_repair_count": 0,
        }
        embedding = catalog["items"][2]
        embedding["model_key"] = HISTORY_VECTOR_RECIPE["route"]
        embedding["deployment"]["fingerprint"].update(
            sha256=QWEN_FINGERPRINT,
            artifact_reference=HISTORY_VECTOR_RECIPE["artifact_reference"],
            artifact_revision=HISTORY_VECTOR_RECIPE["artifact_revision"],
            sampling_settings={"dimensions": 1024},
        )
        catalog = {"items": [chat, embedding]}
        definitions = natural_worker_support.definitions(catalog)

        class BoundDefinitions:
            async def prepare(self, request, *, purpose):
                prepared = await definitions.prepare(request, purpose=purpose)
                prepared["memory_policy_version"] = HISTORY_PROBE_POLICY
                return bind_history_probe_capacity(prepared)

        settings = AdeApiSettings(
            _env_file=None,
            agent_runtime_mode="development",
            agent_runtime_enabled=True,
            database_url=DATABASE_URL,
            agent_runtime_worker_id="fresh-conversations-fake",
        )
        transport = NaturalLiveTransport(
            ScriptedProvider(catalog),
            capture_dir=tmp_path / "raw",
            generation_model="deepseek::deepseek-flash",
            embedding_model=HISTORY_VECTOR_RECIPE["route"],
        )
        database = RuntimeDatabase(engine)
        sessions = PurposeSessionService(
            database=database,
            definitions=BoundDefinitions(),
            purpose="evaluation",
            session_namespace="fresh-conversations-fake",
        )
        service = RunService(
            database=database,
            settings=settings,
            router_transport=transport,
            worker_health=natural_worker_support.ready_worker(),
        )
        resources = ResourceService(database)
        worker = AgentRuntimeWorker(
            engine=engine,
            settings=settings,
            transport=transport,
            history_probe=HistoryProbe(
                arm="automatic_history",
                ranking_recipe="probe_local_qwen_cosine",
                expected_embedding_fingerprint=QWEN_FINGERPRINT,
            ),
        )
        binding = json.loads(GENERATION_BINDING.read_text())
        schedule = frozen_fresh_schedule(
            generation_binding_sha256=sha256_file(GENERATION_BINDING),
            per_turn=binding["per_turn"],
        )
        try:
            results = [
                await execute_fresh_trajectory(
                    trajectory=trajectory,
                    index=index,
                    sessions=sessions,
                    service=service,
                    resources=resources,
                    worker=worker,
                    engine=engine,
                    transport=transport,
                    output=tmp_path,
                    prompt_key="chat_v20260926",
                )
                for index, trajectory in enumerate(schedule["trajectories"])
            ]
            assert [len(item["turns"]) for item in results] == [3, 4, 2, 3]
            assert all(item["status"] == "observed" for item in results)
            assert len({item["subjects"]["primary"] for item in results}) == 4
            assert (
                results[3]["subjects"]["primary"] != results[3]["subjects"]["isolated"]
            )
            assert (
                results[0]["chats"]["source"]["conversation_id"]
                != results[0]["chats"]["recall"]["conversation_id"]
            )
            assert results[0]["turns"][1]["after_facts"][0]["value"] == "渥太华"
            assert all(
                turn["observed_delta"]["revision_count"] == 0
                for turn in results[1]["turns"]
            )
            assert all(
                turn["observed_delta"]["revision_count"] == 0
                for turn in results[2]["turns"]
            )
            assert results[3]["turns"][2]["after_facts"] == []
            for result in results:
                for subject_key, subject_id in result["subjects"].items():
                    last_turn = next(
                        turn
                        for turn in reversed(result["turns"])
                        if turn["subject"] == subject_key
                    )
                    assert (
                        await fact_state(engine, subject_id) == last_turn["after_facts"]
                    )

            source_chat = results[2]["chats"]["source"]["conversation_id"]
            async with engine.connect() as connection:
                archived_at = await connection.scalar(
                    select(conversations.c.archived_at).where(
                        conversations.c.id == source_chat
                    )
                )
                source_messages = (
                    await connection.execute(
                        select(messages.c.role, messages.c.content)
                        .where(messages.c.conversation_id == source_chat)
                        .order_by(messages.c.sequence)
                    )
                ).all()
            assert archived_at is not None
            assert [row.role for row in source_messages] == ["user", "assistant"]
            assert (
                source_messages[1].content == results[2]["turns"][0]["delivered_reply"]
            )
            assert "native fake assistant" in source_messages[1].content
            assert any(
                message["content"] == source_messages[1].content
                for exchange in results[2]["turns"][1]["admitted_history"]
                for message in exchange["messages"]
            )
        finally:
            await engine.dispose()

    asyncio.run(scenario())
