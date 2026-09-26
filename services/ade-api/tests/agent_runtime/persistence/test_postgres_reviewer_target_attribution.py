"""Native mechanics for the seven-turn target-attribution diagnostic shape."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from copy import deepcopy
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
from ade_api.features.agent_runtime.persistence.metadata import memory_facts
from ade_api.features.agent_runtime.resource_service import ResourceService
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.platform.settings import AdeApiSettings
from workflows.evals.character_memory_dev.history_h4_run import (
    QWEN_FINGERPRINT,
    _execute_cell,
)
from workflows.evals.character_memory_dev.natural_live_transport import (
    NaturalLiveTransport,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="isolated PostgreSQL target-attribution database required"
)


class ScriptedProvider:
    """Emit planned decisions so the native persistence path can be checked."""

    def __init__(self, catalog: dict) -> None:
        self.catalog_result = catalog

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
            if current == "它现在叫小黑。":
                decisions = [
                    {"kind": "defer", "current_quote": current, "reason": "unresolved"}
                ]
            elif "Roxy" in current or "Nini" in current:
                old_name = "Roxy" if "Roxy" in current else "Nini"
                target = next(
                    item["handle"]
                    for item in packet["targets"]
                    if item["fact_type"] == "pet.name" and item["value"] == old_name
                )
                decisions = [
                    {
                        "kind": "revise",
                        "target": target,
                        "reason": "supersede",
                        "value": "小黑",
                        "evidence": {"mode": "direct", "current_quote": current},
                    }
                ]
            elif current == "我现在又喜欢茉莉花茶了。":
                decisions = [
                    {
                        "kind": "subject_add",
                        "fact_type": "person.preference",
                        "qualifier": "drink",
                        "value": "现在喜欢茉莉花茶",
                        "evidence": {"mode": "direct", "current_quote": current},
                    }
                ]
            else:
                decisions = []
            content = json.dumps({"decisions": decisions}, ensure_ascii=False)
        else:
            content = (
                "你以前提过茉莉花茶。"
                if "你还记得我以前提过什么茶吗" in str(payload)
                else "好的，请说清是哪只。"
            )
        return {
            "id": "scripted-target-attribution",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
        }


def test_native_target_attribution_and_removed_jasmine_trajectories(
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
            agent_runtime_worker_id="target-attribution-fake",
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
            session_namespace="target-attribution-fake",
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
        cases = {
            case["id"]: case
            for case in json.loads(
                Path(
                    "workflows/evals/character_memory_dev/fixtures/history_recall/cases.json"
                ).read_text()
            )["cases"]
        }
        try:
            for index, old_name in enumerate(("Roxy", "Nini")):
                case = deepcopy(cases["h_only_referent"])
                case["followup"]["user"] = (
                    f"我是说以前那只叫 {old_name} 的"
                    f"{'黑' if old_name == 'Roxy' else '白'}狗，现在叫小黑。"
                )
                result = await _execute_cell(
                    name=f"ambiguous-{old_name.lower()}",
                    case=case,
                    target=case,
                    arm="automatic_history",
                    sessions=sessions,
                    service=service,
                    resources=resources,
                    workers={"automatic_history": worker},
                    engine=engine,
                    transport=transport,
                    output=tmp_path,
                    index=index,
                )
                assert result["status"] == "observed", result.get("failure")
                target = result["target"]
                followup = result["followup"]
                assert target["observed_delta"]["revision_count"] == 0
                assert target["observed_delta"]["generation_advance"] == 0
                target_facts = {fact["id"]: fact for fact in target["memory"]["facts"]}
                assert (
                    target_facts[result["setup"]["fact_ids"]["roxy_name"]]["value"]
                    == "Roxy"
                )
                assert (
                    target_facts[result["setup"]["fact_ids"]["nini_name"]]["value"]
                    == "Nini"
                )
                assert followup["status"] == "committed"
                revisions = followup["observed_delta"]["run_revisions"]
                assert len(revisions) == 1
                assert (
                    revisions[0]["fact_id"]
                    == result["setup"]["fact_ids"][
                        "roxy_name" if old_name == "Roxy" else "nini_name"
                    ]
                )
                assert revisions[0]["operation"] == "revise"
                assert revisions[0]["value"] == "小黑"
                assert any(
                    source["authority_role"] == "user_assertion"
                    and source["quote"] == case["followup"]["user"]
                    for source in revisions[0]["sources"]
                )
                by_id = {fact["id"]: fact for fact in followup["memory"]["facts"]}
                other = "nini_name" if old_name == "Roxy" else "roxy_name"
                assert by_id[result["setup"]["fact_ids"][other]]["value"] == (
                    "Nini" if old_name == "Roxy" else "Roxy"
                )

            explicit = deepcopy(cases["h_only_referent"])
            explicit["target"]["user"] = "Roxy 现在叫小黑。"
            explicit.pop("followup")
            result = await _execute_cell(
                name="explicit-roxy",
                case=explicit,
                target=explicit,
                arm="automatic_history",
                sessions=sessions,
                service=service,
                resources=resources,
                workers={"automatic_history": worker},
                engine=engine,
                transport=transport,
                output=tmp_path,
                index=2,
            )
            assert result["status"] == "observed", result.get("failure")
            revisions = result["target"]["observed_delta"]["run_revisions"]
            assert len(revisions) == 1
            assert revisions[0]["fact_id"] == result["setup"]["fact_ids"]["roxy_name"]
            assert revisions[0]["value"] == "小黑"
            explicit_facts = {
                fact["id"]: fact for fact in result["target"]["memory"]["facts"]
            }
            assert (
                explicit_facts[result["setup"]["fact_ids"]["nini_name"]]["value"]
                == "Nini"
            )

            jasmine = deepcopy(cases["removed_acknowledgment"])
            result = await _execute_cell(
                name="removed-jasmine",
                case=jasmine,
                target=jasmine,
                arm="automatic_history",
                sessions=sessions,
                service=service,
                resources=resources,
                workers={"automatic_history": worker},
                engine=engine,
                transport=transport,
                output=tmp_path,
                index=3,
            )
            assert result["status"] == "observed", result.get("failure")
            assert result["target"]["observed_delta"]["revision_count"] == 0
            target_attempt = json.loads(
                Path(result["target"]["attempt_artifact"]).read_text()
            )
            assert "以前提过茉莉花茶" in target_attempt["candidate_visible_reply"]
            reviewer_packet = json.loads(
                target_attempt["reviewer_request"]["messages"][1]["content"]
            )
            assert any(
                "我以前喜欢茉莉花茶" in message["content"]
                for exchange in reviewer_packet["history"]
                for message in exchange["messages"]
            )
            revisions = result["followup"]["observed_delta"]["run_revisions"]
            assert len(revisions) == 1
            assert revisions[0]["operation"] == "add"
            assert revisions[0]["fact_type"] == "person.preference"
            assert (
                revisions[0]["fact_id"]
                != result["setup"]["fact_ids"]["jasmine_preference"]
            )
            assert revisions[0]["value"] == "现在喜欢茉莉花茶"
            assert revisions[0]["sources"] == [
                {
                    "quote": jasmine["followup"]["user"],
                    "authority_role": "user_assertion",
                }
            ]
            async with engine.connect() as connection:
                old_status = await connection.scalar(
                    select(memory_facts.c.status).where(
                        memory_facts.c.id
                        == result["setup"]["fact_ids"]["jasmine_preference"]
                    )
                )
            assert old_status == "forgotten"
        finally:
            await engine.dispose()

    asyncio.run(scenario())
