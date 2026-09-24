"""One-shot, source-bound factual-continuity diagnostic on an isolated database."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values

import uvicorn
from sqlalchemy import text as sql_text

import model_router.app as router_app
import model_router.forwarding as forwarding
from model_router.catalog import RouterCatalogService

import ade_api.features.agent_runtime.natural_attempt_evidence as evidence_module
from ade_api.features.agent_runtime.agent_studio_sessions import PurposeSessionService
from ade_api.features.agent_runtime.contracts import (
    AcceptTurnRequest,
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
)
from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.definition_service import DefinitionService
from ade_api.features.agent_runtime.natural_evaluation_capacity import (
    DEEPSEEK_ROUTE,
    bind_checkpoint6_capacity,
)
from ade_api.features.agent_runtime.natural_memory_review import (
    natural_review_json_schema,
)
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    NATURAL_REVIEWER_SYSTEM,
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
    isolated_database_url,
    router_settings,
)

from .natural_live_contract import EMBEDDING_ROUTE, ROOT
from .natural_live_results import (
    capture_scope,
    sha256_file,
    verify_attempt_safety,
    write_json,
)
from .natural_live_transport import NaturalLiveTransport, RequestScope


FIXTURE = (
    ROOT
    / "workflows/evals/character_memory_dev/fixtures/natural_memory/factual_live_diagnostic.json"
)
POLICY = "natural-user-assertions-v4-b"


def pinned_router_settings(env_file: Path):
    """Resolve Docker's pinned Spark alias on this Mac without changing route identity."""

    configured = router_settings(env_file, include_spark=True)
    host = str(dotenv_values(env_file).get("DGX_SPARK_HOST") or "").strip()
    if (
        not host
        or not all(part.isdigit() and 0 <= int(part) <= 255 for part in host.split("."))
        or len(host.split(".")) != 4
    ):
        raise RuntimeError("Spark host must be a configured IPv4 address")
    original_getaddrinfo = socket.getaddrinfo

    def resolve_pinned_alias(name, *args, **kwargs):
        return original_getaddrinfo(
            host if name == "dgx-spark" else name, *args, **kwargs
        )

    socket.getaddrinfo = resolve_pinned_alias
    sources = [
        source.model_copy(
            update={"base_url": "http://dgx-spark:8001/v1", "base_url_env": ""}
        )
        if source.id == "dgx_embedding_sidecar"
        else source
        for source in configured.sources
    ]
    return configured.model_copy(update={"sources": sources})


def source_identity() -> tuple[str, str]:
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT):
        raise RuntimeError("live diagnostic requires a clean source commit")
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    fingerprint = subprocess.check_output(
        [
            sys.executable,
            str(ROOT / "scripts/source_fingerprint.py"),
            "--root",
            str(ROOT),
        ],
        cwd=ROOT,
        text=True,
    ).strip()
    return revision, fingerprint


async def run(args: argparse.Namespace) -> None:
    database_url, database_name = isolated_database_url(args.database_url)
    revision, fingerprint = source_identity()
    fixture = json.loads(FIXTURE.read_text())
    if (
        fixture["policy"] != POLICY
        or fixture["routes"] != [DEEPSEEK_ROUTE, EMBEDDING_ROUTE]
        or fixture["reviewer_output_tokens"] != 4096
        or fixture["retry_count"] != 0
        or sum(len(case["turns"]) for case in fixture["cases"]) != 11
    ):
        raise RuntimeError("factual diagnostic schedule drifted")
    if args.output.exists():
        raise RuntimeError("diagnostic output must be new")
    engine = create_persistence_engine(database_url)
    try:
        async with engine.connect() as connection:
            identity = (
                await connection.execute(
                    sql_text("SELECT current_database(), current_user")
                )
            ).one()
            pending = await connection.scalar(sql_text("SELECT count(*) FROM ade.runs"))
            extension_schema = await connection.scalar(
                sql_text(
                    "SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'"
                )
            )
        if (
            tuple(identity) != (database_name, "ade_owner")
            or pending
            or extension_schema != "extensions"
        ):
            raise RuntimeError("fresh isolated database identity or bootstrap failed")
        await RuntimeDatabase(engine).ensure_ready()
        args.output.mkdir(parents=True, exist_ok=False)
        args.output.chmod(0o700)
        os.environ.update(
            ADE_REPOSITORY_ROOT=str(ROOT),
            ADE_SOURCE_REVISION=revision,
            ADE_SOURCE_FINGERPRINT=fingerprint,
            ADE_SOURCE_DIRTY="false",
            ADE_NATURAL_MEMORY_CAPTURE="1",
        )
        configured_router = pinned_router_settings(args.env_file)
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
                    raise RuntimeError("isolated router failed to start")
                await asyncio.sleep(0.1)
            else:
                raise RuntimeError("isolated router did not start")
            transport = NaturalLiveTransport(
                RouterTransport(f"http://127.0.0.1:{args.router_port}/v1"),
                capture_dir=args.output / "raw",
                generation_model=DEEPSEEK_ROUTE,
                embedding_model=EMBEDDING_ROUTE,
            )
            catalog = await transport.catalog(timeout_seconds=30)
            models = {item["model_key"]: item for item in catalog.get("items", [])}
            for route in (DEEPSEEK_ROUTE, EMBEDDING_ROUTE):
                if not models.get(route, {}).get("deployment"):
                    raise RuntimeError(f"pinned route unavailable: {route}")
            manifest = {
                "id": fixture["id"],
                "status": "running",
                "source_revision": revision,
                "source_fingerprint": fingerprint,
                "fixture_sha256": sha256_file(FIXTURE),
                "database": database_name,
                "policy": POLICY,
                "reviewer_envelope": {"input_limit": 6759, "max_output_tokens": 4096},
                "reviewer_instruction_sha256": hashlib.sha256(
                    NATURAL_REVIEWER_SYSTEM.encode()
                ).hexdigest(),
                "reviewer_schema_sha256": hashlib.sha256(
                    json.dumps(
                        natural_review_json_schema(), ensure_ascii=False, sort_keys=True
                    ).encode()
                ).hexdigest(),
                "route_fingerprints": {
                    route: models[route]["deployment"]["fingerprint"]["sha256"]
                    for route in (DEEPSEEK_ROUTE, EMBEDDING_ROUTE)
                },
                "cases": [],
            }
            write_json(args.output / "manifest.json", manifest)
            settings = AdeApiSettings(
                _env_file=None,
                agent_runtime_enabled=True,
                agent_runtime_mode="development",
                database_url=database_url,
                model_discovery_timeout_seconds=30,
                agent_runtime_worker_id=f"factual-{uuid4().hex[:8]}",
            )
            evidence_module.ARTIFACT_ROOT = args.output / "attempts"
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
                    prepared["memory_policy_version"] = POLICY
                    return bind_checkpoint6_capacity(
                        prepared, diagnostic_reviewer_output=True
                    )

            sessions = PurposeSessionService(
                database=database,
                definitions=BoundDefinitions(),
                purpose="evaluation",
                session_namespace=fixture["id"],
            )
            service = RunService(
                database=database,
                settings=settings,
                router_transport=transport,
                worker_health=RuntimeWorkerHealthService(
                    engine=engine, settings=settings
                ),
            )
            resources = ResourceService(database)
            worker = AgentRuntimeWorker(
                engine=engine, settings=settings, transport=transport
            )
            heartbeat_stop = asyncio.Event()
            await worker.presence.register()
            heartbeat = asyncio.create_task(
                worker.presence.heartbeat_forever(heartbeat_stop)
            )
            try:
                for case_index, case in enumerate(fixture["cases"]):
                    case_result = {"id": case["id"], "turns": []}
                    manifest["cases"].append(case_result)
                    subject_id = None
                    definition_id = None
                    conversation_id = None
                    conversation_number = 0
                    for turn_index, turn in enumerate(case["turns"]):
                        if turn["conversation"] != conversation_number:
                            token = uuid4().hex[:12]
                            request = CreateAgentStudioSessionRequest(
                                idempotency_key=f"factual-session-{token}",
                                title=f"Factual {case['id']} conversation {turn['conversation']}",
                                **(
                                    {
                                        "new_definition": CreateAgentDefinitionRequest(
                                            definition_key=f"factual_{case_index}_{token}",
                                            name=f"Factual {case['id']}",
                                            model_key=DEEPSEEK_ROUTE,
                                            reviewer_model_key=DEEPSEEK_ROUTE,
                                            embedding_model_key=EMBEDDING_ROUTE,
                                            tool_names=["search_memory"],
                                        ),
                                        "new_subject": CreateMemorySubjectRequest(
                                            external_key=f"factual-{token}",
                                            display_name=f"Synthetic subject {case_index + 1}",
                                        ),
                                    }
                                    if subject_id is None
                                    else {
                                        "agent_definition_id": definition_id,
                                        "memory_subject_id": subject_id,
                                    }
                                ),
                            )
                            session = await sessions.create(request)
                            subject_id = session["memory_subject"]["id"]
                            definition_id = session["agent_definition"]["id"]
                            conversation_id = session["conversation"]["id"]
                            conversation_number = turn["conversation"]
                            case_result.setdefault("sessions", []).append(
                                {
                                    "subject_id": subject_id,
                                    "definition_id": definition_id,
                                    "conversation_id": conversation_id,
                                    "definition": session["agent_definition"],
                                }
                            )
                        label = f"case-{case_index + 1}-turn-{turn_index + 1}"
                        result = {
                            "label": label,
                            "user": turn["user"],
                            "expect": turn["expect"],
                            "status": "started",
                            "dispatch_before": transport.counts(),
                        }
                        case_result["turns"].append(result)
                        write_json(args.output / "manifest.json", manifest)
                        accepted = await service.accept_turn(
                            conversation_id,
                            AcceptTurnRequest(
                                content=turn["user"],
                                idempotency_key=f"factual-turn-{uuid4().hex}",
                                timeout_seconds=180,
                                retry_count=0,
                            ),
                        )
                        result["run_id"] = accepted["run_id"]
                        scope = RequestScope(label)
                        try:
                            with transport.scope(scope):
                                processed = await worker.process_once()
                            if not processed:
                                raise RuntimeError(
                                    "native worker did not process accepted run"
                                )
                            result["provider_captures"] = capture_scope(
                                transport.capture_dir, scope
                            )
                            run = await service.get_run(accepted["run_id"])
                            memory = await resources.get_subject_memories(
                                subject_id, required_purpose="evaluation"
                            )
                            conversation = await resources.get_conversation_state(
                                conversation_id, required_purpose="evaluation"
                            )
                            attempt_path = (
                                args.output
                                / "attempts"
                                / accepted["run_id"]
                                / "attempt-001.json"
                            )
                            if not attempt_path.is_file():
                                raise RuntimeError("native attempt evidence missing")
                            attempt = json.loads(attempt_path.read_text())
                            safe, safety_reason = verify_attempt_safety(
                                run=run, evidence=attempt, facts=memory["facts"]
                            )
                            result.update(
                                run=run,
                                memory=memory,
                                conversation=conversation,
                                attempt_artifact=str(attempt_path),
                                attempt_sha256=sha256_file(attempt_path),
                                safety=safety_reason,
                                dispatch_after=transport.counts(),
                            )
                            if not safe:
                                raise RuntimeError(safety_reason)
                            result["status"] = (
                                "committed"
                                if attempt["terminal_readback"]["outcome"]
                                == "committed"
                                else "rejected"
                            )
                            if result["status"] == "rejected":
                                raise RuntimeError(
                                    "native review rejected; stop for diagnosis"
                                )
                        except Exception as exc:
                            result["status"] = "stopped"
                            result["stop_reason"] = f"{type(exc).__name__}: {exc}"
                            manifest["status"] = "stopped"
                            manifest["stop_reason"] = result["stop_reason"]
                            raise
                        finally:
                            result["dispatch_after"] = transport.counts()
                            result["artifact_sha256"] = write_json(
                                args.output / "cells" / f"{label}.json", result
                            )
                            write_json(args.output / "manifest.json", manifest)
                manifest["status"] = "completed_pending_semantic_review"
            finally:
                heartbeat_stop.set()
                await asyncio.gather(heartbeat, return_exceptions=True)
                await worker.presence.mark_stopped()
                manifest["dispatch_final"] = transport.counts()
                write_json(args.output / "manifest.json", manifest)
        finally:
            server.should_exit = True
            await asyncio.gather(server_task, return_exceptions=True)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--router-port", type=int, default=8137)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
