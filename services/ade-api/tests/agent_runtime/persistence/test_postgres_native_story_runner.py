"""Native runner mechanics through real HTTP handlers/PG with scripted providers.

Every reply, vector and annotation here is a test fixture, not native quality.
"""

import asyncio
import os
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from ade_api.features.agent_runtime.api import router as runtime_router
from ade_api.features.agent_runtime.application import AgentRuntimeApplication
from ade_api.features.agent_runtime.dependencies import get_agent_runtime_service
from ade_api.features.agent_runtime.history_admission import HistoryProbe
from ade_api.features.agent_runtime.history_trial import TRIAL_QWEN_FINGERPRINT
from ade_api.features.agent_runtime.history_trial_api import router as trial_router
import ade_api.features.agent_runtime.natural_attempt_evidence as evidence_module
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.features.prompt_center import build_prompt_template_reader
from ade_api.platform.auth import require_operator, require_reader
from ade_api.platform.project_paths import PROJECT_ROOT
from ade_api.platform.settings import AdeApiSettings
from workflows.evals.character_memory_dev.story_continuity import native_sequence
from workflows.evals.character_memory_dev.story_continuity.native_artifacts import (
    annotate,
    read,
    write_once,
)
from workflows.evals.character_memory_dev.story_continuity.native_transport import (
    NativeADE,
)
from workflows.evals.character_memory_dev.story_continuity.schedule import (
    frozen_schedule,
)
from .story_continuity_support import ScriptedRouter, require_owned_database

DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="fresh disposable PostgreSQL required"
)


def test_native_runner_scripted_full_sequence(
    tmp_path, monkeypatch, natural_worker_support
):
    assert DATABASE_URL
    require_owned_database(DATABASE_URL)
    monkeypatch.setenv("ADE_SOURCE_REVISION", "0" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "1" * 64)
    monkeypatch.setenv("ADE_NATURAL_MEMORY_CAPTURE", "1")
    monkeypatch.setattr(
        evidence_module, "ARTIFACT_ROOT", tmp_path / "natural-memory-attempts"
    )
    monkeypatch.setattr(native_sequence, "OUTPUTS", tmp_path)
    monkeypatch.setattr(native_sequence, "check_preparation", lambda *_: {})

    async def scenario():
        engine = create_persistence_engine(DATABASE_URL)
        settings = AdeApiSettings(
            _env_file=None,
            database_url=DATABASE_URL,
            agent_runtime_mode="development",
            agent_runtime_enabled=True,
        )
        fake = ScriptedRouter()
        registry = build_prompt_template_reader(
            PROJECT_ROOT,
            persona_db_path=tmp_path / "personas.sqlite3",
            persona_seed_jsonl_path=PROJECT_ROOT / "content/personas/personas.jsonl",
        )
        service = AgentRuntimeApplication(
            engine=engine,
            settings=settings,
            prompt_registry=registry,
            router_transport=fake,
        )
        service.runs.worker_health = natural_worker_support.ready_worker()
        app = FastAPI()
        app.include_router(runtime_router)
        app.include_router(trial_router)
        app.dependency_overrides[get_agent_runtime_service] = lambda: service
        app.dependency_overrides[require_operator] = lambda: None
        app.dependency_overrides[require_reader] = lambda: None
        worker = AgentRuntimeWorker(
            engine=engine,
            settings=settings,
            transport=fake,
            history_probe=HistoryProbe(
                arm="automatic_history",
                ranking_recipe="probe_local_qwen_cosine_v2",
                expected_embedding_fingerprint=TRIAL_QWEN_FINGERPRINT,
            ),
        )
        schedule = frozen_schedule()
        story, detail = (
            schedule["controls"][0]["reply"],
            schedule["controls"][2]["reply"],
        )
        replies = [
            story,
            "Fine.",
            detail,
            schedule["controls"][6]["reply"],
            story,
            "It was a solo event.",
            story,
            story,
            "No prior story with you.",
            "Not my experience.",
        ]

        class ScriptedWorkerHTTP(NativeADE):
            count = 0

            async def request(self, method, path, body=None):
                is_turn = method == "POST" and path.endswith("/turns")
                if is_turn:
                    fake.script(replies[self.count], reject=False)
                result = await super().request(method, path, body)
                if is_turn:
                    assert await worker.process_once()
                    fake.bind_document(
                        body["content"],
                        replies[self.count],
                        preferred=self.count in {0, 2},
                    )
                    self.count += 1
                return result

        api = ScriptedWorkerHTTP(
            "http://127.0.0.1:9000",
            "synthetic-test",
            transport=httpx.ASGITransport(app=app),
        )
        write_once(tmp_path / "database.json", {"token": uuid4().hex})
        try:
            for phase, frontier in enumerate([1, 3, None], start=1):
                launch = tmp_path / f"launch-{phase}"
                launch.mkdir()
                result = await native_sequence.run_sequence(api, tmp_path, launch)
                if frontier is None:
                    assert result["status"] == "sequence_complete", result
                    break
                assert result["status"] == "human_annotation_required", result
                assert result["turn"] == frontier
                assert api.count == frontier
                annotate(
                    tmp_path,
                    frontier,
                    {
                        "reviewer_kind": "human",
                        "reviewer": "scripted annotation fixture, not an actual human review",
                        "usable": True,
                        "quotes": [story if frontier == 1 else detail],
                        "rationale": "Scripted mechanics control only.",
                        "replacement_suggestion": "a different shared event"
                        if frontier == 1
                        else None,
                    },
                )
            assert api.count == 10
            assert all(
                read(tmp_path / f"turn-{n:02d}.json")["validation"]["disposition"]
                == "committed"
                for n in range(1, 11)
            )
            origin_id = read(tmp_path / "turn-01.json")["readback"]["run"]["id"]
            assert (
                origin_id
                in read(tmp_path / "turn-07.json")["validation"]["admitted_run_ids"]
            )
            assert read(tmp_path / "archive-origin.json")["conversation"]["archived_at"]
            assert read(tmp_path / "archive-callback.json")["conversation"][
                "archived_at"
            ]
            assert read(tmp_path / "version-02.json")["version"] == 2
            for number in [9, 10]:
                assert (
                    read(tmp_path / f"turn-{number:02d}.json")["validation"][
                        "admitted_run_ids"
                    ]
                    == []
                )
        finally:
            await api.close()
            await engine.dispose()

    asyncio.run(scenario())
