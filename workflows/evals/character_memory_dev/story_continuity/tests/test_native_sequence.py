"""Scripted orchestration and safety tests, never native story qualification."""

import asyncio
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

from .. import native_artifacts as artifacts
from .. import native_sequence as sequence
from ..baseline import expected_catalog, ROLE_ROUTES
from ..native_artifacts import annotate, read, write_once
from ..schedule import frozen_schedule


def definition():
    deployments = []
    for role, route in ROLE_ROUTES.items():
        item = next(
            item
            for item in expected_catalog()["items"]
            if route in item["route_aliases"]
        )
        fingerprint = item["deployment"]["fingerprint"]
        deployments.append(
            {
                "role": role,
                "route_alias": route,
                "fingerprint": fingerprint["sha256"],
                "fingerprint_payload": fingerprint,
            }
        )
    return {
        "id": "v1",
        "agent_definition_id": "root",
        "version": 1,
        "prompt_key": "chat_v20260926",
        "persona_key": "chat_linxiaotang",
        "prompt_sha256": "p",
        "persona_sha256": "b",
        "tool_names": ["search_memory"],
        "memory_policy_version": "natural-user-assertions-v4-b-history-probe",
        "qualification_state": "unqualified",
        "deployments": deployments,
    }


def session():
    return {
        "agent_definition": definition(),
        "memory_subject": {"id": "s"},
        "conversation": {
            "id": "c",
            "agent_definition_id": "v1",
            "memory_subject_id": "s",
            "purpose": "evaluation",
            "archived_at": None,
        },
        "latest_run": None,
    }


def origin():
    return {
        "validation": {"disposition": "committed"},
        "readback": {
            "run": {"id": "r1", "status": "succeeded", "conversation_id": "c"},
            "state": {
                "messages": [
                    {"run_id": "r1", "role": "assistant", "content": "A solo walk."}
                ]
            },
            "definition_version_id": "v1",
        },
        "scope": {
            "subject": "s",
            "root": "root",
            "purpose": "evaluation",
            "workspace": sequence.WORKSPACE_ID,
        },
    }


def human():
    return {
        "reviewer_kind": "human",
        "reviewer": "synthetic test operator",
        "usable": True,
        "quotes": ["solo walk"],
        "rationale": "Explicit solo event in this scripted control.",
        "replacement_suggestion": "a shared walk",
    }


def test_immutable_receipts_and_clean_source_gate(tmp_path, monkeypatch):
    write_once(tmp_path / "receipt.json", {"first": True})
    with pytest.raises(FileExistsError):
        write_once(tmp_path / "receipt.json", {"replacement": True})
    assert read(tmp_path / "receipt.json") == {"first": True}
    monkeypatch.setattr(
        artifacts.subprocess, "check_output", lambda *a, **k: b" M changed.py"
    )
    with pytest.raises(ValueError, match="Commit"):
        artifacts.clean_preparation()


def test_changed_source_cannot_resume(tmp_path, monkeypatch):
    write_once(tmp_path / "preparation.json", {"source_revision": "one"})
    monkeypatch.setattr(
        artifacts, "clean_preparation", lambda: {"source_revision": "two"}
    )
    with pytest.raises(ValueError, match="changed"):
        artifacts.check_preparation(tmp_path)


def test_human_annotation_gate_and_no_late_annotation(tmp_path):
    record = origin()
    write_once(tmp_path / "turn-01.json", record)
    with pytest.raises(ValueError, match="Human annotation required"):
        sequence.prior_evidence(tmp_path, 2)
    annotated = annotate(tmp_path, 1, human())
    assert annotated["usable"]
    outcomes, ledger = sequence.prior_evidence(tmp_path, 2)
    assert outcomes[1]["usable_annotation"]
    assert ledger["r1"]["messages"][0]["content"] == "A solo walk."
    write_once(tmp_path / "turn-02.intent.json", {})
    with pytest.raises(ValueError, match="later dispatch"):
        annotate(tmp_path, 1, human())


def test_agent_cannot_claim_human_annotation(tmp_path):
    write_once(tmp_path / "turn-01.json", origin())
    supplied = {**human(), "reviewer_kind": "agent"}
    with pytest.raises(ValueError, match="human"):
        annotate(tmp_path, 1, supplied)
    supplied = {**human(), "quotes": ["not in the actual reply"]}
    with pytest.raises(ValueError, match="actual reply"):
        annotate(tmp_path, 1, supplied)


def test_no_usable_origin_leaves_dependent_turns_unassessable(tmp_path):
    write_once(tmp_path / "turn-01.json", origin())
    annotate(
        tmp_path, 1, {**human(), "usable": False, "rationale": "No established event."}
    )
    write_once(tmp_path / "turn-02.json", {"validation": {"disposition": "committed"}})
    api = AsyncMock()
    result = asyncio.run(
        sequence.execute_turn(api, tmp_path, frozen_schedule()["turns"][2])
    )
    assert result["validation"]["disposition"] == "unassessable_dependency"
    api.request.assert_not_called()


def test_uncertain_submission_is_never_retried(tmp_path, monkeypatch):
    write_once(tmp_path / "database.json", {"token": "test"})
    monkeypatch.setattr(sequence, "session_for", AsyncMock(return_value=session()))
    monkeypatch.setattr(sequence, "check_preparation", lambda *_: {})
    api = AsyncMock()
    api.request.side_effect = [
        {"subject_id": "s", "facts": []},
        TimeoutError("uncertain"),
    ]
    turn = frozen_schedule()["turns"][0]
    with pytest.raises(TimeoutError, match="uncertain"):
        asyncio.run(sequence.execute_turn(api, tmp_path, turn))
    intent = read(tmp_path / "turn-01.intent.json")
    assert intent["request"]["content"] == turn["prompt"]
    assert intent["request"]["retry_count"] == 0
    assert intent["request"]["timeout_seconds"] == 180
    with pytest.raises(ValueError, match="never reroll"):
        asyncio.run(sequence.execute_turn(api, tmp_path, turn))
    assert (
        len([call for call in api.request.call_args_list if call.args[0] == "POST"])
        == 1
    )


def test_mutable_latest_run_does_not_change_session_binding(tmp_path):
    original = session()
    write_once(tmp_path / "session-origin.json", original)
    current = deepcopy(original)
    current["latest_run"] = {"id": "r1", "status": "succeeded"}
    api = AsyncMock()
    api.request.return_value = current
    actual = asyncio.run(
        sequence.session_for(api, tmp_path, frozen_schedule()["turns"][1])
    )
    assert actual == original
    current["agent_definition"]["id"] = "wrong-version"
    with pytest.raises(ValueError, match="session changed"):
        asyncio.run(sequence.session_for(api, tmp_path, frozen_schedule()["turns"][1]))


def test_version_two_uses_public_version_then_session_requests(tmp_path):
    write_once(tmp_path / "database.json", {"token": "test"})
    write_once(tmp_path / "session-origin.json", session())
    version = {**definition(), "id": "v2", "version": 2}
    updated = session()
    updated["agent_definition"] = version
    updated["conversation"].update(id="new", agent_definition_id="v2")
    api = AsyncMock()
    api.request.side_effect = [version, updated]
    actual = asyncio.run(
        sequence.session_for(api, tmp_path, frozen_schedule()["turns"][6])
    )
    assert actual["agent_definition"]["id"] == "v2"
    first, second = api.request.call_args_list
    assert first.args[1] == "/api/v3/history-trial/definitions/root/versions"
    assert first.args[2]["expected_current_version"] == 1
    assert second.args[1] == "/api/v3/history-trial/sessions"
    assert second.args[2]["agent_definition_id"] == "v2"
    assert "new_definition" not in second.args[2]


@pytest.mark.parametrize("change", ["role", "payload", "route", "persona"])
def test_definition_drift_rejected(change):
    primary = definition()
    changed = deepcopy(primary)
    if change == "role":
        changed["deployments"][0]["role"] = "retriever"
    elif change == "payload":
        changed["deployments"][0]["fingerprint_payload"]["model"] = "different-model"
    elif change == "route":
        changed["deployments"][0]["route_alias"] = "different-route"
    else:
        changed["persona_sha256"] = "changed-biography"
    with pytest.raises(ValueError):
        sequence.validate_definition(changed, primary)


def test_run_stops_at_origin_annotation_without_observing_turn_two(
    tmp_path, monkeypatch
):
    launch = tmp_path / "launch"
    launch.mkdir()
    api = AsyncMock()
    api.request.return_value = {"runtime": "ade_native", "max_retry_count": 0}
    execute = AsyncMock(return_value=origin())
    monkeypatch.setattr(sequence, "execute_turn", execute)
    result = asyncio.run(sequence.run_sequence(api, tmp_path, launch))
    assert result == {
        "status": "human_annotation_required",
        "turn": 1,
        "reply": "A solo walk.",
    }
    assert execute.await_count == 1


def test_evidence_failure_stops_further_dispatch(tmp_path, monkeypatch):
    launch = tmp_path / "launch"
    launch.mkdir()
    api = AsyncMock()
    api.request.return_value = {"runtime": "ade_native", "max_retry_count": 0}
    execute = AsyncMock(
        return_value={"validation": {"disposition": "evidence_failure"}}
    )
    monkeypatch.setattr(sequence, "execute_turn", execute)
    result = asyncio.run(sequence.run_sequence(api, tmp_path, launch))
    assert result["status"] == "stopped_evidence_failure"
    assert execute.await_count == 1
