"""Execute the one approved natural-memory checkpoint-6 campaign, serially.

This is a single-use diagnostic. It rejects an existing output or ledger and
never resumes or rerolls an incomplete cell.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text as sql_text

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
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.request_budget import (
    BudgetedTransport,
    budget_ledger,
)
from ade_api.features.agent_runtime.resource_service import ResourceService
from ade_api.features.agent_runtime.router_transport import RouterTransport
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.features.agent_runtime.worker_health import RuntimeWorkerHealthService
from ade_api.features.prompt_center import build_prompt_template_reader
from ade_api.platform.settings import AdeApiSettings
from workflows.evals.deepseek_dev_smoke.isolation import isolated_database_url

from .natural_live_results import (
    capture_scope,
    remaining_turn_embedding_limit,
    require_mutation_state,
    sha256_file,
    stop_campaign_at,
    verify_attempt_safety,
    verify_allocation_counts,
    write_json,
)
from .natural_live_setup import seed_live_cell
from .natural_live_contract import (
    ROOT,
    EMBEDDING_ROUTE,
    EXPECTED_CASES_SHA256,
    EXPECTED_MATRIX_SHA256,
    _source_identity,
    _frozen_inputs,
    _branch,
    _current_text,
    _admitted_mutation_sources,
)
from .natural_live_transport import NaturalLiveTransport, RequestScope


async def _run(args: argparse.Namespace) -> None:
    checked_url, database_name = isolated_database_url(args.database_url)
    revision, fingerprint = _source_identity()
    cases, matrix, cells = _frozen_inputs()
    if args.output.exists() or args.ledger.exists():
        raise RuntimeError("campaign output and ledger must both be new")
    if not args.ledger.resolve().is_relative_to((ROOT / "data/runtime").resolve()):
        raise RuntimeError("campaign ledger must live in retained runtime data")
    engine = create_persistence_engine(checked_url)
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
    finally:
        await engine.dispose()

    args.output.mkdir(parents=True, exist_ok=False)
    args.output.chmod(0o700)
    os.environ.update(
        ADE_SOURCE_REVISION=revision,
        ADE_SOURCE_FINGERPRINT=fingerprint,
        ADE_SOURCE_DIRTY="false",
        ADE_NATURAL_MEMORY_CAPTURE="1",
    )
    settings = AdeApiSettings(
        _env_file=None,
        agent_runtime_enabled=True,
        agent_runtime_mode="development",
        database_url=checked_url,
        model_discovery_timeout_seconds=10,
        agent_runtime_worker_id=f"natural-c6-{uuid4().hex[:8]}",
        agent_runtime_budget_ledger_path=str(args.ledger),
        agent_runtime_budget_stage="natural-memory-checkpoint6-once",
        agent_runtime_budget_generation_limit=96,
        agent_runtime_budget_embedding_limit=160,
    )
    ledger = budget_ledger(settings)
    if ledger is None or ledger.counts() != {"generation": 0, "embedding": 0}:
        raise RuntimeError("new shared budget ledger was not initialized")
    transport = NaturalLiveTransport(
        BudgetedTransport(RouterTransport(args.router_url), ledger),
        capture_dir=args.output / "raw",
        generation_model=DEEPSEEK_ROUTE,
        embedding_model=EMBEDDING_ROUTE,
    )
    catalog = await transport.catalog(timeout_seconds=10)
    by_key = {item["model_key"]: item for item in catalog.get("items", [])}
    for route in (DEEPSEEK_ROUTE, EMBEDDING_ROUTE):
        item = by_key.get(route)
        if not item or not item.get("deployment"):
            raise RuntimeError(
                f"approved model route has no real pinned deployment: {route}"
            )
    manifest = {
        "schema_version": 1,
        "status": "running",
        "source_revision": revision,
        "source_fingerprint": fingerprint,
        "database": database_name,
        "ledger": str(args.ledger),
        "router_url": args.router_url,
        "routes": {
            route: by_key[route]["deployment"]["fingerprint"]["sha256"]
            for route in (DEEPSEEK_ROUTE, EMBEDDING_ROUTE)
        },
        "fixture_sha256": {
            "cases": EXPECTED_CASES_SHA256,
            "matrix": EXPECTED_MATRIX_SHA256,
        },
        "caps": {
            "generation": 96,
            "embedding": 160,
            "setup_embedding": 40,
            "turn_embedding": 120,
        },
        "cells": [],
        "unrun": [],
    }
    write_json(args.output / "manifest.json", manifest)
    engine = create_persistence_engine(checked_url)
    evidence_module.ARTIFACT_ROOT = args.output / "attempts"
    prompt_registry = build_prompt_template_reader(
        ROOT, persona_db_path=args.output / "personas.sqlite3"
    )
    database = RuntimeDatabase(engine)
    base_definitions = DefinitionService(
        database=database,
        settings=settings,
        prompt_registry=prompt_registry,
        router_transport=transport,
    )
    resources = ResourceService(database)
    health = RuntimeWorkerHealthService(engine=engine, settings=settings)
    service = RunService(
        database=database,
        settings=settings,
        router_transport=transport,
        worker_health=health,
    )
    worker = AgentRuntimeWorker(engine=engine, settings=settings, transport=transport)
    heartbeat_stop = asyncio.Event()
    await worker.presence.register()
    heartbeat = asyncio.create_task(worker.presence.heartbeat_forever(heartbeat_stop))
    setup_scope = RequestScope("scripted-setup-indexing", 0, 40)
    turn_embedding_used = 0
    generated_summaries: dict[str, tuple[str, int]] = {}
    stop_reason: str | None = None
    try:
        for index, (name, cell, fixture_variant) in enumerate(cells):
            variant = "B" if fixture_variant == "native" else fixture_variant
            branch = _branch(cases, cell)
            token = uuid4().hex[:12]
            result = {
                "cell": name,
                "fixture_variant": fixture_variant,
                "executed_policy": variant,
                "arc": cell["arc"],
                "branch": cell["branch"],
                "expected": cell["expected"],
                "forbidden": cell["forbidden"],
                "status": "started",
                "ledger_before": ledger.counts(),
            }
            manifest["cells"].append(result)
            write_json(args.output / "manifest.json", manifest)

            class BoundDefinitions:
                async def prepare(self, request, *, purpose):
                    prepared = await base_definitions.prepare(request, purpose=purpose)
                    prepared["memory_policy_version"] = (
                        f"natural-user-assertions-v2-{variant.casefold()}"
                    )
                    if cell["id"].startswith("pressure-"):
                        padding = (
                            "P"
                            * matrix["budgets"]["pressure"][
                                "synthetic_prompt_repeat_bytes"
                            ]
                        )
                        prepared["prompt_content"] += padding
                        prepared["prompt_sha256"] = hashlib.sha256(
                            prepared["prompt_content"].encode()
                        ).hexdigest()
                    return bind_checkpoint6_capacity(prepared)

            sessions = PurposeSessionService(
                database=database,
                definitions=BoundDefinitions(),
                purpose="evaluation",
                session_namespace="natural-checkpoint6",
            )
            try:
                session = await sessions.create(
                    CreateAgentStudioSessionRequest(
                        idempotency_key=f"natural-c6-{token}",
                        title=f"Synthetic natural {name}",
                        new_definition=CreateAgentDefinitionRequest(
                            definition_key=f"natural_c6_{index:02d}_{token}_{variant.casefold()}",
                            name=f"Synthetic natural {name}",
                            model_key=DEEPSEEK_ROUTE,
                            reviewer_model_key=DEEPSEEK_ROUTE,
                            embedding_model_key=EMBEDDING_ROUTE,
                            tool_names=["search_memory"],
                        ),
                        new_subject=CreateMemorySubjectRequest(
                            external_key=f"natural-c6-{token}",
                            display_name="Synthetic checkpoint-6 subject",
                        ),
                    )
                )
                result["session"] = {
                    "conversation_id": session["conversation"]["id"],
                    "subject_id": session["memory_subject"]["id"],
                    "definition_id": session["agent_definition"]["id"],
                    "deployment_snapshots": session["agent_definition"]["deployments"],
                }
                supplied = (
                    generated_summaries.get(cell["id"])
                    if fixture_variant in {"A0", "B"}
                    else None
                )
                setup_embedding_start = setup_scope.embedding_used
                with transport.scope(setup_scope):
                    seeded = await seed_live_cell(
                        engine,
                        session,
                        cell=cell,
                        branch=branch,
                        token=token,
                        transport=transport,
                        embedding_model=EMBEDDING_ROUTE,
                        summary_content=supplied[0] if supplied else "",
                        summary_through_sequence=supplied[1] if supplied else 2,
                    )
                result["scripted_setup"] = {
                    "history_message_ids": seeded.history_message_ids,
                    "fact_ids": seeded.fact_ids,
                    "notes": seeded.scripted_setup,
                    "provider_captures": capture_scope(
                        transport.capture_dir,
                        setup_scope,
                        embedding_start=setup_embedding_start,
                    ),
                    "supplied_summary_from_A": bool(supplied),
                    "prompt_pressure_padding_bytes": (
                        matrix["budgets"]["pressure"]["synthetic_prompt_repeat_bytes"]
                        if cell["id"].startswith("pressure-")
                        else 0
                    ),
                }
                verify_allocation_counts(
                    setup_used=setup_scope.embedding_used,
                    turn_used=turn_embedding_used,
                    total=ledger.counts()["embedding"],
                )
                accepted = await service.accept_turn(
                    session["conversation"]["id"],
                    AcceptTurnRequest(
                        content=_current_text(branch, cell),
                        idempotency_key=f"natural-c6-turn-{token}",
                        timeout_seconds=180,
                        retry_count=0,
                    ),
                )
                result["run_id"] = accepted["run_id"]
                extra_compaction = (
                    cell["kind"] == "diagnostic_summary" and fixture_variant == "A"
                )
                cell_scope = RequestScope(
                    name=name.replace("::", "-"),
                    generation_limit=4 if extra_compaction else 3,
                    embedding_limit=remaining_turn_embedding_limit(turn_embedding_used),
                )
                with transport.scope(cell_scope):
                    processed = await worker.process_once()
                turn_embedding_used += cell_scope.embedding_used
                verify_allocation_counts(
                    setup_used=setup_scope.embedding_used,
                    turn_used=turn_embedding_used,
                    total=ledger.counts()["embedding"],
                )
                if not processed:
                    raise RuntimeError("native worker did not process accepted run")
                result["provider_captures"] = capture_scope(
                    transport.capture_dir, cell_scope
                )
                after = ledger.counts()
                before = result["ledger_before"]
                if any(
                    after[kind] - before[kind]
                    != sum(item["kind"] == kind for item in result["provider_captures"])
                    + sum(
                        item["kind"] == kind
                        for item in result["scripted_setup"]["provider_captures"]
                    )
                    for kind in ("generation", "embedding")
                ):
                    raise RuntimeError(
                        "shared ledger and provider capture counts differ"
                    )
                run = await service.get_run(accepted["run_id"])
                memory = await resources.get_subject_memories(
                    session["memory_subject"]["id"], required_purpose="evaluation"
                )
                conversation = await resources.get_conversation_state(
                    session["conversation"]["id"], required_purpose="evaluation"
                )
                attempt_path = (
                    args.output / "attempts" / accepted["run_id"] / "attempt-001.json"
                )
                if not attempt_path.is_file():
                    raise RuntimeError("native attempt evidence is missing")
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
                    ledger_after=ledger.counts(),
                    safety=safety_reason,
                )
                if not safe:
                    raise RuntimeError(safety_reason)
                if fixture_variant == "native":
                    if not _admitted_mutation_sources(branch, cell, attempt):
                        raise RuntimeError(
                            "required native source spans were not admitted to generation and review"
                        )
                    require_mutation_state(
                        cell["id"],
                        facts=memory["facts"],
                        run_id=run["id"],
                        terminal=attempt["terminal_readback"],
                    )
                    result["status"] = "mutation_state_verified"
                else:
                    result["status"] = (
                        "pending_human_reply_review"
                        if attempt["terminal_readback"]["outcome"] == "committed"
                        else "response_attempt_rejected"
                    )
                if extra_compaction:
                    compacted = attempt.get("compaction_result", {})
                    if not compacted.get("summary_content"):
                        raise RuntimeError(
                            "required actual compaction evidence is absent"
                        )
                    generated_summaries[cell["id"]] = (
                        compacted["summary_content"],
                        int(compacted["summary_through_sequence"]),
                    )
                if ledger.exhausted():
                    raise RuntimeError("shared provider budget exhausted")
            except Exception as exc:
                stop_reason = stop_campaign_at(manifest, cells, index, exc)
            finally:
                result["ledger_after"] = ledger.counts()
                result["artifact_sha256"] = write_json(
                    args.output
                    / "cells"
                    / f"{index:02d}-{name.replace('::', '-')}.json",
                    result,
                )
                write_json(args.output / "manifest.json", manifest)
            if stop_reason:
                break
        manifest["status"] = (
            "stopped" if stop_reason else "completed_pending_human_review"
        )
        manifest["stop_reason"] = stop_reason
        manifest["ledger_final"] = ledger.counts()
        manifest["coverage"] = {
            "executed": len(manifest["cells"]),
            "scheduled": len(cells),
        }
        write_json(args.output / "manifest.json", manifest)
    finally:
        heartbeat_stop.set()
        await asyncio.gather(heartbeat, return_exceptions=True)
        await worker.presence.mark_stopped()
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--router-url", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
