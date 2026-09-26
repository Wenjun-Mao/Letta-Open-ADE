"""Native turn execution and independent readback for the seven-turn diagnostic."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from ade_api.features.agent_runtime.contracts import (
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
)
from ade_api.features.agent_runtime.history_native_rank import HISTORY_EMBEDDING_ROUTE
from ade_api.features.agent_runtime.persistence.metadata import (
    memory_facts,
    memory_revision_sources,
    memory_revisions,
)

from .history_h4_run import _execute_turn
from .history_h4_evidence import capture_receipts
from .history_h4_seed import seed_history_case
from .natural_live_results import write_json
from .natural_live_transport import RequestScope


async def fact_state(engine, subject_id: str) -> list[dict]:
    """Read every fact, including forgotten records absent from the active packet."""
    async with engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    select(
                        memory_facts.c.id,
                        memory_facts.c.entity_id,
                        memory_facts.c.fact_type,
                        memory_facts.c.qualifier,
                        memory_facts.c.value,
                        memory_facts.c.status,
                        memory_facts.c.version,
                        memory_facts.c.current_revision_id,
                    )
                    .where(memory_facts.c.subject_id == subject_id)
                    .order_by(memory_facts.c.created_at, memory_facts.c.id)
                )
            )
            .mappings()
            .all()
        )
    return [
        {
            **row,
            "id": str(row["id"]),
            "entity_id": str(row["entity_id"]),
            "current_revision_id": str(row["current_revision_id"]),
        }
        for row in rows
    ]


async def run_revisions(engine, run_id: str) -> list[dict]:
    """Read committed revisions and complete bound source coordinates directly."""
    async with engine.connect() as connection:
        revisions = (
            (
                await connection.execute(
                    select(memory_revisions)
                    .where(memory_revisions.c.run_id == run_id)
                    .order_by(memory_revisions.c.created_at, memory_revisions.c.id)
                )
            )
            .mappings()
            .all()
        )
        result = []
        for revision in revisions:
            sources = (
                (
                    await connection.execute(
                        select(memory_revision_sources)
                        .where(memory_revision_sources.c.revision_id == revision["id"])
                        .order_by(memory_revision_sources.c.id)
                    )
                )
                .mappings()
                .all()
            )
            result.append(
                {
                    "id": str(revision["id"]),
                    "fact_id": str(revision["fact_id"]),
                    "operation": revision["operation"],
                    "reason": revision["reason"],
                    "value": revision["value"],
                    "fact_version": revision["fact_version"],
                    "sources": [
                        {
                            "message_id": str(source["message_id"]),
                            "start_char": source["start_char"],
                            "end_char": source["end_char"],
                            "quote": source["quote"],
                            "message_sha256": source["message_sha256"],
                            "authority_role": source["authority_role"],
                        }
                        for source in sources
                    ],
                }
            )
    return result


def verified_turn_disposition(turn: dict) -> str:
    """Continue independent cases only after terminal integrity is established."""
    receipts = turn.get("provider_captures") or []
    complete = (
        turn.get("terminal_safety") == "verified"
        and bool(turn.get("attempt_sha256"))
        and receipts
        and all(item.get("status") == "completed" for item in receipts)
    )
    if not complete:
        raise RuntimeError("native turn evidence is incomplete")
    delta = turn["observed_delta"]
    if turn["status"] == "committed" and turn["terminal_outcome"] == "committed":
        return "committed"
    if (
        turn["status"] == "rejected"
        and turn["terminal_outcome"] == "confirmed_rejection"
        and turn["run"]["status"] == "failed"
        and delta["generation_advance"] == 0
        and delta["revision_count"] == 0
        and not delta["run_revisions"]
        and not delta["other_revision_ids"]
        and not delta["entity_additions"]
    ):
        return "verified_rejection"
    raise RuntimeError("native turn has inconsistent terminal or mutation evidence")


async def execute_trajectory(
    *,
    trajectory: dict,
    case: dict,
    index: int,
    sessions,
    service,
    resources,
    worker,
    engine,
    transport,
    output: Path,
) -> dict:
    """Run one new subject serially; a rejected first turn blocks its followup."""
    name = trajectory["id"]
    token = uuid4().hex[:12]
    result: dict = {
        "name": name,
        "source_case": case["id"],
        "status": "started",
        "turns": [],
        "dispatch_before": transport.counts(),
    }
    setup_scope = RequestScope(f"target-{index:02d}-{name}-setup")
    session = await sessions.create(
        CreateAgentStudioSessionRequest(
            idempotency_key=f"target-session-{token}",
            title=f"Target diagnostic {name}",
            new_definition=CreateAgentDefinitionRequest(
                definition_key=f"target_{index:02d}_{token}",
                name=f"Target diagnostic {name}",
                model_key="deepseek::deepseek-flash",
                reviewer_model_key="deepseek::deepseek-flash",
                embedding_model_key=HISTORY_EMBEDDING_ROUTE,
                tool_names=["search_memory"],
            ),
            new_subject=CreateMemorySubjectRequest(
                external_key=f"target-{token}",
                display_name="Target diagnostic synthetic subject",
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
    with transport.scope(setup_scope):
        seeded = await seed_history_case(
            engine,
            session,
            case=case,
            token=token,
            transport=transport,
            embedding_model=HISTORY_EMBEDDING_ROUTE,
        )
    result["setup"] = {
        "exchange_ids": seeded.exchange_ids,
        "message_ids": seeded.message_ids,
        "fact_ids": seeded.fact_ids,
        "memory_generation": seeded.memory_generation,
        "embedding_dispatches": seeded.setup_embedding_dispatches,
    }
    result["setup_captures"] = capture_receipts(transport.capture_dir, setup_scope)
    if any(item["status"] != "completed" for item in result["setup_captures"]):
        raise RuntimeError("setup provider capture is incomplete")
    for turn_index, planned in enumerate(trajectory["turns"]):
        before = await fact_state(engine, seeded.subject_id)
        label = f"target-{index:02d}-{name}-{turn_index + 1}"
        turn = await _execute_turn(
            label=label,
            content=planned["user"],
            expected=None,
            arm="automatic_history",
            conversation_id=seeded.target_conversation_id,
            subject_id=seeded.subject_id,
            seeded_fact_ids=seeded.fact_ids,
            service=service,
            resources=resources,
            worker=worker,
            engine=engine,
            transport=transport,
            output=output,
            scope=RequestScope(label),
        )
        disposition = verified_turn_disposition(turn)
        after = await fact_state(engine, seeded.subject_id)
        revisions = await run_revisions(engine, turn["run_id"])
        if {item["id"] for item in revisions} != {
            item["id"] for item in turn["observed_delta"]["run_revisions"]
        }:
            raise RuntimeError("independent revision readback differs from turn delta")
        if disposition == "verified_rejection" and before != after:
            raise RuntimeError("rejected turn changed held facts")
        attempt = json.loads(Path(turn["attempt_artifact"]).read_text())
        packet = attempt.get("reviewer_request", {}).get("messages", [])
        history = (
            json.loads(packet[1]["content"]).get("history", [])
            if len(packet) > 1
            else []
        )
        result["turns"].append(
            {
                "user": planned["user"],
                "expectation": planned["expect"],
                "disposition": disposition,
                "run_id": turn["run_id"],
                "attempt_sha256": turn["attempt_sha256"],
                "turn_artifact_sha256": turn["artifact_sha256"],
                "terminal_outcome": turn["terminal_outcome"],
                "failure_detail_code": turn["failure_detail_code"],
                "before_facts": before,
                "after_facts": after,
                "run_revisions": revisions,
                "observed_delta": turn["observed_delta"],
                "history_selection": turn["stage_evidence"],
                "admitted_history": history,
                "reviewer_decision": attempt.get("reviewer_decision"),
                "candidate_reply": attempt.get("candidate_visible_reply"),
                "delivered_reply": (
                    attempt.get("candidate_visible_reply")
                    if disposition == "committed"
                    else None
                ),
                "provider_captures": turn["provider_captures"],
                "dispatch_after": turn["dispatch_after"],
            }
        )
        write_json(output / "trajectories" / f"{index:02d}-{name}.json", result)
        if disposition != "committed":
            break
    if len(result["turns"]) != len(trajectory["turns"]):
        result["status"] = "dependency_skip_after_verified_rejection"
        result["unrun_dependency"] = trajectory["turns"][len(result["turns"]) :]
    else:
        result["status"] = "observed"
    result["dispatch_after"] = transport.counts()
    result["artifact_sha256"] = write_json(
        output / "trajectories" / f"{index:02d}-{name}.json", result
    )
    return result
