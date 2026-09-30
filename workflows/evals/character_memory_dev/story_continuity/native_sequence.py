"""Frozen native schedule over public ADE HTTP, with no automatic resubmission."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from model_catalog_contracts.deployment_manifest import DeploymentFingerprint

from .baseline import ROLE_ROUTES, preparation_binding
from .evidence import checked_capture, validate_turn
from .native_artifacts import (
    OUTPUTS,
    annotation_for,
    check_preparation,
    delivered_reply,
    read,
    reviewer_kind,
    write_once,
)
from .native_transport import NativeADE
from .schedule import dependency_status, digest, frozen_schedule, prompt_for

WORKSPACE_ID = str(uuid5(NAMESPACE_URL, "ade://workspace/default"))


def validate_definition(definition: dict, primary: dict | None = None) -> None:
    roles = preparation_binding()["roles"]
    deployments = definition["deployments"]
    if (
        definition["prompt_key"] != "chat_v20260926"
        or definition["persona_key"] != "chat_linxiaotang"
        or definition["tool_names"] != ["search_memory"]
        or definition["memory_policy_version"]
        != "natural-user-assertions-v4-b-history-probe"
        or definition["qualification_state"] != "unqualified"
        or len(deployments) != 3
        or {item["role"] for item in deployments} != set(roles)
    ):
        raise ValueError("Immutable definition differs from the frozen native baseline")
    for item in deployments:
        expected = roles[item["role"]]
        payload = item["fingerprint_payload"]
        if (
            item["route_alias"] != expected["route"]
            or item["fingerprint"] != expected["deployment_fingerprint"]
            or payload.get("sha256") != item["fingerprint"]
            or DeploymentFingerprint.from_payload(
                {key: value for key, value in payload.items() if key != "sha256"}
            ).sha256
            != expected["deployment_fingerprint"]
        ):
            raise ValueError("Immutable definition deployment drift")
    if primary and any(
        definition[key] != primary[key]
        for key in (
            "prompt_sha256",
            "persona_sha256",
            "deployments",
            "tool_names",
            "memory_policy_version",
        )
    ):
        raise ValueError(
            "Ordinary version/root changed the baseline biography or models"
        )


def definition_request(token: str) -> dict:
    return {
        "definition_key": f"pc11_{token}",
        "name": "PC11 native baseline",
        "model_key": ROLE_ROUTES["conversation"],
        "reviewer_model_key": ROLE_ROUTES["reviewer"],
        "embedding_model_key": ROLE_ROUTES["retriever"],
        "prompt_key": "chat_v20260926",
        "persona_key": "chat_linxiaotang",
        "tool_names": ["search_memory"],
    }


async def session_for(api: NativeADE, directory: Path, turn: dict) -> dict:
    path = directory / f"session-{turn['chat']}.json"
    if path.exists():
        session = read(path)
        current = await api.request(
            "GET", f"/api/v3/history-trial/sessions/{session['conversation']['id']}"
        )
        if (
            current["agent_definition"] != session["agent_definition"]
            or current["memory_subject"]["id"] != session["memory_subject"]["id"]
            or any(
                current["conversation"][key] != session["conversation"][key]
                for key in (
                    "id",
                    "agent_definition_id",
                    "memory_subject_id",
                    "purpose",
                    "archived_at",
                )
            )
        ):
            raise ValueError("Previously bound native session changed")
        return session
    token = read(directory / "database.json")["token"]
    request = {"idempotency_key": f"pc11-{token}-{turn['id']}"}
    primary_path = directory / "session-origin.json"
    primary = read(primary_path) if primary_path.exists() else None
    definition = definition_request(token)
    if primary is None or turn["id"] == 10:
        if primary:
            definition["definition_key"] += "_other"
        request["new_definition"] = definition
    elif turn["id"] == 7:
        version_path = directory / "version-02.json"
        if version_path.exists():
            version = read(version_path)
        else:
            root = primary["agent_definition"]["agent_definition_id"]
            definition.update(
                name="PC11 native version two", expected_current_version=1
            )
            version = await api.request(
                "POST", f"/api/v3/history-trial/definitions/{root}/versions", definition
            )
            write_once(version_path, version)
        validate_definition(version, primary["agent_definition"])
        if (
            version["version"] != 2
            or version["agent_definition_id"]
            != primary["agent_definition"]["agent_definition_id"]
        ):
            raise ValueError("Ordinary immutable version binding differs")
        request["agent_definition_id"] = version["id"]
    else:
        bound = (
            read(directory / "session-archive_callback.json")
            if turn["id"] == 9
            else primary
        )
        request["agent_definition_id"] = bound["agent_definition"]["id"]
    if primary and turn["subject"] == "primary":
        request["memory_subject_id"] = primary["memory_subject"]["id"]
    else:
        request["new_subject"] = {"external_key": f"pc11-{token}-{turn['subject']}"}
    session = await api.request("POST", "/api/v3/history-trial/sessions", request)
    write_once(path, session)
    validate_definition(
        session["agent_definition"], primary["agent_definition"] if primary else None
    )
    if (
        session["conversation"]["purpose"] != "evaluation"
        or session["agent_definition"]["version"] != turn["version"]
    ):
        raise ValueError("Native session purpose/version mismatch")
    if primary:
        same_subject = (
            session["memory_subject"]["id"] == primary["memory_subject"]["id"]
        )
        same_root = (
            session["agent_definition"]["agent_definition_id"]
            == primary["agent_definition"]["agent_definition_id"]
        )
        if same_subject != (turn["subject"] == "primary") or same_root != (
            turn["root"] == "xiaotang"
        ):
            raise ValueError("Native subject/root isolation binding differs")
    return session


def prior_evidence(directory: Path, before: int) -> tuple[dict, dict]:
    outcomes, ledger = {}, {}
    archived = {
        read(path)["conversation"]["id"] for path in directory.glob("archive-*.json")
    }
    for number in range(1, before):
        record = read(directory / f"turn-{number:02d}.json")
        result = dict(record["validation"])
        if result["disposition"] == "evidence_failure":
            raise ValueError("Prior integrity/capture failure stops native dispatch")
        outcomes[number] = result
        if "readback" not in record:
            continue
        if number in {1, 3} and result["disposition"] == "committed":
            annotation = annotation_for(directory, number, record)
            if annotation is None:
                raise ValueError(
                    f"Human annotation required after turn {number}"
                    if reviewer_kind(directory) == "human"
                    else f"Agent annotation required after turn {number}"
                )
            result["usable_annotation"] = annotation["usable"]
        run = record["readback"]["run"]
        ledger[run["id"]] = {
            "status": run["status"],
            "scope": record["scope"],
            "ordinal": number,
            "archived": run["conversation_id"] in archived,
            "conversation_id": run["conversation_id"],
            "definition_version_id": record["readback"]["definition_version_id"],
            "messages": [
                {**message, "content_sha256": digest(message["content"].encode())}
                for message in record["readback"]["state"]["messages"]
                if message["run_id"] == run["id"]
            ],
        }
    return outcomes, ledger


async def capture_for(
    run_id: str, policy: str, directory: Path, number: int
) -> tuple[dict, str]:
    UUID(run_id)
    source = OUTPUTS / "natural-memory-attempts" / run_id / "attempt-001.json"
    deadline = time.monotonic() + 20
    while not source.exists() and time.monotonic() < deadline:
        await asyncio.sleep(0.2)
    if source.is_symlink() or source.parent.is_symlink() or not source.exists():
        raise ValueError("Missing or unsafe private capture; stop native assessment")
    raw = source.read_bytes()
    with (directory / f"capture-{number:02d}.json").open("xb") as stream:
        stream.write(raw)
    sha256 = digest(raw)
    return checked_capture(raw, sha256=sha256, run_id=run_id, policy=policy), sha256


async def execute_turn(api: NativeADE, directory: Path, turn: dict) -> dict:
    number = turn["id"]
    outcomes, ledger = prior_evidence(directory, number)
    target = directory / f"turn-{number:02d}.json"
    if target.exists() or (directory / f"turn-{number:02d}.intent.json").exists():
        raise ValueError("Turn already recorded or submission uncertain; never reroll")
    if dependency_status(turn, outcomes) == "unassessable_dependency":
        record = {"validation": {"disposition": "unassessable_dependency"}}
        write_once(target, record)
        return record
    for chat in turn.get("archive_before", []):
        archived_path = directory / f"archive-{chat}.json"
        source = read(directory / f"session-{chat}.json")
        cid = source["conversation"]["id"]
        if not archived_path.exists():
            archived = await api.request(
                "DELETE", f"/api/v3/history-trial/sessions/{cid}"
            )
            if (
                archived["conversation"]["id"] != cid
                or not archived["conversation"]["archived_at"]
            ):
                raise ValueError("Source conversation was not archived")
            write_once(archived_path, archived)
    _, ledger = prior_evidence(directory, number)
    session = await session_for(api, directory, turn)
    cid, sid = session["conversation"]["id"], session["memory_subject"]["id"]
    scope = {
        "subject": sid,
        "root": session["agent_definition"]["agent_definition_id"],
        "purpose": "evaluation",
        "workspace": WORKSPACE_ID,
    }
    suggestion = None
    if number == 4:
        origin = read(directory / "turn-01.json")
        suggestion = annotation_for(directory, 1, origin)["annotation"][
            "replacement_suggestion"
        ]
    prompt = prompt_for(turn, replacement_suggestion=suggestion)
    before = await api.request("GET", f"/api/v3/history-trial/subjects/{sid}/memories")
    write_once(directory / f"before-{number:02d}.json", before)
    check_preparation(directory)
    request = {
        "content": prompt,
        "idempotency_key": f"pc11-turn-{read(directory / 'database.json')['token']}-{number}",
        "retry_count": 0,
        "timeout_seconds": 180,
    }
    write_once(
        directory / f"turn-{number:02d}.intent.json",
        {"conversation_id": cid, "request": request},
    )
    accepted = await api.request("POST", f"/api/v3/conversations/{cid}/turns", request)
    write_once(directory / f"accepted-{number:02d}.json", accepted)
    run = await api.wait_terminal(accepted["run_id"])
    readback = await api.readback(cid, sid, run)
    readback.update(
        ordinal=number, definition_version_id=session["agent_definition"]["id"]
    )
    write_once(directory / f"readback-{number:02d}.json", readback)
    record = {"readback": readback, "scope": scope, "session": session}
    try:
        capture, sha256 = await capture_for(
            run["id"],
            session["agent_definition"]["memory_policy_version"],
            directory,
            number,
        )
        record["capture_sha256"] = sha256
        origin = (
            read(directory / "turn-01.json")["readback"]["run"]["id"]
            if turn["depends_on"]
            else None
        )
        record["validation"] = validate_turn(
            capture=capture,
            readback=readback,
            before_memories=before,
            expected_prompt=prompt,
            source_ledger=ledger,
            target_scope=scope,
            origin_run_id=origin,
            archive_probe=number == 7,
            evidence_kind="native",
        )
        record["provider_request_counts"] = capture["provider_request_counts"]
    except (ValueError, KeyError) as exc:
        record["validation"] = {
            "disposition": "evidence_failure",
            "reason": str(exc),
            "semantic": "not_assessed",
        }
    write_once(target, record)
    return record


async def run_sequence(api: NativeADE, directory: Path, launch: Path) -> dict:
    options = await api.request("GET", "/api/v3/history-trial/options")
    write_once(launch / "options.json", options)
    if options["runtime"] != "ade_native" or options["max_retry_count"] != 0:
        raise ValueError("Native history trial options differ")
    for turn in frozen_schedule()["turns"]:
        path = directory / f"turn-{turn['id']:02d}.json"
        result = (
            read(path) if path.exists() else await execute_turn(api, directory, turn)
        )
        disposition = result["validation"]["disposition"]
        if disposition == "evidence_failure":
            return {
                "status": "stopped_evidence_failure",
                "turn": turn["id"],
                "validation": result["validation"],
            }
        if turn["id"] in {1, 3} and disposition == "committed":
            if annotation_for(directory, turn["id"], result) is None:
                return {
                    "status": f"{reviewer_kind(directory)}_annotation_required",
                    "turn": turn["id"],
                    "reply": delivered_reply(result),
                }
    return {
        "status": "sequence_complete",
        "semantic": f"{reviewer_kind(directory)}_review_required",
    }
