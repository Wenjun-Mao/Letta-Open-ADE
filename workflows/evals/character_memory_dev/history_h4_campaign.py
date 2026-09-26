"""Finite H4 schedule and immutable provider/database preflight."""

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
from ade_api.features.agent_runtime.natural_memory_review import (
    natural_review_json_schema,
)
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    HISTORY_REVIEWER_INSTRUCTION,
    NATURAL_REVIEWER_SYSTEM,
    natural_review_request,
    serialized_review_tokens,
)
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
from .history_h4_run import (
    FIXTURES,
    H4_AMENDMENT,
    H2_RESULT_SHA256,
    QWEN_FINGERPRINT,
    _execute_cell,
    _fresh_database,
    _frozen_inputs,
)
from .history_h4_transport import SplitHistoryTransport
from .history_h4_remaining import load_remaining, ORIGINAL_SHA256, PROPOSAL_SHA256
from .history_h4_disposition import (
    CampaignStop,
    _classify_cell as _classify_cell,
    _classify_cell_turns,
    _paired_packet_check,
)
from .natural_factual_live import source_identity
from .natural_live_results import sha256_file, write_json
from .natural_live_transport import NaturalLiveTransport


def _planned_cells(contract: dict, fixture: dict) -> list[dict]:
    followups = set(contract["paired_schedule"]["followup_case_ids_per_arm"])
    return [
        {"name": f"control-{control['id']}", "arm": "empty_history"}
        for control in fixture["native_controls"]
    ] + [
        {
            "name": case["id"],
            "arm": arm,
            "followup_scheduled": case["id"] in followups,
        }
        for case in fixture["cases"]
        for arm in contract["paired_schedule"]["arms"]
    ]


def _planned_turns(contract: dict, fixture: dict) -> list[dict[str, str]]:
    turns = []
    for cell in _planned_cells(contract, fixture):
        turns.append({"name": cell["name"], "arm": cell["arm"], "turn": "target"})
        if cell.get("followup_scheduled"):
            turns.append({"name": cell["name"], "arm": cell["arm"], "turn": "followup"})
    return turns


def reviewer_envelope_lower_bound(contract: dict, fixture: dict) -> dict[str, int]:
    """Use the smallest H-capable packet with the frozen full reply reserve."""
    user = fixture["cases"][0]["target"]["user"]
    current = {"id": "current", "role": "user", "content": user}
    request = natural_review_request(
        model_key="deepseek::deepseek-flash",
        provider_adapter="deepseek_openai",
        current_user_message=current,
        source_messages=[current],
        facts=[],
        entities=[],
        candidate_reply="x" * (4 * contract["binding"]["generation_output_tokens"]),
        max_output_tokens=contract["binding"]["reviewer_output_tokens"],
        history_capable=True,
    )
    return {
        "minimum_input_tokens": serialized_review_tokens(request),
        "frozen_input_limit": contract["binding"]["reviewer_input_limit_tokens"],
    }


async def run(args: argparse.Namespace) -> None:
    checked_url, database_name = isolated_database_url(args.database_url)
    source_revision, source_fingerprint = source_identity()
    contract, fixture, _h2 = _frozen_inputs()
    original, proposal, selected_cells = load_remaining(
        _planned_cells(contract, fixture)
    )
    selected_keys = {(cell["name"], cell["arm"]) for cell in selected_cells}
    current_fixture = {
        "contract": sha256_file(FIXTURES / "contract.json"),
        "h4_amendment": sha256_file(H4_AMENDMENT),
        "effective_h4_contract": hashlib.sha256(
            json.dumps(contract, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest(),
        "cases": sha256_file(FIXTURES / "cases.json"),
        "h2_result": H2_RESULT_SHA256,
    }
    instruction_sha = hashlib.sha256(
        (NATURAL_REVIEWER_SYSTEM + HISTORY_REVIEWER_INSTRUCTION).encode()
    ).hexdigest()
    schema_sha = hashlib.sha256(
        json.dumps(
            natural_review_json_schema(history_capable=True),
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
    ).hexdigest()
    registry = build_prompt_template_reader(
        ROOT, persona_db_path=args.output.parent / ".h4-remaining-personas.sqlite3"
    )
    prompt = registry.get_template("prompt", "chat_v20260516", scenario="chat")
    persona = registry.get_template("persona", "chat_linxiaotang", scenario="chat")
    prompt_sha = (
        hashlib.sha256(str(prompt["content"]).encode()).hexdigest() if prompt else None
    )
    persona_sha = (
        hashlib.sha256(str(persona["content"]).encode()).hexdigest()
        if persona
        else None
    )
    old_definition = original["cells"][0]["session"]
    if (
        current_fixture != original["fixture_sha256"]
        or contract["binding"] != original["capacity"]
        or HISTORY_PROBE_POLICY != original["policy"]
        or instruction_sha != original["reviewer_instruction_sha256"]
        or schema_sha != original["reviewer_schema_sha256"]
        or prompt_sha != old_definition["prompt_sha256"]
        or persona_sha != old_definition["persona_sha256"]
    ):
        raise RuntimeError(
            "H4 prompt, persona, fixture, policy, or reviewer binding drifted"
        )
    envelope = reviewer_envelope_lower_bound(contract, fixture)
    if envelope["minimum_input_tokens"] > envelope["frozen_input_limit"]:
        raise RuntimeError(
            "H4 reviewer envelope is infeasible before provider dispatch: "
            f"{envelope['minimum_input_tokens']} > {envelope['frozen_input_limit']}"
        )
    if args.output.exists():
        raise RuntimeError(
            "H4 output must be new; an incomplete campaign is never resumed"
        )
    await _fresh_database(checked_url, database_name)
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
        catalog = await split.catalog(timeout_seconds=30)
        items = {item["model_key"]: item for item in catalog["items"]}
        deepseek = items["deepseek::deepseek-flash"]["deployment"]["fingerprint"]
        qwen = items[HISTORY_EMBEDDING_ROUTE]["deployment"]["fingerprint"]
        if (
            deepseek.get("sha256") != original["routes"]["deepseek::deepseek-flash"]
            or qwen.get("sha256") != QWEN_FINGERPRINT
            or qwen.get("artifact_reference") != "Qwen/Qwen3-Embedding-0.6B"
            or qwen.get("artifact_revision")
            != "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
            or qwen.get("sampling_settings", {}).get("dimensions") != 1024
            or qwen.get("sha256") != original["routes"][HISTORY_EMBEDDING_ROUTE]
            or deepseek.get("context_settings", {}).get("reviewer_repair_count") != 0
            or int(deepseek.get("context_settings", {}).get("total_tokens") or 0)
            < 16384
            or int(deepseek.get("context_settings", {}).get("max_output_tokens") or 0)
            < 4096
        ):
            raise RuntimeError("H4 catalog differs from frozen provider identities")
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
            "campaign_kind": "approved_remaining_21_turns",
            "original_manifest_sha256": ORIGINAL_SHA256,
            "proposal_sha256": PROPOSAL_SHA256,
            "original_source_revision": original["source_revision"],
            "prompt_sha256": prompt_sha,
            "persona_sha256": persona_sha,
            "source_revision": source_revision,
            "source_fingerprint": source_fingerprint,
            "database": database_name,
            "fixture_sha256": {
                "contract": sha256_file(FIXTURES / "contract.json"),
                "h4_amendment": sha256_file(H4_AMENDMENT),
                "effective_h4_contract": hashlib.sha256(
                    json.dumps(contract, ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest(),
                "cases": sha256_file(FIXTURES / "cases.json"),
                "h2_result": H2_RESULT_SHA256,
            },
            "policy": HISTORY_PROBE_POLICY,
            "arms": contract["paired_schedule"]["arms"],
            "routes": {
                "deepseek::deepseek-flash": deepseek["sha256"],
                HISTORY_EMBEDDING_ROUTE: qwen["sha256"],
            },
            "capacity": contract["binding"],
            "reviewer_instruction_sha256": hashlib.sha256(
                (NATURAL_REVIEWER_SYSTEM + HISTORY_REVIEWER_INSTRUCTION).encode()
            ).hexdigest(),
            "reviewer_schema_sha256": hashlib.sha256(
                json.dumps(
                    natural_review_json_schema(history_capable=True),
                    ensure_ascii=False,
                    sort_keys=True,
                ).encode()
            ).hexdigest(),
            "scheduled_controls": contract["paired_schedule"]["native_control_ids"],
            "scheduled_targets": [case["id"] for case in fixture["cases"]],
            "scheduled_followups_per_arm": fixture["followup_schedule"],
            "planned_cells": selected_cells,
            "planned_turns": proposal["remaining_turns"],
            "cells": [],
            "cell_dispositions": [],
            "pair_checks": [],
        }
        write_json(args.output / "manifest.json", manifest)
        engine = create_persistence_engine(checked_url)
        evidence_module.ARTIFACT_ROOT = args.output / "attempts"
        settings = AdeApiSettings(
            _env_file=None,
            agent_runtime_enabled=True,
            agent_runtime_mode="development",
            database_url=checked_url,
            model_discovery_timeout_seconds=30,
            agent_runtime_worker_id=f"history-h4-{uuid4().hex[:8]}",
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
            session_namespace="natural-history-h4",
        )
        service = RunService(
            database=database,
            settings=settings,
            router_transport=transport,
            worker_health=RuntimeWorkerHealthService(engine=engine, settings=settings),
        )
        resources = ResourceService(database)
        workers = {
            "empty_history": AgentRuntimeWorker(
                engine=engine,
                settings=settings,
                transport=transport,
                history_probe=HistoryProbe(arm="empty_history"),
            ),
            "automatic_history": AgentRuntimeWorker(
                engine=engine,
                settings=settings,
                transport=transport,
                history_probe=HistoryProbe(
                    arm="automatic_history",
                    ranking_recipe="probe_local_qwen_cosine",
                    expected_embedding_fingerprint=QWEN_FINGERPRINT,
                ),
            ),
        }
        heartbeat_stop = asyncio.Event()
        await workers["empty_history"].presence.register()
        heartbeat = asyncio.create_task(
            workers["empty_history"].presence.heartbeat_forever(heartbeat_stop)
        )
        try:
            index = 0
            for case in fixture["cases"]:
                if not any(
                    (case["id"], arm) in selected_keys
                    for arm in contract["paired_schedule"]["arms"]
                ):
                    continue
                paired = []
                for arm in contract["paired_schedule"]["arms"]:
                    if (case["id"], arm) not in selected_keys:
                        continue
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
                        output=args.output,
                        index=index,
                    )
                    manifest["cells"].append(result)
                    paired.append(result)
                    write_json(args.output / "manifest.json", manifest)
                    manifest["cell_dispositions"].extend(_classify_cell_turns(result))
                    write_json(args.output / "manifest.json", manifest)
                    index += 1
                if case["id"] == "user_retraction":
                    prior = next(
                        cell
                        for cell in original["cells"]
                        if cell["name"] == case["id"] and cell["arm"] == "empty_history"
                    )
                    check = _paired_packet_check(case["id"], [prior, paired[0]])
                    check["scope"] = "cross_campaign"
                    check["original_manifest_sha256"] = ORIGINAL_SHA256
                else:
                    check = _paired_packet_check(case["id"], paired)
                    check["scope"] = "remaining_campaign"
                manifest["pair_checks"].append(check)
                write_json(args.output / "manifest.json", manifest)
                if manifest["pair_checks"][-1]["base_packet_equal"] is False:
                    raise CampaignStop(f"{case['id']} paired base packets differ")
            manifest["status"] = (
                "completed_with_bounded_rejections_pending_director_review"
                if any(
                    item["disposition"] == "bounded_rejection"
                    for item in manifest["cell_dispositions"]
                )
                else "completed_pending_director_semantic_review"
            )
        except CampaignStop as exc:
            manifest["status"] = "stopped_structural"
            manifest["stop_reason"] = str(exc)
        except Exception as exc:
            manifest["status"] = "stopped_unexpected_error"
            manifest["stop_reason"] = f"{type(exc).__name__}: {exc}"
        finally:
            for planned in manifest["planned_cells"][len(manifest["cells"]) :]:
                manifest["cells"].append(
                    {
                        **planned,
                        "status": "unrun_after_stop",
                        "target": {"status": "unrun_after_stop"},
                        **(
                            {"followup": {"status": "unrun_dependency"}}
                            if planned.get("followup_scheduled")
                            else {}
                        ),
                    }
                )
            heartbeat_stop.set()
            await asyncio.gather(heartbeat, return_exceptions=True)
            await workers["empty_history"].presence.mark_stopped()
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
    parser.add_argument("--router-port", type=int, default=8141)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
