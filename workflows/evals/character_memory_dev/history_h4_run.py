"""One-shot native H4 paired history probe on a fresh isolated database."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, text as sql_text


from ade_api.features.agent_runtime.agent_studio_sessions import PurposeSessionService
from ade_api.features.agent_runtime.contracts import (
    AcceptTurnRequest,
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
)
from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.history_native_rank import (
    HISTORY_EMBEDDING_ROUTE,
    HISTORY_VECTOR_RECIPE,
)
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    memory_entities,
    run_events,
)
from ade_api.features.agent_runtime.resource_service import ResourceService
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from workflows.evals.deepseek_dev_smoke.isolation import (
    ROOT,
)

from .history_fixture_contract import validate_history_cases
from .history_h4_evidence import (
    capture_receipts,
    compare_expected_delta,
    mutation_delta,
    mutation_snapshot,
    paired_base_packet,
)
from .history_h4_seed import seed_history_case
from .natural_live_results import sha256_file, verify_attempt_safety, write_json
from .natural_live_transport import NaturalLiveTransport, RequestScope


FIXTURES = ROOT / "workflows/evals/character_memory_dev/fixtures/history_recall"
H2_RESULT = (
    ROOT
    / "workflows/evals/character_memory_dev/outputs/history-h2-ranking/development.json"
)
H2_RESULT_SHA256 = "8c6bc0ff6c648f05be0edcfd2834f34116f237d619e4531234ac13599142ba32"
QWEN_FINGERPRINT = "c549d7dc288d2112f10e8b1032b502eda74557d093bc1390fe0fc4f44de63086"
H2_CONTRACT_SHA256 = "4ac62cf6a3daf1335ff13492007b6ae1b90918920c56a979c41c39a669d98721"
H4_CASES_SHA256 = "7a402aa3b0dba6c0672515698248b511c214fa08ed37c94fc0db2b881d7886df"
H4_AMENDMENT = FIXTURES / "h4_reviewer_amendment.json"


def _frozen_inputs() -> tuple[dict, dict, dict]:
    h2_contract = json.loads((FIXTURES / "contract.json").read_text())
    fixture = json.loads((FIXTURES / "cases.json").read_text())
    amendment = json.loads(H4_AMENDMENT.read_text())
    if (
        sha256_file(FIXTURES / "contract.json") != H2_CONTRACT_SHA256
        or sha256_file(FIXTURES / "cases.json") != H4_CASES_SHA256
        or amendment
        != {
            "schema_version": 1,
            "status": "director-approved-h4-reviewer-envelope-2026-09-26",
            "h2_contract_sha256": H2_CONTRACT_SHA256,
            "h2_result_sha256": H2_RESULT_SHA256,
            "cases_sha256": H4_CASES_SHA256,
            "reviewer_context_tokens": 16384,
            "reviewer_output_tokens": 4096,
            "reviewer_safety_percent": 5,
            "reviewer_input_limit_tokens": 11469,
        }
        or h2_contract["binding"]["reviewer_input_limit_tokens"] != 6759
        or h2_contract["binding"]["reviewer_output_tokens"] != 4096
        or h2_contract["binding"]["generation_output_tokens"] != 4096
    ):
        raise RuntimeError("H4 amendment differs from approved H2-bound envelope")
    contract = deepcopy(h2_contract)
    contract["binding"]["reviewer_input_limit_tokens"] = amendment[
        "reviewer_input_limit_tokens"
    ]
    contract["h4_reviewer_amendment"] = amendment
    validate_history_cases(contract, fixture)
    if sha256_file(H2_RESULT) != H2_RESULT_SHA256:
        raise RuntimeError("H2 result differs from reviewed selection")
    h2 = json.loads(H2_RESULT.read_text())
    if (
        h2["contract_sha256"] != H2_CONTRACT_SHA256
        or h2["selection"]["selected"] != "probe_local_qwen_cosine"
        or h2["provider_identity"]["deployment_fingerprint"] != QWEN_FINGERPRINT
        or h2["vector_recipe"] != HISTORY_VECTOR_RECIPE
    ):
        raise RuntimeError("H2 selection or recipe differs from frozen H4 binding")
    return contract, fixture, h2


async def _fresh_database(url: str, name: str) -> None:
    engine = create_persistence_engine(url)
    try:
        async with engine.connect() as connection:
            identity = (
                await connection.execute(
                    sql_text("SELECT current_database(), current_user")
                )
            ).one()
            count = await connection.scalar(sql_text("SELECT count(*) FROM ade.runs"))
            extension_schema = await connection.scalar(
                sql_text(
                    "SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'"
                )
            )
            vector_distance = await connection.scalar(
                sql_text("SELECT '[1,0]'::vector <=> '[1,0]'::vector")
            )
        if (
            tuple(identity) != (name, "ade_owner")
            or count
            or extension_schema != "extensions"
            or vector_distance != 0
        ):
            raise RuntimeError("H4 requires a fresh migrated owner database")
        await RuntimeDatabase(engine).ensure_ready()
    finally:
        await engine.dispose()


async def _execute_cell(
    *,
    name: str,
    case: dict,
    target: dict,
    arm: str,
    sessions: PurposeSessionService,
    service: RunService,
    resources: ResourceService,
    workers: dict[str, AgentRuntimeWorker],
    engine,
    transport: NaturalLiveTransport,
    output: Path,
    index: int,
    through: str | None = None,
    empty_setup: bool = False,
) -> dict:
    token = uuid4().hex[:12]
    result: dict = {
        "name": name,
        "source_case": case["id"],
        "arm": arm,
        "status": "started",
        "expected": {
            key: target[key]
            for key in (
                "expected_delta",
                "expected_generation_advance",
                "expected_revision_count",
                "expected_entity_additions",
            )
        },
        "dispatch_before": transport.counts(),
    }
    scope = RequestScope(f"h4-{index:02d}-{name}-{arm}")
    try:
        session = await sessions.create(
            CreateAgentStudioSessionRequest(
                idempotency_key=f"h4-session-{token}",
                title=f"H4 {name} {arm}",
                new_definition=CreateAgentDefinitionRequest(
                    definition_key=f"h4_{index:02d}_{arm}_{token}",
                    name=f"H4 {name}",
                    model_key="deepseek::deepseek-flash",
                    reviewer_model_key="deepseek::deepseek-flash",
                    embedding_model_key=HISTORY_EMBEDDING_ROUTE,
                    tool_names=["search_memory"],
                ),
                new_subject=CreateMemorySubjectRequest(
                    external_key=f"h4-{token}",
                    display_name="H4 synthetic subject",
                ),
            )
        )
        result["session"] = {
            "conversation_id": session["conversation"]["id"],
            "subject_id": session["memory_subject"]["id"],
            "definition_version_id": session["agent_definition"]["id"],
            "prompt_sha256": session["agent_definition"]["prompt_sha256"],
            "persona_sha256": session["agent_definition"]["persona_sha256"],
        }
        with transport.scope(scope):
            seeded = await seed_history_case(
                engine,
                session,
                case=case,
                token=token,
                transport=transport,
                embedding_model=HISTORY_EMBEDDING_ROUTE,
                through=through,
                empty_setup=empty_setup,
            )
        result["setup"] = {
            "exchange_ids": seeded.exchange_ids,
            "message_ids": seeded.message_ids,
            "fact_ids": seeded.fact_ids,
            "memory_generation": seeded.memory_generation,
            "embedding_dispatches": seeded.setup_embedding_dispatches,
        }
        result["target"] = await _execute_turn(
            label=f"{name}-target",
            content=target.get("user") or target["target"]["user"],
            expected=target,
            arm=arm,
            conversation_id=seeded.target_conversation_id,
            subject_id=seeded.subject_id,
            seeded_fact_ids=seeded.fact_ids,
            service=service,
            resources=resources,
            worker=workers[arm],
            engine=engine,
            transport=transport,
            output=output,
            scope=RequestScope(f"h4-{index:02d}-{name}-{arm}-target"),
        )
        if case.get("followup") and result["target"]["status"] == "committed":
            result["followup"] = await _execute_turn(
                label=f"{name}-followup",
                content=case["followup"]["user"],
                expected=case["followup"],
                arm=arm,
                conversation_id=seeded.target_conversation_id,
                subject_id=seeded.subject_id,
                seeded_fact_ids=seeded.fact_ids,
                service=service,
                resources=resources,
                worker=workers[arm],
                engine=engine,
                transport=transport,
                output=output,
                scope=RequestScope(f"h4-{index:02d}-{name}-{arm}-followup"),
            )
        elif case.get("followup"):
            result["followup"] = {"status": "unrun_dependency"}
        result["status"] = (
            "observed" if result["target"]["status"] == "committed" else "rejected"
        )
    except Exception as exc:
        result["status"] = "failed"
        result["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        result["setup_captures"] = capture_receipts(transport.capture_dir, scope)
        result["dispatch_after"] = transport.counts()
        result["artifact_sha256"] = write_json(
            output / "cells" / f"{index:02d}-{name}-{arm}.json", result
        )
    return result


async def _execute_turn(
    *,
    label: str,
    content: str,
    expected: dict | None,
    arm: str,
    conversation_id: str,
    subject_id: str,
    seeded_fact_ids: dict[str, str],
    service: RunService,
    resources: ResourceService,
    worker: AgentRuntimeWorker,
    engine,
    transport: NaturalLiveTransport,
    output: Path,
    scope: RequestScope,
) -> dict:
    result: dict = {"status": "started", "user": content}
    before = await mutation_snapshot(engine, subject_id)
    accepted = await service.accept_turn(
        conversation_id,
        AcceptTurnRequest(
            content=content,
            idempotency_key=f"h4-turn-{uuid4().hex}",
            timeout_seconds=180,
            retry_count=0,
        ),
    )
    run_id = accepted["run_id"]
    result["run_id"] = run_id
    try:
        with transport.scope(scope):
            processed = await worker.process_once()
        if not processed:
            raise RuntimeError("native worker did not process accepted H4 run")
        run = await service.get_run(run_id)
        memory = await resources.get_subject_memories(
            subject_id, required_purpose="evaluation"
        )
        conversation = await resources.get_conversation_state(
            conversation_id, required_purpose="evaluation"
        )
        attempt_path = output / "attempts" / run_id / "attempt-001.json"
        if not attempt_path.is_file():
            raise RuntimeError("native attempt evidence is missing")
        attempt = json.loads(attempt_path.read_text())
        safe, safety = verify_attempt_safety(
            run=run, evidence=attempt, facts=memory["facts"]
        )
        observed = await mutation_delta(
            engine, subject_id=subject_id, run_id=run_id, before=before
        )
        async with engine.connect() as connection:
            subject_entity_id = await connection.scalar(
                select(memory_entities.c.id).where(
                    memory_entities.c.subject_id == subject_id,
                    memory_entities.c.kind == "subject",
                )
            )
            failure_payload = await connection.scalar(
                select(run_events.c.payload)
                .where(
                    run_events.c.run_id == run_id,
                    run_events.c.event_type == "run.failed",
                )
                .order_by(run_events.c.sequence.desc())
                .limit(1)
            )
        issues = (
            compare_expected_delta(
                observed,
                expected,
                seeded_fact_ids=seeded_fact_ids,
                subject_entity_id=str(subject_entity_id),
            )
            if expected is not None
            else None
        )
        result.update(
            status=(
                "committed"
                if safe and attempt["terminal_readback"]["outcome"] == "committed"
                else "rejected"
                if safe
                else "unsafe"
            ),
            run=run,
            memory=memory,
            conversation=conversation,
            attempt_artifact=str(attempt_path),
            attempt_sha256=sha256_file(attempt_path),
            terminal_safety=safety,
            terminal_outcome=attempt["terminal_readback"]["outcome"],
            failure_detail_code=(failure_payload or {}).get("error_detail_code"),
            observed_delta=observed,
            expected_delta_issues=issues,
            stage_evidence=attempt.get("history_selection"),
            base_packet=paired_base_packet(attempt),
        )
    except Exception as exc:
        result["status"] = "failed"
        result["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        result["provider_captures"] = capture_receipts(transport.capture_dir, scope)
        result["dispatch_after"] = transport.counts()
        result["artifact_sha256"] = write_json(
            output / "turns" / f"{label}-{arm}.json", result
        )
    return result
