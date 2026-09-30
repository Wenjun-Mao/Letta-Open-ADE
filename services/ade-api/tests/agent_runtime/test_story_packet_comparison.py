"""Reproduce the bounded non-blind diagnostic without any model dispatch."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from .story_packet_comparison import LABEL_COMMIT, compare, digest, select, wire
from workflows.evals.character_memory_dev.story_continuity.packet_sufficiency.packet import (
    DIRECTORY,
    load_inputs,
)


@pytest.fixture(scope="module")
def result():
    return compare()


def test_exact_summary_and_all_wire_packets_reproduce(result):
    summary, packets = result
    assert summary == json.loads((DIRECTORY / "comparison.json").read_bytes())
    raw = "".join(wire(packet) + "\n" for packet in packets).encode()
    assert raw == (DIRECTORY / "packets.jsonl").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == summary["packets_sha256"]
    assert summary["labels_commit"] == LABEL_COMMIT
    assert (
        summary["kind"] == "synthetic_nonblind_packet_diagnostic_not_model_evaluation"
    )
    assert len(packets) == len({p["key"] for p in packets}) == 68


def test_wire_packets_preserve_roles_text_sources_and_bounds(result):
    summary, packets = result
    by_key = {packet["key"]: packet for packet in packets}
    _, cases, _ = load_inputs()
    for case, row in zip(cases, summary["cases"], strict=True):
        sources = {source["id"]: source for source in case["exchanges"]}
        for receipt in row["packets"].values():
            packet = by_key[receipt["artifact_key"]]
            assert digest(packet["generation"]) == receipt["generation_sha256"]
            assert digest(packet["reviewer"]) == receipt["reviewer_sha256"]
            review = json.loads(packet["reviewer"]["messages"][1]["content"])
            assert review["current_user"]["content"] == case["query"]
            assert (
                review["context"]
                == review["eligible_support"]
                == review["targets"]
                == []
            )
            assert receipt["omitted_capacity"] == []
            assert receipt["selected"] == receipt["admitted"]
            assert receipt["history_equal"]
            assert receipt["generation_input_estimate"] <= 11213
            assert receipt["reviewer_input_with_full_reply_reserve"] <= 11469
            assert len(review["history"]) == len(receipt["admitted"]) <= 4
            for index, (source_id, exchange) in enumerate(
                zip(receipt["admitted"], review["history"], strict=True)
            ):
                assert exchange["run_id"] == f"{case['id']}-{source_id}"
                assert exchange["archived"] is True
                for offset, role in enumerate(("user", "assistant"), 1):
                    message = exchange["messages"][offset - 1]
                    assert message["role"] == role
                    assert message["handle"] == f"H{index * 2 + offset}"
                    assert message["content"] == sources[source_id][role]
                    assert (
                        message["content_sha256"]
                        == hashlib.sha256(message["content"].encode()).hexdigest()
                    )
                    assert message["created_at"] == sources[source_id]["at"]


def test_every_reference_supports_its_annotated_use_without_capacity_omission(result):
    summary, _ = result
    count = 0
    for case in summary["cases"]:
        for name, packet in case["packets"].items():
            if name.startswith("reference-"):
                count += 1
                assert not packet["omitted_capacity"]
                for use in packet["reference_for"]:
                    field, route_id = use.split("/")
                    assert packet["assessment"][field][route_id]
    assert count == 38


def test_selection_never_consumes_judgments_or_reference_sets():
    _, cases, _ = load_inputs()
    for case in cases:
        original = copy.deepcopy(case)
        before = select(case)
        case = {
            **case,
            "answer_routes": [{"sets": [["not-a-source"]]}],
            "expected": "select-the-origin",
        }
        assert select(case) == before
        assert (
            select({**case, "exchanges": list(reversed(case["exchanges"]))}) == before
        )
        assert original["exchanges"] == case["exchanges"]


def test_new_controls_show_gain_and_unresolved_dependency_without_adoption(result):
    by_id = {case["id"]: case for case in result[0]["cases"]}
    c01 = by_id["C01"]["packets"]
    assert c01["baseline"]["selected"] == ["E02", "E05", "E04", "E07"]
    assert c01["candidate"]["selected"] == ["E02", "E05", "E07", "E06"]
    assert (
        c01["baseline"]["assessment"]["dependencies"]["name_restored_day"] == "missing"
    )
    for arm in ("baseline", "candidate"):
        assert not c01[arm]["assessment"]["answer_routes"]["friday"]
    c06 = by_id["C06"]["packets"]
    assert not c06["baseline"]["assessment"]["answer_routes"][
        "unresolved_place_weather"
    ]
    assert c06["candidate"]["assessment"]["answer_routes"]["unresolved_place_weather"]
    assert c06["candidate"]["selected"] == ["E04", "E05", "E02", "E01"]


def test_c08_conditional_alternative_remains_visible_without_affecting_arm_difference(
    result,
):
    case = result[0]["cases"][7]
    for arm in ("baseline", "candidate"):
        assert not case["packets"][arm]["assessment"]["answer_routes"][
            "withdrawal_and_reassertion"
        ]
    for first in ("E02", "E03", "E04"):
        packet = case["packets"][f"reference-{first}-E05-E06"]
        assert packet["assessment"]["answer_routes"]["withdrawal_and_reassertion"]
        assert not packet["assessment"]["answer_routes"]["named_day_conflict"]


def test_empty_packets_and_admission_classes_are_not_collapsed(result):
    cases = result[0]["cases"]
    for case in cases:
        empty = case["packets"]["empty"]
        assert empty["admitted"] == []
        assert any(empty["assessment"]["answer_routes"].values()) == (
            case["id"] == "C03"
        )
    for arm, unrelated, other in (("baseline", 4, 3), ("candidate", 11, 1)):
        assert (
            sum(
                len(c["packets"][arm]["assessment"]["unrelated_admitted"])
                for c in cases
            )
            == unrelated
        )
        assert (
            sum(
                len(c["packets"][arm]["assessment"]["other_episode_admitted"])
                for c in cases
            )
            == other
        )
