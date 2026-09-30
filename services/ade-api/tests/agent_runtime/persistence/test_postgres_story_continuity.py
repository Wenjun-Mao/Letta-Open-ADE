"""Real ADE HTTP/worker/persistence sequence; scripted router, never model quality."""

import asyncio
import json
import os
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import insert, select

from ade_api.features.agent_runtime.api import router as runtime_router
from ade_api.features.agent_runtime.application import AgentRuntimeApplication
from ade_api.features.agent_runtime.database_boundary import DEFAULT_WORKSPACE_ID
from ade_api.features.agent_runtime.dependencies import get_agent_runtime_service
from ade_api.features.agent_runtime.history_admission import HistoryProbe
from ade_api.features.agent_runtime.history_trial import (
    TRIAL_QWEN_FINGERPRINT,
    trial_definition_request,
)
from ade_api.features.agent_runtime.history_trial_api import router as trial_router
import ade_api.features.agent_runtime.natural_attempt_evidence as evidence_module
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.metadata import memory_entities, runs
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.features.prompt_center import build_prompt_template_reader
from ade_api.platform.auth import require_operator, require_reader
from ade_api.platform.project_paths import PROJECT_ROOT
from ade_api.platform.settings import AdeApiSettings
from workflows.evals.character_memory_dev.story_continuity.api import OfflineADE
from workflows.evals.character_memory_dev.story_continuity.evidence import (
    checked_capture,
    validate_turn,
)
from workflows.evals.character_memory_dev.story_continuity.schedule import (
    dependency_status,
    digest,
    frozen_schedule,
    prompt_for,
)
from .story_continuity_support import ScriptedRouter, full_state, require_owned_database
from .story_version_support import create_checked_version

DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="fresh disposable PostgreSQL required"
)


@pytest.mark.parametrize("reject_origin", [False, True])
def test_scripted_story_sequence(
    tmp_path, monkeypatch, natural_worker_support, reject_origin
):
    assert DATABASE_URL
    require_owned_database(DATABASE_URL)
    monkeypatch.setenv("ADE_SOURCE_REVISION", "0" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "1" * 64)
    monkeypatch.setenv("ADE_NATURAL_MEMORY_CAPTURE", "1")
    monkeypatch.setattr(evidence_module, "ARTIFACT_ROOT", tmp_path / "captures")

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
        api = OfflineADE(httpx.ASGITransport(app=app))
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
        token = uuid4().hex[:12]
        schedule = frozen_schedule()
        story = schedule["controls"][0]["reply"]
        replies = [
            story,
            "散步也不错。",
            schedule["controls"][2]["reply"],
            schedule["controls"][6]["reply"],
            story,
            "那次是我自己去的。",
            story,
            story,
            "我不记得跟你讲过这件事。",
            "我没有这段经历。",
        ]
        sessions, subjects, outcomes, ledger = {}, {}, {}, {}
        origin_run_id = None
        definition = trial_definition_request().model_dump(mode="json")
        definition.update(definition_key=f"pc11_{token}", name="PC11 offline")
        primary = None
        try:
            async with engine.connect() as connection:
                assert not list(
                    (
                        await connection.execute(
                            select(runs.c.id).where(
                                runs.c.status.in_(["pending", "running"])
                            )
                        )
                    ).scalars()
                ), "Worker requires exclusively idle owned DB"
            for turn in schedule["turns"]:
                number = turn["id"]
                if dependency_status(turn, outcomes) == "unassessable_dependency":
                    outcomes[number] = {"disposition": "unassessable_dependency"}
                    continue
                for name in turn.get("archive_before", []):
                    session = sessions[name]
                    archived = await api.archive(session["conversation"]["id"])
                    assert archived["conversation"]["archived_at"] is not None
                    for source in ledger.values():
                        if source["conversation_id"] == session["conversation"]["id"]:
                            source["archived"] = True
                if turn["chat"] not in sessions:
                    request = {"idempotency_key": f"pc11-{token}-{number}"}
                    if primary is None or number in {7, 10}:
                        changed = dict(definition)
                        if number == 7:
                            changed.update(
                                name="PC11 offline version two",
                                expected_current_version=1,
                            )
                        elif number == 10:
                            changed["definition_key"] += "_other"
                        request["new_definition"] = changed
                        if number == 7:
                            version = await create_checked_version(
                                api, engine, primary, changed
                            )
                            del request["new_definition"]
                            request["agent_definition_id"] = str(version["id"])
                    else:
                        request["agent_definition_id"] = primary["agent_definition"][
                            "id"
                        ]
                        if number == 9:
                            request["agent_definition_id"] = sessions[
                                "archive_callback"
                            ]["agent_definition"]["id"]
                    if turn["subject"] in subjects:
                        request["memory_subject_id"] = subjects[turn["subject"]]
                    else:
                        request["new_subject"] = {
                            "external_key": f"pc11-{token}-{turn['subject']}"
                        }
                    session = await api.create(request)
                    sessions[turn["chat"]] = session
                    subjects[turn["subject"]] = session["memory_subject"]["id"]
                    primary = primary or session
                    bound = session["agent_definition"]
                    assert bound["prompt_key"] == "chat_v20260926"
                    assert bound["persona_key"] == "chat_linxiaotang"
                    assert (
                        bound["persona_sha256"]
                        == primary["agent_definition"]["persona_sha256"]
                    )
                    if number == 7:
                        assert bound["version"] == 2
                        assert (
                            bound["agent_definition_id"]
                            == primary["agent_definition"]["agent_definition_id"]
                        )
                        assert bound["id"] != primary["agent_definition"]["id"]
                session = sessions[turn["chat"]]
                cid, sid = (
                    session["conversation"]["id"],
                    session["memory_subject"]["id"],
                )
                scope = {
                    "subject": sid,
                    "root": session["agent_definition"]["agent_definition_id"],
                    "purpose": "evaluation",
                    "workspace": DEFAULT_WORKSPACE_ID,
                }
                before = await full_state(engine, sid)
                before_public = await api.request(
                    "GET", f"/api/v3/history-trial/subjects/{sid}/memories"
                )
                if number == 1:
                    orphan_id = str(uuid4())
                    async with engine.begin() as connection:
                        await connection.execute(
                            insert(memory_entities).values(
                                id=orphan_id,
                                workspace_id=DEFAULT_WORKSPACE_ID,
                                subject_id=sid,
                                kind="pet",
                                label="orphan test sentinel",
                            )
                        )
                    assert await full_state(engine, sid) != before
                    assert (
                        await api.request(
                            "GET", f"/api/v3/history-trial/subjects/{sid}/memories"
                        )
                        == before_public
                    )
                    # Keep the orphan for both captured readbacks. Projection-only
                    # equality would never prove that this row remained unchanged.
                    before = await full_state(engine, sid)
                prompt = prompt_for(
                    turn,
                    replacement_suggestion="我们一起去，你买了那本书"
                    if number == 4
                    else None,
                )
                fake.script(replies[number - 1], reject=reject_origin and number == 1)
                accepted = await api.accept(
                    cid, prompt=prompt, key=f"pc11-turn-{token}-{number}"
                )
                assert await worker.process_once()
                run_id = accepted["run_id"]
                readback = await api.readback(cid, sid, run_id)
                readback.update(
                    ordinal=number,
                    definition_version_id=session["agent_definition"]["id"],
                )
                after = await full_state(engine, sid)
                assert after == before
                raw = (tmp_path / "captures" / run_id / "attempt-001.json").read_bytes()
                capture = checked_capture(
                    raw,
                    sha256=digest(raw),
                    run_id=run_id,
                    policy=session["agent_definition"]["memory_policy_version"],
                )
                observation = capture["private_observations"]
                assert observation["before"]["state"] == before
                assert observation["after"]["state"] == after
                assert observation["isolation"] == "isolated"
                if number == 1:
                    assert orphan_id in {
                        row["id"] for row in observation["before"]["state"]["entities"]
                    }
                result = validate_turn(
                    capture=capture,
                    readback=readback,
                    before_memories=before_public,
                    expected_prompt=prompt,
                    source_ledger=ledger,
                    target_scope=scope,
                    origin_run_id=origin_run_id if turn["depends_on"] else None,
                    archive_probe=number == 7,
                    evidence_kind="scripted",
                )
                result["usable_annotation"] = (
                    number in {1, 3} and result["disposition"] == "committed"
                )
                outcomes[number] = result
                result["evidence"] = {
                    "readback": readback,
                    "full_before": before,
                    "full_after": after,
                    "capture_sha256": digest(raw),
                    "reviewer_decision": capture["reviewer_decision"],
                    "history_selection": capture["history_selection"],
                    "scope": scope,
                    "definition": session["agent_definition"],
                }
                if number == 1:
                    origin_run_id = run_id
                if number in {5, 7}:
                    assert origin_run_id in result["admitted_run_ids"]
                if number in {9, 10}:
                    assert capture["history_selection"]["corpus_run_ids"] == []
                persisted = [
                    m for m in readback["state"]["messages"] if m["run_id"] == run_id
                ]
                ledger[run_id] = {
                    "status": readback["run"]["status"],
                    "scope": scope,
                    "ordinal": number,
                    "archived": False,
                    "conversation_id": cid,
                    "definition_version_id": session["agent_definition"]["id"],
                    "messages": [
                        {**m, "content_sha256": digest(m["content"].encode())}
                        for m in persisted
                    ],
                }
                if result["disposition"] == "committed":
                    fake.bind_document(
                        prompt, replies[number - 1], preferred=number in {1, 3}
                    )
                if reject_origin and number == 2:
                    assert (
                        origin_run_id
                        not in capture["history_selection"]["corpus_run_ids"]
                    )
            assert len(outcomes) == 10
            if reject_origin:
                assert outcomes[1]["disposition"] == "rejected"
                assert all(
                    outcomes[i]["disposition"] == "unassessable_dependency"
                    for i in range(3, 11)
                )
            else:
                assert all(
                    item["semantic"] == "not_measured" for item in outcomes.values()
                )
            assert any(p["path"] == "/embeddings" for p in fake.packets)
            # Retain explicit distinction from native evidence in the test artifact.
            (tmp_path / "scripted-results.json").write_text(
                json.dumps(outcomes, ensure_ascii=False, default=str)
            )
        finally:
            await engine.dispose()

    asyncio.run(scenario())
