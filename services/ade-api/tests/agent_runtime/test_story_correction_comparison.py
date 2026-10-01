"""Reproduce matched packet evidence without dispatching a provider or database."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.history_ranking import document_text, query_text

from .story_correction_comparison import (
    LABEL_COMMIT,
    build_packet,
    compare,
    current_message,
    exchanges,
    paired_signals,
    select,
)
from .story_packet_builder import build_history_packet, digest, wire
from .story_packet_comparison import select as original_recipe
from workflows.evals.character_memory_dev.story_continuity.correction_dependencies.inputs import (
    DIRECTORY,
    ROOT,
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
    assert (
        summary["labels_commit"]
        == LABEL_COMMIT
        == "2447917ddd979a8459d23e1998c421aa22f196bf"
    )
    assert (
        summary["kind"]
        == "nonblind_author_matched_packet_measurement_not_model_evaluation"
    )
    assert len(packets) == len({packet["key"] for packet in packets}) == 63
    for path, expected in summary["execution_sources"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_source_topology_has_one_archive_eight_runs_and_sixteen_ordered_messages():
    context, cases = load_inputs()
    for case in cases:
        sources = exchanges(case, context)
        assert (
            len(sources) == len({source["run_id"] for source in sources.values()}) == 8
        )
        assert {source["conversation_id"] for source in sources.values()} == {
            case["conversation_id"]
        }
        messages = [
            message for source in sources.values() for message in source["messages"]
        ]
        assert len(messages) == len({message["id"] for message in messages}) == 16
        assert [message["sequence"] for message in messages] == list(range(1, 17))
        assert [message["created_at"] for message in messages] == sorted(
            message["created_at"] for message in messages
        )
        assert all(source["archived"] for source in sources.values())
    for first, second in zip(cases[::2], cases[1::2], strict=True):
        left = exchanges(first, context)
        right = exchanges(second, context)
        assert current_message(first) == current_message(second)
        for source_id in left:
            if source_id == "E07":
                assert (
                    left[source_id]["messages"][1]["content"]
                    != right[source_id]["messages"][1]["content"]
                )
                for message in (
                    left[source_id]["messages"][1],
                    right[source_id]["messages"][1],
                ):
                    message.pop("content")
                    message.pop("content_sha256")
            assert left[source_id] == right[source_id]


def test_paired_requests_preserve_sources_roles_handles_order_and_real_bounds(result):
    summary, packets = result
    by_key = {packet["key"]: packet for packet in packets}
    context, cases = load_inputs()
    for case, row in zip(cases, summary["cases"], strict=True):
        sources = exchanges(case, context)
        assert row["current_conversation_id"] != row["historical_conversation_id"]
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
            assert receipt["selected"] == receipt["admitted"]
            assert receipt["omitted_capacity"] == receipt["omissions"]["capacity"] == []
            assert receipt["history_equal"]
            assert receipt["generation_input_estimate"] <= 11213
            assert receipt["reviewer_input_with_full_reply_reserve"] <= 11469
            history = review["history"]
            if history:
                system = packet["generation"]["messages"][0]["content"]
                assert (
                    json.loads(system.split("Historical evidence (read-only):\n", 1)[1])
                    == history
                )
            assert len(history) == len(receipt["admitted"]) <= 4
            ordered_messages = []
            for source_id, supplied in zip(receipt["admitted"], history, strict=True):
                source = sources[source_id]
                assert supplied["conversation_id"] == case["conversation_id"]
                assert supplied["run_id"] == source["run_id"]
                assert supplied["archived"]
                for original, message in zip(
                    source["messages"], supplied["messages"], strict=True
                ):
                    index = len(ordered_messages)
                    assert message["handle"] == f"H{index + 1}"
                    assert message["role"] == original["role"]
                    assert message["content"] == original["content"]
                    assert (
                        message["content_sha256"]
                        == hashlib.sha256(original["content"].encode()).hexdigest()
                    )
                    assert message["created_at"] == original["created_at"]
                    assert "sequence" not in message
                    binding = receipt["source_order"][index]
                    assert binding["message_id"] == original["id"]
                    assert binding["sequence"] == original["sequence"]
                    assert binding["source_id"] == source_id
                    assert binding["conversation_id"] == case["conversation_id"]
                    assert binding["handle"] == message["handle"]
                    ordered_messages.append(message)
            assert len(receipt["source_order"]) == len(ordered_messages)


def test_every_reference_supports_its_use_and_empty_history_is_not_an_answer(result):
    count = 0
    keys = {
        "answer_routes": "named_answer_supported",
        "correction_explanation": "correction_explanation_supported",
        "correction_intent": "correction_intent_visible",
        "mistaken_retelling": "mistaken_retelling_visible",
        "optional_detail": "optional_detail_supported",
    }
    for case in result[0]["cases"]:
        assert not case["packets"]["empty"]["assessment"]["named_answer_supported"]
        assert case["packets"]["empty"]["admitted"] == []
        for name, packet in case["packets"].items():
            if name.startswith("reference-"):
                count += 1
                assert not packet["omitted_capacity"]
                for field in packet["reference_for"]:
                    assert packet["assessment"][keys[field]]
    assert count == 45


def test_text_lengths_use_explicit_codepoint_units_without_artificial_equalization(
    result,
):
    _, cases = load_inputs()
    corrections = []
    for case, row in zip(cases, result[0]["cases"], strict=True):
        lengths = row["text_lengths"]
        assert lengths["unit"] == "unicode_code_points"
        assert lengths["current_user"] == len(case["query"])
        assert lengths["scored_query"] == len(query_text(case["query"], []))
        for source in case["exchanges"]:
            assert lengths["sources"][source["id"]] == {
                "user": len(source["user"]),
                "assistant": len(source["assistant"]),
                "scored_document": len(document_text(source)),
            }
        corrections.append(lengths["sources"]["E07"]["assistant"])
    assert corrections == [37, 41, 40, 43, 36, 41]


def test_selection_uses_unchanged_recipes_and_is_insensitive_to_labels_and_input_order():
    _, cases = load_inputs()
    for case in cases:
        before = copy.deepcopy(case)
        expected = select(case)
        assert expected == original_recipe(case)
        poisoned = copy.deepcopy(case)
        poisoned.update(expected="always-select-the-origin", answer_routes=[["E99"]])
        for source in poisoned["exchanges"]:
            source["oracle_priority"] = 1 if source["id"] == "E01" else -1
        assert select(poisoned) == expected
        assert (
            select({**poisoned, "exchanges": list(reversed(poisoned["exchanges"]))})
            == expected
        )
        assert case == before


def test_frozen_results_show_repeated_gap_not_candidate_adoption(result):
    summary, _ = result
    assert summary["paired_assessment"]["investment_trigger_met"] == {
        "baseline": True,
        "candidate": True,
    }
    assert [
        pair["dependency_specific_signal"]
        for pair in summary["paired_assessment"]["pairs"]
    ] == [
        {"baseline": True, "candidate": False},
        {"baseline": True, "candidate": True},
        {"baseline": True, "candidate": True},
    ]
    for direct, dependent in zip(
        summary["cases"][::2], summary["cases"][1::2], strict=True
    ):
        for arm in ("baseline", "candidate"):
            first, second = direct["packets"][arm], dependent["packets"][arm]
            assert first["selected"] == second["selected"]
            assert first["assessment"]["named_answer_supported"]
            assert first["assessment"]["correction_admitted"]
            assert second["assessment"]["correction_admitted"]
            assert not first["assessment"]["unrelated_admitted"]
            assert not second["assessment"]["unrelated_admitted"]
    weekday_candidate = summary["cases"][1]["packets"]["candidate"]
    assert weekday_candidate["selected"] == ["E02", "E07", "E04", "E01"]
    assert weekday_candidate["assessment"]["dependency_status"] == "resolved"
    for index in (3, 5):
        for arm in ("baseline", "candidate"):
            packet = summary["cases"][index]["packets"][arm]
            assert not packet["assessment"]["named_answer_supported"]
            assert packet["assessment"]["dependency_status"] == "missing"


def test_investment_signal_excludes_capacity_and_unresolved_labels(result):
    rows = copy.deepcopy(result[0]["cases"])
    for index in (1, 3, 5):
        packet = rows[index]["packets"]["baseline"]
        packet["selected"] = ["E02", "E04", "E07", "E01"]
        packet["admitted"] = ["E02", "E04", "E07"]
        packet["omitted_capacity"] = ["E01"]
    assessment = paired_signals(rows)
    assert not assessment["investment_trigger_met"]["baseline"]
    assert not any(
        pair["dependency_specific_signal"]["baseline"] for pair in assessment["pairs"]
    )
    rows = copy.deepcopy(result[0]["cases"])
    for row in rows:
        for arm in ("baseline", "candidate"):
            row["packets"][arm]["assessment"]["unresolved"] = [
                "Unresolved author reading."
            ]
    assert paired_signals(rows)["investment_trigger_met"] == {
        "baseline": False,
        "candidate": False,
    }


def test_nonchronological_selection_keeps_original_source_order_receipt():
    context, cases = load_inputs()
    selected = ["E07", "E01", "E05", "E02"]
    receipt, _ = build_packet(cases[1], context, selected)
    assert receipt["selected"] == receipt["admitted"] == selected
    assert [message["sequence"] for message in receipt["source_order"]] == [
        13,
        14,
        1,
        2,
        9,
        10,
        3,
        4,
    ]
    assert [message["handle"] for message in receipt["source_order"]] == [
        f"H{i}" for i in range(1, 9)
    ]


@pytest.mark.parametrize("field", ["saved_facts", "local_suffix", "related_entities"])
def test_shared_builder_rejects_nonempty_controlled_context(field):
    context, cases = load_inputs()
    context[field] = [{"synthetic": "unexpected"}]
    with pytest.raises(ValueError, match="empty saved/local context"):
        build_packet(cases[0], context, ["E01"])


def test_shared_builder_preserves_whole_window_capacity_omission_and_integrity():
    context, cases = load_inputs()
    case = cases[0]
    sources = exchanges(case, context)
    long = sources["E07"]["messages"][1]
    long["content"] = "x" * 60_000
    long["content_sha256"] = hashlib.sha256(long["content"].encode()).hexdigest()
    before = copy.deepcopy(sources)
    receipt, requests = build_history_packet(
        current=current_message(case),
        context=context,
        sources=sources,
        selected=["E07", "E01"],
    )
    assert receipt["admitted"] == ["E01"]
    assert receipt["omitted_capacity"] == ["E07"]
    assert sources == before
    history = json.loads(requests["reviewer"]["messages"][1]["content"])["history"]
    assert len(history) == 1 and len(history[0]["messages"]) == 2
    sources = exchanges(case, context)
    sources["E01"]["messages"][1]["content"] += " changed without new hash"
    with pytest.raises(RuntimeValidationError) as error:
        build_history_packet(
            current=current_message(case),
            context=context,
            sources=sources,
            selected=["E01"],
        )
    assert error.value.detail_code == "natural_history_integrity"
