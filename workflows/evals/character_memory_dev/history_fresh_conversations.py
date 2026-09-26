"""Chronological native conversations for the frozen fresh-fixture check."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from ade_api.features.agent_runtime.contracts import (
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
)
from ade_api.features.agent_runtime.history_native_rank import HISTORY_EMBEDDING_ROUTE

from .history_h4_run import _execute_turn
from .history_target_diagnostic_run import (
    fact_state,
    run_revisions,
    verified_turn_disposition,
)
from .natural_live_results import sha256_file, write_json
from .natural_live_transport import RequestScope


FRESH_FIXTURE = (
    Path(__file__).parent
    / "fixtures/history_recall/fresh_conversation_generalization.json"
)
FRESH_FIXTURE_SHA256 = (
    "ef59e3bcb43e044262c08e4e9f8b3c56e0aeb2d666577552457a2a9139901ae1"
)


def frozen_fresh_schedule(*, generation_binding_sha256: str, per_turn: dict) -> dict:
    if sha256_file(FRESH_FIXTURE) != FRESH_FIXTURE_SHA256:
        raise RuntimeError("fresh conversation fixture changed after offline freeze")
    schedule = json.loads(FRESH_FIXTURE.read_text())
    turns = schedule["trajectories"]
    if (
        schedule["status"] != "revised-offline-frozen-pending-director-review"
        or schedule["generation_binding_sha256"] != generation_binding_sha256
        or schedule["prompt_key"] != "chat_v20260926"
        or schedule["persona_key"] != "chat_linxiaotang"
        or schedule["policy"] != "natural-user-assertions-v4-b-history-probe"
        or schedule["arm"] != "automatic_history"
        or schedule["per_turn"] != per_turn
        or [item["id"] for item in turns]
        != [
            "location_correction_cross_chat",
            "two_exhibits_ambiguous_then_clear",
            "archived_pottery_outcome",
            "unrelated_turn_and_subject_boundary",
        ]
        or [len(item["turns"]) for item in turns] != [3, 4, 2, 3]
    ):
        raise RuntimeError("fresh conversation fixture differs from frozen binding")
    return schedule


async def execute_fresh_trajectory(
    *,
    trajectory: dict,
    index: int,
    sessions,
    service,
    resources,
    worker,
    engine,
    transport,
    output: Path,
    prompt_key: str,
) -> dict:
    """Create each chat at its first turn and retain native assistant history."""
    name = trajectory["id"]
    token = uuid4().hex[:12]
    result: dict = {
        "name": name,
        "status": "started",
        "turns": [],
        "subjects": {},
        "chats": {},
        "dispatch_before": transport.counts(),
    }
    primary = None
    chats: dict[tuple[str, str], dict] = {}
    for turn_index, planned in enumerate(trajectory["turns"]):
        subject_key = planned.get("subject", "primary")
        chat_key = planned["chat"]
        key = (subject_key, chat_key)
        if key not in chats:
            session_request = CreateAgentStudioSessionRequest(
                idempotency_key=f"fresh-{token}-{subject_key}-{chat_key}",
                title=f"Fresh diagnostic {name} {chat_key}",
                **(
                    {
                        "new_definition": CreateAgentDefinitionRequest(
                            definition_key=f"fresh_{index:02d}_{token}",
                            name=f"Fresh diagnostic {name}",
                            model_key="deepseek::deepseek-flash",
                            reviewer_model_key="deepseek::deepseek-flash",
                            embedding_model_key=HISTORY_EMBEDDING_ROUTE,
                            prompt_key=prompt_key,
                            tool_names=["search_memory"],
                        ),
                        "new_subject": CreateMemorySubjectRequest(
                            external_key=f"fresh-{token}",
                            display_name="Fresh diagnostic subject",
                        ),
                    }
                    if primary is None
                    else {
                        "agent_definition_id": primary["agent_definition"]["id"],
                        **(
                            {"memory_subject_id": primary["memory_subject"]["id"]}
                            if subject_key == "primary"
                            else {
                                "new_subject": CreateMemorySubjectRequest(
                                    external_key=f"fresh-isolated-{token}",
                                    display_name="Fresh isolated subject",
                                )
                            }
                        ),
                    }
                ),
            )
            session = await sessions.create(session_request)
            if primary is None:
                primary = session
                result["session"] = {
                    "definition_version_id": session["agent_definition"]["id"],
                    "prompt_sha256": session["agent_definition"]["prompt_sha256"],
                    "persona_sha256": session["agent_definition"]["persona_sha256"],
                }
            elif session["agent_definition"]["id"] != primary["agent_definition"]["id"]:
                raise RuntimeError("fresh chat changed definition version")
            elif (
                session["memory_subject"]["id"] == primary["memory_subject"]["id"]
            ) != (subject_key == "primary"):
                raise RuntimeError("fresh chat crossed the subject boundary")
            chats[key] = session
            result["subjects"][subject_key] = session["memory_subject"]["id"]
            result["chats"][chat_key] = {
                "subject": subject_key,
                "conversation_id": session["conversation"]["id"],
            }

        session = chats[key]
        subject_id = session["memory_subject"]["id"]
        conversation_id = session["conversation"]["id"]
        before = await fact_state(engine, subject_id)
        label = f"fresh-{index:02d}-{name}-{turn_index + 1}"
        turn = await _execute_turn(
            label=label,
            content=planned["user"],
            expected=None,
            arm="automatic_history",
            conversation_id=conversation_id,
            subject_id=subject_id,
            seeded_fact_ids={},
            service=service,
            resources=resources,
            worker=worker,
            engine=engine,
            transport=transport,
            output=output,
            scope=RequestScope(label),
        )
        disposition = verified_turn_disposition(turn)
        after = await fact_state(engine, subject_id)
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
                "subject": subject_key,
                "chat": chat_key,
                "user": planned["user"],
                "must": planned["must"],
                "must_not": planned["must_not"],
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
        if trajectory.get("archive_after") == chat_key:
            archived = await sessions.set_archived(conversation_id, archived=True)
            if archived["conversation"]["archived_at"] is None:
                raise RuntimeError("source chat did not archive")
            result["chats"][chat_key]["archived"] = True

    result["status"] = (
        "dependency_skip_after_verified_rejection"
        if len(result["turns"]) < len(trajectory["turns"])
        else "observed_with_verified_rejection"
        if result["turns"][-1]["disposition"] == "verified_rejection"
        else "observed"
    )
    result["unrun_dependency"] = trajectory["turns"][len(result["turns"]) :]
    result["dispatch_after"] = transport.counts()
    result["artifact_sha256"] = write_json(
        output / "trajectories" / f"{index:02d}-{name}.json", result
    )
    return result
