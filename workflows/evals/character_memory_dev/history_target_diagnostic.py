"""One-shot, source-bound seven-turn reviewer target-attribution diagnostic."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

import uvicorn

import model_router.app as router_app
import model_router.forwarding as forwarding
from model_router.catalog import RouterCatalogService

import ade_api.features.agent_runtime.natural_attempt_evidence as evidence_module
from ade_api.features.agent_runtime.agent_studio_sessions import PurposeSessionService
from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.definition_service import DefinitionService
from ade_api.features.agent_runtime.history_admission import HistoryProbe
from ade_api.features.agent_runtime.history_capacity import bind_history_probe_capacity
from ade_api.features.agent_runtime.history_native_rank import HISTORY_EMBEDDING_ROUTE
from ade_api.features.agent_runtime.natural_context import HISTORY_PROBE_POLICY
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.resource_service import ResourceService
from ade_api.features.agent_runtime.router_transport import RouterTransport
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.features.agent_runtime.worker_health import RuntimeWorkerHealthService
from ade_api.features.prompt_center import build_prompt_template_reader
from ade_api.platform.settings import AdeApiSettings
from workflows.evals.deepseek_dev_smoke.isolation import (
    ROOT,
    isolated_database_url,
    router_settings,
)

from .history_h2_router import ContainerEmbeddingClient
from .history_h4_campaign import reviewer_envelope_lower_bound
from .history_h4_run import (
    FIXTURES,
    H4_AMENDMENT,
    H2_RESULT,
    _fresh_database,
    _frozen_inputs,
)
from .history_h4_transport import SplitHistoryTransport
from .history_target_diagnostic_run import (
    CANDIDATE_PROMPT_KEY,
    GENERATION_BINDING,
    admission_comparison,
    execute_trajectory,
    fact_state,
    verified_generation_binding,
)
from .natural_factual_live import source_identity
from .natural_live_results import sha256_file, write_json
from .natural_live_transport import NaturalLiveTransport


SCHEDULE = FIXTURES / "target_attribution_diagnostic.json"
AUTHORIZED_TURNS = [
    ["它现在叫小黑。", "我是说以前那只叫 Roxy 的黑狗，现在叫小黑。"],
    ["它现在叫小黑。", "我是说以前那只叫 Nini 的白狗，现在叫小黑。"],
    ["Roxy 现在叫小黑。"],
    ["你还记得我以前提过什么茶吗？", "我现在又喜欢茉莉花茶了。"],
]
OLD_MANIFESTS = (
    (
        ROOT
        / "workflows/evals/character_memory_dev/outputs/history-h4-live-20260926/manifest.json",
        "07228ca7c3642d3528c76db345ef5a14e2bd9463ada14858784872af1b9458a2",
    ),
    (
        ROOT
        / "workflows/evals/character_memory_dev/outputs/history-h4-remaining-live-20260926/manifest.json",
        "e309d643542406446cd349962bc3dee598f22ac49bfaaceaf8b6fd1e606ddb6a",
    ),
    (
        ROOT
        / "workflows/evals/character_memory_dev/outputs/history-h4-final-remaining-live-20260926/manifest.json",
        "cf5f8bbc144a33e7aa3678683f8fbc99e9bb232883c438d06a757f001bb24cb8",
    ),
)
PRIOR_DIAGNOSTIC = (
    ROOT
    / "workflows/evals/character_memory_dev/outputs/history-target-diagnostic-20260926/manifest.json",
    "9c0753c07271f2beacb7e8ab3b0e92a8d8e2c43566b90a1b1a0908ce568c7b15",
)


def frozen_schedule() -> tuple[dict, dict, dict]:
    """Check the new finite schedule against all immutable H4 source material."""
    contract, fixture, _h2 = _frozen_inputs()
    schedule = json.loads(SCHEDULE.read_text())
    cases = {case["id"]: case for case in fixture["cases"]}
    previous = []
    for path, expected_hash in OLD_MANIFESTS:
        if sha256_file(path) != expected_hash:
            raise RuntimeError("an immutable H4 manifest changed")
        previous.append(json.loads(path.read_text()))
    turns = schedule.get("trajectories", [])
    if (
        schedule.get("schema_version") != 1
        or schedule.get("status") != "director-approved-seven-turn-diagnostic"
        or schedule.get("source_cases_sha256") != sha256_file(FIXTURES / "cases.json")
        or schedule.get("h2_result_sha256") != sha256_file(H2_RESULT)
        or schedule.get("h4_reviewer_amendment_sha256") != sha256_file(H4_AMENDMENT)
        or schedule.get("policy") != HISTORY_PROBE_POLICY
        or schedule.get("arm") != "automatic_history"
        or [item.get("id") for item in turns]
        != [
            "ambiguous_then_roxy",
            "ambiguous_then_nini",
            "explicit_roxy",
            "removed_jasmine",
        ]
        or [item.get("seed_case") for item in turns]
        != [
            "h_only_referent",
            "h_only_referent",
            "h_only_referent",
            "removed_acknowledgment",
        ]
        or [len(item.get("turns", [])) for item in turns] != [2, 2, 1, 2]
        or [[turn.get("user") for turn in item["turns"]] for item in turns]
        != AUTHORIZED_TURNS
        or not all(item.get("isolated_subject") is True for item in turns)
        or turns[0]["turns"][0]["user"] != cases["h_only_referent"]["target"]["user"]
        or turns[1]["turns"][0]["user"] != cases["h_only_referent"]["target"]["user"]
        or turns[3]["turns"][0]["user"]
        != cases["removed_acknowledgment"]["target"]["user"]
        or turns[3]["turns"][1]["user"]
        != cases["removed_acknowledgment"]["followup"]["user"]
        or schedule.get("per_turn")
        != {
            "timeout_seconds": 180,
            "retry_count": 0,
            "reviewer_repairs": 0,
            "generation_input_limit_tokens": 11213,
            "generation_output_tokens": 4096,
            "reviewer_input_limit_tokens": 11469,
            "reviewer_output_tokens": 4096,
            "conversation_request_ceiling": 2,
            "reviewer_request_ceiling": 1,
            "dispatch_counts": "observational; missing receipts mark counts incomplete",
        }
        or contract["binding"]["generation_input_limit_tokens"] != 11213
        or contract["binding"]["reviewer_input_limit_tokens"] != 11469
        or previous[-1]["fixture_sha256"]["cases"] != schedule["source_cases_sha256"]
        or previous[-1]["capacity"] != contract["binding"]
        or previous[-1]["routes"]["deepseek::deepseek-flash"]
        != schedule["routes"]["conversation_and_reviewer"]["fingerprint"]
        or previous[-1]["routes"][HISTORY_EMBEDDING_ROUTE]
        != schedule["routes"]["history_and_fact_embeddings"]["fingerprint"]
    ):
        raise RuntimeError("target-attribution schedule or H4 source contract drifted")
    envelope = reviewer_envelope_lower_bound(contract, fixture)
    if envelope["minimum_input_tokens"] > envelope["frozen_input_limit"]:
        raise RuntimeError("reviewer envelope cannot fit before provider dispatch")
    return schedule, cases, previous[-1]


def prior_diagnostic() -> dict:
    path, expected_hash = PRIOR_DIAGNOSTIC
    if sha256_file(path) != expected_hash:
        raise RuntimeError("prior seven-turn diagnostic manifest changed")
    manifest = json.loads(path.read_text())
    if manifest.get("status") != "completed_pending_semantic_review":
        raise RuntimeError("prior seven-turn diagnostic did not complete")
    return manifest


def validate_catalog(catalog: dict, schedule: dict) -> tuple[dict, dict]:
    """Bind live routes to the previously observed provider identities."""
    items = {item["model_key"]: item for item in catalog["items"]}
    deepseek = items["deepseek::deepseek-flash"]["deployment"]["fingerprint"]
    qwen = items[HISTORY_EMBEDDING_ROUTE]["deployment"]["fingerprint"]
    expected_chat = schedule["routes"]["conversation_and_reviewer"]
    expected_embedding = schedule["routes"]["history_and_fact_embeddings"]
    if (
        expected_chat["model"] != "deepseek::deepseek-flash"
        or deepseek.get("sha256") != expected_chat["fingerprint"]
        or deepseek.get("context_settings", {}).get("reviewer_repair_count") != 0
        or int(deepseek.get("context_settings", {}).get("total_tokens") or 0) < 16384
        or int(deepseek.get("context_settings", {}).get("max_output_tokens") or 0)
        < 4096
        or expected_embedding["model"] != HISTORY_EMBEDDING_ROUTE
        or qwen.get("sha256") != expected_embedding["fingerprint"]
        or qwen.get("artifact_reference") != "Qwen/Qwen3-Embedding-0.6B"
        or qwen.get("artifact_revision") != expected_embedding["artifact_revision"]
        or qwen.get("sampling_settings", {}).get("dimensions")
        != expected_embedding["dimensions"]
    ):
        raise RuntimeError("provider catalog differs from pinned diagnostic routes")
    return deepseek, qwen


async def run(args: argparse.Namespace) -> None:
    database_url, database_name = isolated_database_url(args.database_url)
    source_revision, source_fingerprint = source_identity()
    schedule, cases, old_manifest = frozen_schedule()
    prior_manifest = prior_diagnostic()
    if args.output.exists():
        raise RuntimeError("one-shot diagnostic output must be new")
    await _fresh_database(database_url, database_name)
    registry = build_prompt_template_reader(
        ROOT, persona_db_path=args.output.parent / ".target-diagnostic-personas.sqlite3"
    )
    prompt = registry.get_template("prompt", CANDIDATE_PROMPT_KEY, scenario="chat")
    old_prompt = registry.get_template("prompt", "chat_v20260516", scenario="chat")
    persona = registry.get_template("persona", "chat_linxiaotang", scenario="chat")
    prompt_hash = hashlib.sha256(str(prompt["content"]).encode()).hexdigest()
    old_prompt_hash = hashlib.sha256(str(old_prompt["content"]).encode()).hexdigest()
    persona_hash = hashlib.sha256(str(persona["content"]).encode()).hexdigest()
    if (
        old_prompt_hash != old_manifest["prompt_sha256"]
        or persona_hash != old_manifest["persona_sha256"]
    ):
        raise RuntimeError("old prompt or persona differs from the H4 source")
    binding = verified_generation_binding(
        prompt,
        persona,
        old_manifest,
        prior_manifest,
        schedule,
        schedule_sha256=sha256_file(SCHEDULE),
        historical_manifest_sha256=[item[1] for item in OLD_MANIFESTS],
        prior_diagnostic_manifest_sha256=PRIOR_DIAGNOSTIC[1],
    )
    configured_router = router_settings(args.env_file, include_spark=False)
    router_app.get_settings = lambda: configured_router
    router_app.catalog_service = RouterCatalogService(
        settings_factory=lambda: configured_router
    )
    forwarding.get_settings = lambda: configured_router
    server = uvicorn.Server(
        uvicorn.Config(
            router_app.app,
            host="127.0.0.1",
            port=args.router_port,
            log_level="warning",
            access_log=False,
        )
    )
    server_task = asyncio.create_task(server.serve())
    try:
        for _ in range(100):
            if server.started:
                break
            if server_task.done():
                raise RuntimeError("isolated DeepSeek router failed to start")
            await asyncio.sleep(0.1)
        else:
            raise RuntimeError("isolated DeepSeek router did not start")
        split = SplitHistoryTransport(
            RouterTransport(f"http://127.0.0.1:{args.router_port}/v1"),
            ContainerEmbeddingClient(args.qwen_container),
        )
        deepseek, qwen = validate_catalog(
            await split.catalog(timeout_seconds=30), schedule
        )
        args.output.mkdir(parents=True, exist_ok=False)
        args.output.chmod(0o700)
        os.environ.update(
            ADE_REPOSITORY_ROOT=str(ROOT),
            ADE_SOURCE_REVISION=source_revision,
            ADE_SOURCE_FINGERPRINT=source_fingerprint,
            ADE_SOURCE_DIRTY="false",
            ADE_NATURAL_MEMORY_CAPTURE="1",
        )
        transport = NaturalLiveTransport(
            split,
            capture_dir=args.output / "raw",
            generation_model="deepseek::deepseek-flash",
            embedding_model=HISTORY_EMBEDDING_ROUTE,
        )
        manifest = {
            "schema_version": 1,
            "status": "running",
            "schedule_sha256": sha256_file(SCHEDULE),
            "historical_manifest_sha256": [item[1] for item in OLD_MANIFESTS],
            "source_revision": source_revision,
            "source_fingerprint": source_fingerprint,
            "database": database_name,
            "policy": HISTORY_PROBE_POLICY,
            "prompt_key": CANDIDATE_PROMPT_KEY,
            "prompt_sha256": prompt_hash,
            "persona_sha256": persona_hash,
            "generation_binding_sha256": sha256_file(GENERATION_BINDING),
            "generation_binding": binding,
            "reviewer_instruction_sha256": binding["reviewer_instruction_sha256"],
            "reviewer_schema_sha256": binding["reviewer_schema_sha256"],
            "routes": {
                "deepseek::deepseek-flash": deepseek["sha256"],
                HISTORY_EMBEDDING_ROUTE: qwen["sha256"],
            },
            "per_turn": schedule["per_turn"],
            "planned_turns": [
                {"trajectory": item["id"], "turn": number + 1}
                for item in schedule["trajectories"]
                for number, _ in enumerate(item["turns"])
            ],
            "trajectories": [],
            "admission_comparison": {},
        }
        write_json(args.output / "manifest.json", manifest)
        engine = create_persistence_engine(database_url)
        evidence_module.ARTIFACT_ROOT = args.output / "attempts"
        settings = AdeApiSettings(
            _env_file=None,
            agent_runtime_enabled=True,
            agent_runtime_mode="development",
            database_url=database_url,
            model_discovery_timeout_seconds=30,
            agent_runtime_worker_id=f"target-diagnostic-{uuid4().hex[:8]}",
        )
        database = RuntimeDatabase(engine)
        definitions = DefinitionService(
            database=database,
            settings=settings,
            prompt_registry=build_prompt_template_reader(
                ROOT, persona_db_path=args.output / "personas.sqlite3"
            ),
            router_transport=transport,
        )

        class BoundDefinitions:
            async def prepare(self, request, *, purpose):
                prepared = await definitions.prepare(request, purpose=purpose)
                prepared["memory_policy_version"] = HISTORY_PROBE_POLICY
                return bind_history_probe_capacity(prepared)

        sessions = PurposeSessionService(
            database=database,
            definitions=BoundDefinitions(),
            purpose="evaluation",
            session_namespace="target-attribution-diagnostic",
        )
        service = RunService(
            database=database,
            settings=settings,
            router_transport=transport,
            worker_health=RuntimeWorkerHealthService(engine=engine, settings=settings),
        )
        resources = ResourceService(database)
        worker = AgentRuntimeWorker(
            engine=engine,
            settings=settings,
            transport=transport,
            history_probe=HistoryProbe(
                arm="automatic_history",
                ranking_recipe="probe_local_qwen_cosine",
                expected_embedding_fingerprint=qwen["sha256"],
            ),
        )
        heartbeat_stop = asyncio.Event()
        await worker.presence.register()
        heartbeat = asyncio.create_task(
            worker.presence.heartbeat_forever(heartbeat_stop)
        )
        try:
            prior_trajectories = {
                item["name"]: item for item in prior_manifest["trajectories"]
            }
            for index, trajectory in enumerate(schedule["trajectories"]):
                result = await execute_trajectory(
                    trajectory=trajectory,
                    case=cases[trajectory["seed_case"]],
                    index=index,
                    sessions=sessions,
                    service=service,
                    resources=resources,
                    worker=worker,
                    engine=engine,
                    transport=transport,
                    output=args.output,
                    prompt_key=CANDIDATE_PROMPT_KEY,
                )
                if (
                    result["session"]["prompt_sha256"] != prompt_hash
                    or result["session"]["persona_sha256"] != persona_hash
                ):
                    raise RuntimeError("session bound a different prompt or persona")
                prior_turns = prior_trajectories[trajectory["id"]]["turns"]
                manifest["admission_comparison"][trajectory["id"]] = [
                    admission_comparison(turn, prior_turns[turn_index])
                    for turn_index, turn in enumerate(result["turns"])
                ]
                manifest["trajectories"].append(result)
                write_json(args.output / "manifest.json", manifest)
            ids = [item["session"]["subject_id"] for item in manifest["trajectories"]]
            if len(ids) != 4 or len(set(ids)) != 4:
                raise RuntimeError("diagnostic trajectories did not isolate subjects")
            manifest["independent_final_readback"] = {
                item["name"]: await fact_state(engine, item["session"]["subject_id"])
                for item in manifest["trajectories"]
            }
            for item in manifest["trajectories"]:
                if (
                    manifest["independent_final_readback"][item["name"]]
                    != item["turns"][-1]["after_facts"]
                ):
                    raise RuntimeError("final fact readback changed after a trajectory")
            manifest["status"] = "completed_pending_semantic_review"
        except Exception as exc:
            manifest["status"] = "stopped_integrity_or_execution"
            manifest["stop_reason"] = f"{type(exc).__name__}: {exc}"
        finally:
            heartbeat_stop.set()
            await asyncio.gather(heartbeat, return_exceptions=True)
            await worker.presence.mark_stopped()
            manifest["dispatch_final"] = transport.counts()
            manifest["transport_dispatches"] = {
                "generation": split.generation_dispatches,
                "embedding": split.embedding_dispatches,
            }
            write_json(args.output / "manifest.json", manifest)
            await engine.dispose()
    finally:
        server.should_exit = True
        await asyncio.gather(server_task, return_exceptions=True)
    if manifest["status"].startswith("stopped_"):
        raise RuntimeError(manifest["stop_reason"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--qwen-container", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--router-port", type=int, default=8143)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
