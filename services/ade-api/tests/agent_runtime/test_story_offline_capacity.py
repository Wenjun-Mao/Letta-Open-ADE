"""Reproduce the fixed eight-row diagnostic and guard its exception boundary."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.history_admission import MAX_ADMITTED_WINDOWS
from ade_api.features.agent_runtime.history_ranking import TOP_K
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    serialized_review_tokens,
)
from workflows.evals.character_memory_dev.story_continuity.evidence_selection.offline_inputs import (
    DIRECTORY,
    PROTOCOL_COMMIT,
    PROTOCOL_SHA256,
    ROOT,
    ROWS,
    load_offline_inputs,
    validate_inputs,
    validate_row,
    verify_freeze,
)

from .story_correction_comparison import current_message, exchanges
from .story_offline_capacity import FULL_REPLY, build_complete_packet, measure
from .story_packet_builder import build_history_packet, digest, wire


@pytest.fixture(scope="module")
def measured():
    return measure()


def fixture():
    context, cases, _ = load_offline_inputs()
    case = cases[1]
    return context, case, exchanges(case, context)


def build(context, case, sources, included=None):
    return build_complete_packet(
        context=context,
        case=case,
        sources=sources,
        included=["E01", "E07"] if included is None else included,
    )


def test_exact_current_artifacts_and_frozen_execution_sources(measured):
    summary, packets = measured
    assert summary == json.loads((DIRECTORY / "offline_capacity.json").read_bytes())
    raw = "".join(wire(packet) + "\n" for packet in packets).encode()
    assert raw == (DIRECTORY / "offline_packets.jsonl").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == summary["packets_sha256"]
    assert summary["protocol_commit"] == PROTOCOL_COMMIT
    assert summary["protocol_sha256"] == PROTOCOL_SHA256
    for path, expected in summary["execution_sources"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    assert len(packets) == len(summary["rows"]) == len(ROWS) == 8
    assert [packet["key"] for packet in packets] == [row[0] for row in ROWS]
    assert TOP_K == MAX_ADMITTED_WINDOWS == 4
    assert summary["capacity_contract"]["candidate_reply_reserve_tokens"] == 4096
    assert (
        summary["capacity_contract"]["candidate_reply_placeholder_ascii_chars"] == 16384
    )


def test_all_complete_sources_full_reserve_and_shared_h(measured):
    summary, packets = measured
    context, cases, _ = load_offline_inputs()
    cases = {case["id"]: case for case in cases}
    for row, artifact, spec in zip(summary["rows"], packets, ROWS, strict=True):
        key, case_id, included = spec
        case = cases[case_id]
        sources = exchanges(case, context)
        review = json.loads(artifact["reviewer"]["messages"][1]["content"])
        full_review = json.loads(
            artifact["reviewer_full_reserve"]["messages"][1]["content"]
        )
        assert full_review == {**review, "candidate_visible_reply": FULL_REPLY}
        assert len(FULL_REPLY) == 16384 and FULL_REPLY.isascii()
        assert (
            full_review["context"]
            == full_review["eligible_support"]
            == full_review["targets"]
            == []
        )
        history = review["history"]
        assert len(history) == row["included_source_count"] == len(included)
        assert row["included_message_count"] == 2 * len(included)
        assert row["included"] == list(included)
        assert row["history_sha256"] == digest(history)
        system = artifact["generation"]["messages"][0]["content"]
        if included:
            assert (
                json.loads(system.split("Historical evidence (read-only):\n", 1)[1])
                == history
            )
        else:
            assert "Historical evidence (read-only):\n" not in system
        for index, (source_id, supplied) in enumerate(
            zip(included, history, strict=True)
        ):
            source = sources[source_id]
            for field in (
                "run_id",
                "conversation_id",
                "definition_version_id",
                "archived",
                "annotations",
            ):
                assert source[field] == supplied[field]
            for offset, (original, message) in enumerate(
                zip(source["messages"], supplied["messages"], strict=True)
            ):
                assert message == {
                    "handle": f"H{index * 2 + offset + 1}",
                    **{
                        field: original[field]
                        for field in ("role", "content", "created_at", "content_sha256")
                    },
                }
                receipt = row["source_order"][index * 2 + offset]
                assert receipt["message_id"] == original["id"]
                assert receipt["sequence"] == original["sequence"]
                assert receipt["handle"] == message["handle"]
                assert receipt["run_id"] == source["run_id"]
        assert row["counterfactual_capacity_status"] == "fits"
        assert row["runtime_admission"] == "not_attempted"
        for name in ("generation", "reviewer", "reviewer_full_reserve"):
            assert artifact[name]["max_tokens"] == 4096
            assert row[f"{name}_sha256"] == digest(artifact[name])
        for name in ("generation", "reviewer_full_reserve", "reviewer_synthetic"):
            cap = row[name]
            assert cap["fits"] and cap["overflow"] == 0
            assert cap["headroom"] == cap["input_limit"] - cap["input_estimate"]
        assert row["reviewer_full_reserve"][
            "input_estimate"
        ] == serialized_review_tokens(artifact["reviewer_full_reserve"])
        assert row["key"] == key
    whole = summary["rows"][2]
    assert whole["generation"]["input_estimate"] == 2410
    assert whole["reviewer_full_reserve"]["input_estimate"] == 9993
    assert whole["generation"]["headroom"] == 8803
    assert whole["reviewer_full_reserve"]["headroom"] == 1476


def test_all_ordinary_controls_have_byte_exact_historical_parity(measured):
    context, cases, _ = load_offline_inputs()
    by_id = {case["id"]: case for case in cases}
    for spec, receipt, artifact in zip(
        ROWS, measured[0]["rows"], measured[1], strict=True
    ):
        _, case_id, included = spec
        if len(included) > 4:
            assert (
                receipt["historical_builder_parity"]
                == "outside_historical_four_window_contract"
            )
            continue
        case = by_id[case_id]
        old_receipt, old = build_history_packet(
            current=current_message(case),
            context=context,
            sources=exchanges(case, context),
            selected=list(included),
        )
        assert receipt["historical_builder_parity"] == "byte_exact"
        assert wire(old) == wire({name: artifact[name] for name in old})
        assert old_receipt["admitted"] == list(included)


def test_no_mutation_or_evaluator_metadata_leakage():
    context, case, sources = fixture()
    before = copy.deepcopy((context, case, sources))
    receipt, requests = build(context, case, sources)
    assert (context, case, sources) == before
    poison = "EVALUATOR_SENTINEL_SHOULD_NEVER_BE_SERIALIZED"
    context["source_topology"] = poison
    context["story_contract"] = poison
    case["answer_routes"] = [[poison]]
    for exchange in sources.values():
        exchange["oracle_priority"] = poison
    included = ["E01", "E07"]
    poisoned_before = copy.deepcopy((context, case, sources, included))
    other_receipt, other = build(context, case, sources, included)
    assert (context, case, sources, included) == poisoned_before
    assert requests == other and receipt == other_receipt
    assert poison not in wire(other)
    for field in (
        "source_topology",
        "answer_routes",
        "named_answer_supported",
        "unresolved",
        "dependency_status",
        "source_order",
    ):
        assert field not in json.loads(other["reviewer"]["messages"][1]["content"])
        if field != "unresolved":
            assert field not in wire(other)


@pytest.mark.parametrize("field", ["saved_facts", "local_suffix", "related_entities"])
def test_nonempty_local_context_rejected(field):
    context, case, sources = fixture()
    context[field] = [{"synthetic": "unapproved"}]
    with pytest.raises(ValueError, match="empty saved/local"):
        build(context, case, sources)


@pytest.mark.parametrize(
    "drift", ["query", "text", "count", "order", "scope", "context", "extra_case"]
)
def test_changed_frozen_input_or_scope_is_rejected(drift):
    context, cases, _ = load_offline_inputs()
    if drift == "query":
        cases[0]["query"] += " altered"
    elif drift == "text":
        cases[0]["exchanges"][0]["assistant"] += " altered"
    elif drift == "count":
        cases[0]["exchanges"].pop()
    elif drift == "order":
        cases[0]["exchanges"].reverse()
    elif drift == "scope":
        cases[0]["conversation_id"] = "another-subject"
    elif drift == "context":
        context["persona"] += " altered"
    else:
        cases.append(copy.deepcopy(cases[0]))
    with pytest.raises(ValueError, match="inputs/scope/count"):
        validate_inputs(context, cases)


@pytest.mark.parametrize(
    "included",
    [
        ["E01", "E01"],
        ["E99"],
        ["E01", "E02", "E03", "E04", "E05"],
        list(reversed(ROWS[2][2])),
    ],
)
def test_duplicate_unknown_and_unapproved_count_order_rejected(included):
    context, case, sources = fixture()
    with pytest.raises(ValueError):
        build(context, case, sources, included)
    with pytest.raises(ValueError, match="eight-row"):
        validate_row("D04/whole-pool", "D04", included)


def test_eight_source_exception_cannot_transfer_to_d02():
    context, cases, _ = load_offline_inputs()
    case = cases[0]
    with pytest.raises(ValueError, match="Only D04"):
        build(context, case, exchanges(case, context), list(ROWS[2][2]))


@pytest.mark.parametrize(
    "field",
    [
        "run_id",
        "conversation_id",
        "definition_version_id",
        "archived",
        "sequence",
        "created_at",
    ],
)
def test_source_binding_drift_rejected(field):
    context, case, sources = fixture()
    source = sources["E01"]
    if field in {"sequence", "created_at"}:
        source["messages"][0][field] = (
            -1 if field == "sequence" else "2000-01-01T00:00:00+00:00"
        )
    else:
        source[field] = False if field == "archived" else "different-binding"
    with pytest.raises(ValueError, match="binding differs"):
        build(context, case, sources)


@pytest.mark.parametrize(
    "corruption", ["hash", "identity", "role", "incomplete", "annotation"]
)
def test_runtime_integrity_rejects_invalid_source(corruption):
    context, case, sources = fixture()
    if corruption == "hash":
        sources["E01"]["messages"][1]["content"] += " unbound"
    elif corruption == "identity":
        sources["E07"]["messages"][1]["id"] = sources["E01"]["messages"][1]["id"]
    elif corruption == "role":
        sources["E01"]["messages"][1]["role"] = "system"
    elif corruption == "incomplete":
        sources["E01"]["messages"].pop()
    else:
        # Keep the controlled annotation equality, so the owning runtime validator acts.
        context["history_annotations"]["links"].append({"message_id": "foreign"})
    with pytest.raises(RuntimeValidationError) as error:
        build(context, case, sources)
    assert error.value.detail_code == "natural_history_integrity"


def test_protocol_drift_is_not_a_fallback(tmp_path):
    (tmp_path / "OFFLINE_PROTOCOL.md").write_bytes(
        (DIRECTORY / "OFFLINE_PROTOCOL.md").read_bytes() + b"changed"
    )
    with pytest.raises(ValueError, match="input differs"):
        verify_freeze(tmp_path)


@pytest.mark.parametrize("consumer", ["generation", "reviewer", "both"])
def test_overflow_preserves_all_sources_and_never_becomes_admission(consumer):
    context, case, sources = fixture()
    included = list(ROWS[2][2])
    if consumer == "generation":
        # Keep the mandatory base in budget; only adding H should cause overflow.
        context["generation_system_text"] += "x" * 37000
    else:
        message = sources["E01"]["messages"][1]
        message["content"] += "x" * (8000 if consumer == "reviewer" else 60000)
        message["content_sha256"] = hashlib.sha256(
            message["content"].encode()
        ).hexdigest()
    before = copy.deepcopy((context, case, sources))
    receipt, requests = build(context, case, sources, included)
    assert (context, case, sources) == before
    assert receipt["included"] == included
    assert receipt["included_source_count"] == 8
    assert receipt["included_message_count"] == 16
    assert receipt["counterfactual_capacity_status"] == "overflow"
    assert receipt["runtime_admission"] == "not_attempted"
    assert receipt["generation"]["fits"] == (consumer == "reviewer")
    assert receipt["reviewer_full_reserve"]["fits"] == (consumer == "generation")
    assert receipt["reviewer_preflight_error"] == (
        None if consumer == "generation" else "natural_reviewer_capacity"
    )
    history = json.loads(requests["reviewer_full_reserve"]["messages"][1]["content"])[
        "history"
    ]
    assert len(history) == 8
    for source_id, supplied in zip(included, history, strict=True):
        assert [message["content"] for message in supplied["messages"]] == [
            message["content"] for message in sources[source_id]["messages"]
        ]
    for name in ("generation", "reviewer_full_reserve"):
        cap = receipt[name]
        assert cap["overflow"] == max(0, cap["input_estimate"] - cap["input_limit"])
        if not cap["fits"]:
            assert cap["overflow"] > 0 and cap["headroom"] < 0
