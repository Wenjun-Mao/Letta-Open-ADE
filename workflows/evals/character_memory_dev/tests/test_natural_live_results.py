from __future__ import annotations

import json

import pytest

from workflows.evals.character_memory_dev.natural_live_results import (
    capture_scope,
    mutation_state_matches,
    require_mutation_state,
    stop_campaign_at,
)
from workflows.evals.character_memory_dev.natural_live_transport import RequestScope


def test_capture_scope_requires_one_completed_file_per_observed_request(
    tmp_path,
) -> None:
    scope = RequestScope("cell-a")
    scope.observe("generation")
    path = tmp_path / "cell-a-generation-001.json"
    path.write_text(
        json.dumps(
            {
                "scope": "cell-a",
                "kind": "generation",
                "number": 1,
                "outcome": "completed",
            }
        )
    )
    assert len(capture_scope(tmp_path, scope)) == 1

    scope.observe("embedding")
    with pytest.raises(RuntimeError, match="missing embedding"):
        capture_scope(tmp_path, scope)
    (tmp_path / "cell-a-embedding-001.json").write_text(
        json.dumps(
            {"scope": "cell-a", "kind": "embedding", "number": 1, "outcome": "failed"}
        )
    )
    with pytest.raises(RuntimeError, match="failed or invalid embedding"):
        capture_scope(tmp_path, scope)


RUN = "run-current"


def _revision(
    revision_id,
    *,
    operation="add",
    run_id=RUN,
    reason=None,
    value="",
    predecessors=(),
    roles=("user_assertion",),
    quote="user said this",
):
    return {
        "id": revision_id,
        "operation": operation,
        "run_id": run_id,
        "reason": reason,
        "value": value,
        "predecessor_revision_ids": list(predecessors),
        "evidence": [{"authority_role": role, "quote": quote} for role in roles],
    }


def _fact(fact_id, fact_type, status, value, revisions, *, entity_id="subject"):
    return {
        "id": fact_id,
        "fact_type": fact_type,
        "status": status,
        "value": value,
        "entity_id": entity_id,
        "revisions": revisions,
    }


def _terminal(*revision_ids, outcome="committed"):
    return {"outcome": outcome, "revision_ids": list(revision_ids)}


def test_scoped_addition_requires_morning_and_evening_separate_assertions() -> None:
    coffee = _fact(
        "coffee",
        "person.preference",
        "active",
        "早上喜欢喝咖啡",
        [_revision("old", run_id="seed")],
    )
    flower = _fact(
        "flower", "person.preference", "active", "晚上喜欢花茶", [_revision("new")]
    )
    assert mutation_state_matches(
        "mutation-scoped-addition",
        [coffee, flower],
        run_id=RUN,
        terminal=_terminal("new"),
    )
    assert not mutation_state_matches(
        "mutation-scoped-addition",
        [{**coffee, "value": "喜欢咖啡"}, flower],
        run_id=RUN,
        terminal=_terminal("new"),
    )
    assert not mutation_state_matches(
        "mutation-scoped-addition",
        [coffee, {**flower, "value": "喜欢花茶"}],
        run_id=RUN,
        terminal=_terminal("new"),
    )


def test_endorsement_requires_husky_on_new_roxy_entity() -> None:
    roxy = _fact(
        "name",
        "pet.name",
        "active",
        "Roxy",
        [_revision("name-new")],
        entity_id="pet-roxy",
    )
    husky = _fact(
        "breed",
        "pet.breed",
        "active",
        "哈士奇",
        [_revision("breed-new", roles=("user_endorsement", "assistant_referent"))],
        entity_id="pet-roxy",
    )
    terminal = _terminal("name-new", "breed-new")
    assert mutation_state_matches(
        "mutation-endorsement", [roxy, husky], run_id=RUN, terminal=terminal
    )
    assert not mutation_state_matches(
        "mutation-endorsement",
        [roxy, {**husky, "entity_id": "other-pet"}],
        run_id=RUN,
        terminal=terminal,
    )


def test_explicit_removal_rejects_active_duplicate() -> None:
    forgotten = _fact(
        "milk",
        "person.preference",
        "forgotten",
        "喜欢奶茶",
        [_revision("forgot", operation="forget")],
    )
    terminal = _terminal("forgot")
    assert mutation_state_matches(
        "mutation-explicit-removal", [forgotten], run_id=RUN, terminal=terminal
    )
    active = _fact(
        "duplicate",
        "person.preference",
        "active",
        "奶茶",
        [_revision("seed", run_id="seed")],
    )
    assert not mutation_state_matches(
        "mutation-explicit-removal", [forgotten, active], run_id=RUN, terminal=terminal
    )


def test_correction_requires_rocky_predecessor_and_user_error_source() -> None:
    original = _revision("rocky", run_id="seed", value="Rocky")
    correction = _revision(
        "roxy",
        operation="revise",
        reason="correct",
        value="Roxy",
        predecessors=("rocky",),
        quote="刚才打错了，它叫 Roxy。",
    )
    roxy = _fact(
        "dog", "pet.name", "active", "Roxy", [original, correction], entity_id="dog"
    )
    terminal = _terminal("roxy")
    assert mutation_state_matches(
        "mutation-natural-correction", [roxy], run_id=RUN, terminal=terminal
    )
    disconnected = {
        **roxy,
        "revisions": [
            original,
            {**correction, "predecessor_revision_ids": ["unrelated"]},
        ],
    }
    assert not mutation_state_matches(
        "mutation-natural-correction", [disconnected], run_id=RUN, terminal=terminal
    )
    wrong_reason = {
        **roxy,
        "revisions": [original, {**correction, "reason": "supersede"}],
    }
    assert not mutation_state_matches(
        "mutation-natural-correction", [wrong_reason], run_id=RUN, terminal=terminal
    )


def test_required_mutation_rejection_stops_serial_schedule_and_keeps_unrun() -> None:
    seeded = _fact(
        "milk",
        "person.preference",
        "forgotten",
        "奶茶",
        [_revision("old", operation="forget", run_id="seed")],
    )
    schedule = [
        ("mutation-explicit-removal::native", {}, "native"),
        ("response-dog::A", {}, "A"),
        ("response-dog::B", {}, "B"),
    ]
    attempted = []
    manifest = {"cells": [], "unrun": []}
    for index, (name, _, _) in enumerate(schedule):
        attempted.append(name)
        manifest["cells"].append({"cell": name, "status": "started"})
        try:
            require_mutation_state(
                "mutation-explicit-removal",
                facts=[seeded],
                run_id=RUN,
                terminal=_terminal(outcome="confirmed_rejection"),
            )
        except RuntimeError as error:
            stop_campaign_at(manifest, schedule, index, error)
            break
    assert attempted == ["mutation-explicit-removal::native"]
    assert manifest["cells"][0]["status"] == "campaign_stopped"
    assert manifest["unrun"] == ["response-dog::A", "response-dog::B"]
