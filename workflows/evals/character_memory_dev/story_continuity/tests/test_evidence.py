"""Explicitly synthetic receipts; these do not test model interpretation."""

import json
from copy import deepcopy

import pytest

from ..evidence import checked_capture, validate_turn
from ..schedule import digest
from .observation_support import reseal, synthetic_observation


@pytest.fixture
def case():
    scope = {
        "subject": "s",
        "root": "xiaotang",
        "purpose": "evaluation",
        "workspace": "w",
    }
    messages = [
        {
            "role": role,
            "content": text,
            "id": str(i),
            "run_id": "origin",
            "content_sha256": digest(text.encode()),
        }
        for i, (role, text) in enumerate(
            [("user", "讲件小事"), ("assistant", "我独自看过灯塔。")]
        )
    ]
    window = {
        "run_id": "origin",
        "conversation_id": "old",
        "definition_version_id": "v1",
        "archived": True,
        "messages": messages,
    }
    ledger = {"origin": {**window, "status": "succeeded", "scope": scope, "ordinal": 1}}
    wire = json.dumps([window], ensure_ascii=False, separators=(",", ":"))
    capture = {
        "schema_version": 1,
        "attempt": 1,
        "run_id": "target",
        "policy_binding": "p",
        "terminal_readback": {
            "outcome": "committed",
            "run_status": "succeeded",
            "attempt_status": "succeeded",
            "assistant_message_ids": ["a"],
            "revision_ids": [],
            "accepted_memory_generation": 1,
            "observed_memory_generation": 1,
        },
        "candidate_visible_reply": "我独自看过灯塔。",
        "history_selection": {
            "admitted_run_ids": ["origin"],
            "corpus_run_ids": ["origin"],
            "ranked_run_ids": ["origin"],
            "omitted_capacity_run_ids": [],
        },
        "reviewer_request": {
            "messages": [
                {"role": "system", "content": "review"},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"history": [window], "current_user": {"content": "那次呢？"}}
                    ),
                },
            ]
        },
        "reviewer_decision": {"decisions": []},
        "generation_requests": [
            {
                "messages": [
                    {
                        "role": "system",
                        "content": "Historical evidence (read-only):\n" + wire,
                    },
                    {"role": "user", "content": "那次呢？"},
                ]
            }
        ],
    }
    memories = {"subject_id": "s", "memory_generation": 1, "facts": []}
    synthetic_observation(capture, scope)
    readback = {
        "ordinal": 7,
        "definition_version_id": "v2",
        "run": {
            "id": "target",
            "conversation_id": "new",
            "status": "succeeded",
            "attempt_count": 1,
            "retry_count": 0,
        },
        "state": {
            "messages_truncated": False,
            "messages": [
                {"id": "u", "run_id": "target", "role": "user", "content": "那次呢？"},
                {
                    "id": "a",
                    "run_id": "target",
                    "role": "assistant",
                    "content": capture["candidate_visible_reply"],
                },
            ],
        },
        "memories": dict(memories),
    }
    return dict(
        capture=capture,
        readback=readback,
        before_memories=memories,
        expected_prompt="那次呢？",
        source_ledger=ledger,
        target_scope=scope,
        origin_run_id="origin",
        archive_probe=True,
        evidence_kind="scripted",
    )


def reject(case):
    case["readback"]["run"]["status"] = "failed"
    case["readback"]["state"]["messages"].pop()
    case["capture"]["terminal_readback"].update(
        outcome="confirmed_rejection",
        run_status="failed",
        attempt_status="failed",
        assistant_message_ids=[],
    )
    case["capture"]["private_observations"]["after"]["subject_run_activity"][0][
        "status"
    ] = "failed"
    reseal(case["capture"])


def test_scripted_capture_is_mechanics_only(case):
    result = validate_turn(**case)
    assert result["semantic"] == "not_measured"
    assert result["full_persistence"] == "independent_complete_before_after_unchanged"


def test_generation_packet_has_bounded_json_before_tool_instructions(case):
    system = case["capture"]["generation_requests"][0]["messages"][0]
    system["content"] += "\n\nCurated tools: use returned results faithfully."
    assert validate_turn(**case)["semantic"] == "not_measured"


def test_duplicate_generation_history_section_is_not_substring_laundered(case):
    system = case["capture"]["generation_requests"][0]["messages"][0]
    system["content"] += "\nHistorical evidence (read-only):\n[]"
    with pytest.raises(ValueError, match="Duplicate"):
        validate_turn(**case)


@pytest.mark.parametrize(
    "mutation",
    [
        "absent_origin",
        "uncommitted_origin",
        "subject",
        "root",
        "workspace",
        "purpose",
        "hash",
        "future",
        "roles",
        "missing_packet",
        "unarchived",
        "current_version",
        "stale_message",
        "revision",
        "generation",
        "truncated",
        "review_roles",
    ],
)
def test_corrupt_or_incomplete_evidence_fails(case, mutation):
    source = case["source_ledger"]["origin"]
    if mutation == "absent_origin":
        case["source_ledger"].clear()
    elif mutation == "uncommitted_origin":
        source["status"] = "failed"
    elif mutation in {"subject", "root", "workspace", "purpose"}:
        source["scope"] = source["scope"] | {mutation: "foreign"}
    elif mutation == "hash":
        source["messages"][1]["content"] = "篡改"
    elif mutation == "future":
        source["ordinal"] = 7
    elif mutation == "roles":
        source["messages"][1]["role"] = "user"
    elif mutation == "missing_packet":
        case["capture"]["generation_requests"] = []
    elif mutation == "unarchived":
        source["archived"] = False
    elif mutation == "current_version":
        case["readback"]["definition_version_id"] = "v1"
    elif mutation == "stale_message":
        case["readback"]["state"]["messages"][1]["content"] = "不同"
    elif mutation == "revision":
        case["capture"]["terminal_readback"]["revision_ids"] = ["unexpected"]
    elif mutation == "generation":
        case["readback"]["memories"]["memory_generation"] = 2
    elif mutation == "truncated":
        case["readback"]["state"]["messages_truncated"] = True
    elif mutation == "review_roles":
        case["capture"]["reviewer_request"]["messages"][1]["role"] = "assistant"
    with pytest.raises(ValueError):
        validate_turn(**case)


@pytest.mark.parametrize("review_absent", [False, True])
def test_rejected_run_does_not_launder_structural_leakage(case, review_absent):
    reject(case)
    if review_absent:
        case["capture"]["reviewer_request"] = {"stage": "absent"}
    case["source_ledger"]["origin"]["scope"] = case["target_scope"] | {
        "subject": "foreign"
    }
    with pytest.raises(ValueError, match="cross-scope"):
        validate_turn(**case)


def test_early_rejection_without_required_observations_stops_qualification(case):
    reject(case)
    for key in ("history_selection", "generation_requests", "reviewer_request"):
        case["capture"][key] = {"stage": "absent"}
    case["capture"]["private_observations"]["history"] = {"status": "unavailable"}
    reseal(case["capture"])
    with pytest.raises(ValueError, match="inventory incomplete"):
        validate_turn(**case)


def test_unarchived_intermediate_echo_cannot_qualify_archive(case):
    echo = deepcopy(case["source_ledger"]["origin"])
    echo.update(run_id="echo", conversation_id="echo_chat", archived=False, ordinal=5)
    case["source_ledger"]["echo"] = echo
    selection = case["capture"]["history_selection"]
    selection["admitted_run_ids"].append("echo")
    selection["corpus_run_ids"].append("echo")
    selection["ranked_run_ids"].append("echo")
    case["capture"]["private_observations"]["history"]["candidates"].append(
        {"run_id": "echo", "reason": "admitted"}
    )
    reseal(case["capture"])
    review = case["capture"]["reviewer_request"]["messages"][1]
    history = json.loads(review["content"])["history"]
    history.append(
        {
            key: echo[key]
            for key in (
                "run_id",
                "conversation_id",
                "definition_version_id",
                "archived",
                "messages",
            )
        }
    )
    review["content"] = json.dumps(
        {"history": history, "current_user": {"content": "那次呢？"}}
    )
    case["capture"]["generation_requests"][0]["messages"][0]["content"] = (
        "Historical evidence (read-only):\n"
        + json.dumps(history, ensure_ascii=False, separators=(",", ":"))
    )
    with pytest.raises(ValueError, match="intermediate echo"):
        validate_turn(**case)


@pytest.mark.parametrize("wrong", ["hash", "run", "policy", "attempt"])
def test_capture_binding_rejects_stale_or_corrupt_bytes(case, wrong):
    capture = case["capture"]
    if wrong == "attempt":
        capture["attempt"] = 2
    raw = json.dumps(capture).encode()
    with pytest.raises(ValueError):
        checked_capture(
            raw,
            sha256="0" * 64 if wrong == "hash" else digest(raw),
            run_id="stale" if wrong == "run" else "target",
            policy="stale" if wrong == "policy" else "p",
        )
