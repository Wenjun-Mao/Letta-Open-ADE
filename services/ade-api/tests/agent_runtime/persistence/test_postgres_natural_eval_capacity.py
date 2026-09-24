"""The native worker consumes the extra evaluation limits after fingerprint checks."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

import ade_api.features.agent_runtime.natural_attempt_evidence as evidence_module
from ade_api.features.agent_runtime.agent_studio_sessions import PurposeSessionService
from ade_api.features.agent_runtime.contracts import (
    AcceptTurnRequest,
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
)
from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.natural_evaluation_capacity import (
    bind_checkpoint6_capacity,
)
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.platform.settings import AdeApiSettings
from workflows.evals.character_memory_dev.natural_live_transport import (
    NaturalLiveTransport,
    RequestScope,
)
from workflows.evals.character_memory_dev.natural_live_setup import seed_live_cell
from workflows.evals.character_memory_dev.natural_memory_contract import (
    load_cases,
    load_matrix,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="isolated PostgreSQL natural evaluation database required"
)


class FakeProvider:
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
        self.calls.append("generation")
        content = (
            json.dumps({"decisions": []})
            if payload.get("response_format") is not None
            else "晚安。"
        )
        return {
            "id": f"fake-{len(self.calls)}",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
        }


def _catalog(natural_worker_support) -> dict:
    original = natural_worker_support.catalog()["items"]
    deepseek = original[0]
    deepseek["model_key"] = "deepseek::deepseek-flash"
    deepseek["source_adapter"] = "deepseek_openai"
    deepseek["deployment"]["roles"] = ["conversation", "reviewer"]
    deepseek["deployment"]["fingerprint"]["context_settings"] = {
        "total_tokens": 16384,
        "max_output_tokens": 4096,
        "max_model_requests": 6,
        "reviewer_repair_count": 0,
    }
    retriever = original[2]
    retriever["model_key"] = "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B"
    return {"items": [deepseek, retriever]}


@pytest.mark.parametrize(
    "diagnostic_reviewer_output, expected_output", [(False, 1024), (True, 4096)]
)
def test_worker_uses_role_limits_and_retains_dispatch_observations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    natural_worker_support,
    diagnostic_reviewer_output: bool,
    expected_output: int,
) -> None:
    assert DATABASE_URL is not None
    monkeypatch.setenv("ADE_NATURAL_MEMORY_CAPTURE", "1")
    monkeypatch.setenv("ADE_SOURCE_REVISION", "0" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "1" * 64)
    monkeypatch.setattr(evidence_module, "ARTIFACT_ROOT", tmp_path / "attempts")

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        settings = AdeApiSettings(
            _env_file=None,
            agent_runtime_mode="development",
            agent_runtime_enabled=True,
            database_url=DATABASE_URL,
            agent_runtime_worker_id="natural-eval-capacity-test",
        )
        catalog = _catalog(natural_worker_support)
        fake = FakeProvider(catalog)
        transport = NaturalLiveTransport(
            fake,
            capture_dir=tmp_path / "raw",
            generation_model="deepseek::deepseek-flash",
            embedding_model="dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
        )
        base_definitions = natural_worker_support.definitions(catalog)

        class BoundDefinitions:
            async def prepare(self, request, *, purpose):
                prepared = await base_definitions.prepare(request, purpose=purpose)
                return bind_checkpoint6_capacity(
                    prepared, diagnostic_reviewer_output=diagnostic_reviewer_output
                )

        sessions = PurposeSessionService(
            database=RuntimeDatabase(engine),
            definitions=BoundDefinitions(),
            purpose="evaluation",
            session_namespace="natural-eval-capacity-test",
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
        token = uuid4().hex[:12]
        try:
            session = await sessions.create(
                CreateAgentStudioSessionRequest(
                    idempotency_key=f"capacity-{token}",
                    new_definition=CreateAgentDefinitionRequest(
                        definition_key=f"capacity_{token}",
                        name="Synthetic capacity check",
                        model_key="deepseek::deepseek-flash",
                        reviewer_model_key="deepseek::deepseek-flash",
                        embedding_model_key="dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
                        tool_names=[],
                    ),
                    new_subject=CreateMemorySubjectRequest(
                        external_key=f"capacity-{token}",
                        display_name="Synthetic capacity subject",
                    ),
                )
            )
            cell = next(
                row
                for row in load_matrix()["cells"]
                if row["id"] == "mutation-scoped-addition"
            )
            branch = next(
                row
                for arc in load_cases()["arcs"]
                if arc["id"] == cell["arc"]
                for row in arc["branches"]
                if row["id"] == cell["branch"]
            )
            with transport.scope(RequestScope("setup")):
                seeded = await seed_live_cell(
                    engine,
                    session,
                    cell=cell,
                    branch=branch,
                    token=token,
                    transport=transport,
                    embedding_model="dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
                )
            assert len(seeded.fact_ids) == 1
            accepted = await service.accept_turn(
                session["conversation"]["id"],
                AcceptTurnRequest(
                    content=branch["turns"][1][2],
                    idempotency_key=f"turn-{token}",
                    timeout_seconds=180,
                    retry_count=0,
                ),
            )
            with transport.scope(RequestScope("cell")):
                assert await worker.process_once()
            run = await service.get_run(accepted["run_id"])
            assert run["status"] == "succeeded", run
            evidence = json.loads(
                (
                    tmp_path / "attempts" / accepted["run_id"] / "attempt-001.json"
                ).read_text()
            )
            assert evidence["generation"]["input_limit"] == 3072
            assert evidence["generation_requests"][0]["max_tokens"] == 512
            assert evidence["reviewer_request"]["max_tokens"] == expected_output
            assert (
                evidence["reviewer_request"]["serialized_visible_token_estimate"]
                <= 6759
            )
            assert fake.calls.count("generation") == 2
            assert fake.calls.count("embedding") == 2
            assert (
                sum(
                    group["attempted"]
                    for group in evidence["provider_request_counts"]["groups"]
                )
                == 3
            )
            assert len(list((tmp_path / "raw").glob("*.json"))) == 4
        finally:
            await engine.dispose()

    asyncio.run(scenario())
