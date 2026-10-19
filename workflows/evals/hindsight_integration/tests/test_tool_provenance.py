"""Per-call exact native projections, including empty and failed lookup semantics."""

import copy
import json

import pytest

from ..capture_components import validate_conversation_chain
from ..tool_provenance import validate_tool_provenance
from .tool_provenance_fixtures import (
    BANK,
    lookup_record,
    memory,
    serial_capture,
    tool_events,
    tool_message,
)


def validate(chain, records):
    return validate_conversation_chain(chain, "final reply", records, bank_id=BANK)


@pytest.mark.parametrize(
    "results", [[], [memory()], [memory("a"), memory("b"), memory("c")]]
)
def test_exact_ordered_native_selection_and_genuine_empty_success(results):
    chain, records = serial_capture(
        [
            [
                {
                    "id": "call-1",
                    "arguments": {"query": "  prior history  ", "limit": 2},
                    "results": results,
                }
            ]
        ]
    )
    bindings = validate(chain, records)
    assert bindings[2] == {
        "lookup_contract": "ade-memory-lookup-v2",
        "lookup_number": 2,
        "parent_request_number": 1,
        "call_index": 0,
        "tool_call_id": "call-1",
    }


@pytest.mark.parametrize(
    "mutation",
    [
        "text",
        "date",
        "nested",
        "type",
        "reorder",
        "drop",
        "empty",
        "duplicate",
        "ok_false",
        "ok_number",
        "scope",
        "missing_memories",
        "null_memories",
    ],
)
def test_changed_tool_content_never_qualifies(mutation):
    chain, records = serial_capture(
        [
            [
                {
                    "id": "call-1",
                    "arguments": {"query": "prior history"},
                    "results": [memory("a"), memory("b")],
                }
            ]
        ]
    )
    tool = tool_message(chain)
    content = json.loads(tool["content"])
    rows = content["memories"]
    match mutation:
        case "text":
            rows[0]["text"] = "Invented text under the same memory ID"
        case "date":
            rows[0]["occurred_start"] = "2099-01-01"
        case "nested":
            rows[0]["attribution"]["speaker"] = "assistant"
        case "type":
            rows[0]["attribution"]["uncertain"] = 1
        case "reorder":
            rows.reverse()
        case "drop":
            rows.pop()
        case "empty":
            content["memories"] = []
        case "duplicate":
            rows.append(rows[0])
        case "ok_false":
            content["ok"] = False
        case "ok_number":
            content["ok"] = 1
        case "scope":
            content["scope"] = "other_relationship"
        case "missing_memories":
            del content["memories"]
        case "null_memories":
            content["memories"] = None
    tool["content"] = json.dumps(content)
    with pytest.raises(ValueError, match="tool_lookup_projection_mismatch"):
        validate(chain, records)


@pytest.mark.parametrize(
    "field,value",
    [
        ("query", "another query"),
        ("limit", 9),
        ("bank_id", "other-bank"),
        ("phase", "automatic"),
        ("lookup_contract", "legacy"),
        ("lookup_number", True),
    ],
)
def test_lookup_identity_and_effective_arguments_cannot_be_changed(field, value):
    chain, records = serial_capture()
    for row in tool_events(records):
        row["value"][field] = value
    with pytest.raises(ValueError):
        validate(chain, records)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_start",
        "missing_finish",
        "duplicate_start",
        "duplicate_finish",
        "missing_pair",
        "changed_finish",
        "before_parent",
        "after_dispatch",
        "selected_ids",
    ],
)
def test_missing_changed_or_noncausal_lookup_lifecycle_fails(mutation):
    chain, records = serial_capture()
    start, finish = tool_events(records)
    match mutation:
        case "missing_start":
            records.remove(start)
        case "missing_finish":
            records.remove(finish)
        case "duplicate_start":
            records.insert(records.index(start), copy.deepcopy(start))
        case "duplicate_finish":
            records.insert(records.index(finish), copy.deepcopy(finish))
        case "missing_pair":
            records.remove(start)
            records.remove(finish)
        case "changed_finish":
            finish["value"]["query"] = "other"
        case "before_parent":
            start["sequence"] = 1
            finish["sequence"] = 2
        case "after_dispatch":
            finish["sequence"] = 999
        case "selected_ids":
            finish["value"]["selected_ids"] = []
    with pytest.raises(ValueError):
        validate(chain, records)


def test_extra_unmatched_lookup_is_not_silently_ignored():
    chain, records = serial_capture()
    extra = lookup_record(3, results=[memory()])
    for row in extra:
        row["sequence"] = len(records) + 1
        records.append(row)
    with pytest.raises(ValueError, match="unmatched_tool_lookup"):
        validate(chain, records)


def test_multiple_calls_with_identical_queries_and_overlapping_ids_are_distinct():
    groups = [
        [
            {
                "id": "call-a",
                "arguments": {"query": "same query"},
                "results": [memory(text="first value")],
            },
            {
                "id": "call-b",
                "arguments": {"query": "same query"},
                "results": [memory(text="second value")],
            },
        ]
    ]
    chain, records = serial_capture(groups)
    assert [row["lookup_number"] for row in validate(chain, records).values()] == [2, 3]
    first, second = tool_message(chain), tool_message(chain, call_index=1)
    first["content"], second["content"] = second["content"], first["content"]
    with pytest.raises(ValueError, match="tool_lookup_projection_mismatch"):
        validate(chain, records)


def test_provider_call_id_may_repeat_across_requests_but_not_within_one_response():
    item = {
        "id": "repeated-id",
        "arguments": {"query": "same query"},
        "results": [memory()],
    }
    chain, records = serial_capture([[item], [item]])
    assert [
        row["parent_request_number"] for row in validate(chain, records).values()
    ] == [1, 2]
    chain, records = serial_capture([[item, item]])
    with pytest.raises(ValueError, match="ambiguous_tool_call_identity"):
        validate(chain, records)


def test_non_memory_tool_does_not_consume_a_native_lookup():
    chain, records = serial_capture(
        [
            [
                {
                    "id": "weather",
                    "name": "get_weather",
                    "arguments": {"city": "synthetic"},
                },
                {
                    "id": "memory",
                    "arguments": {"query": "prior history"},
                    "results": [memory()],
                },
            ]
        ]
    )
    bindings = validate(chain, records)
    assert list(bindings) == [3] and bindings[3]["call_index"] == 1


@pytest.mark.parametrize("failed", [False, True])
def test_interrupted_attempt_may_end_after_a_lookup_without_a_new_dispatch(failed):
    chain, records = serial_capture()
    chain.pop()
    records = records[:-2]
    if failed:
        finish = tool_events(records)[1]
        finish["type"] = "memory_lookup.failed"
        finish["value"]["error_code"] = "hindsight_unavailable"
    assert validate_tool_provenance(chain, records, BANK, successful=False) == {}


def test_failed_lookup_cannot_be_followed_by_character_continuation():
    chain, records = serial_capture()
    tool_events(records)[1]["type"] = "memory_lookup.failed"
    with pytest.raises(ValueError, match="failed_tool_lookup_has_continuation"):
        validate(chain, records)


def test_legacy_tool_records_do_not_gain_inferred_provenance():
    chain, records = serial_capture()
    for row in tool_events(records):
        for field in ("lookup_number", "lookup_contract", "query", "limit"):
            row["value"].pop(field, None)
    with pytest.raises(ValueError, match="tool_lookup_contract_missing"):
        validate(chain, records)


@pytest.mark.parametrize(
    "field,value",
    [("role", "assistant"), ("name", "get_weather"), ("tool_call_id", "foreign-call")],
)
def test_tool_result_identity_is_not_inferred_from_its_content(field, value):
    chain, records = serial_capture()
    tool_message(chain)[field] = value
    with pytest.raises(ValueError, match="tool_result_identity_mismatch"):
        validate(chain, records)


def test_parent_dispatch_must_have_a_received_response():
    chain, records = serial_capture()
    parent = next(row for row in records if row["type"] == "model_request.finished")
    parent["value"]["status"] = "failed"
    with pytest.raises(ValueError, match="tool_parent_response_not_received"):
        validate(chain, records)


def test_next_dispatch_cannot_be_an_unbound_or_nonconversation_request():
    chain, records = serial_capture()
    next_dispatch = [row for row in records if row["type"] == "model_request.started"][
        1
    ]
    next_dispatch["value"] = {**next_dispatch["value"], "stage": "compaction"}
    with pytest.raises(
        ValueError, match="tool_next_dispatch_is_not_bound_continuation"
    ):
        validate(chain, records)


def test_serial_lookup_pairs_cannot_overlap_or_share_a_lookup_number():
    item = {"id": "call-a", "arguments": {"query": "same query"}, "results": [memory()]}
    chain, records = serial_capture([[item, {**item, "id": "call-b"}]])
    events = tool_events(records)
    start, finish = events[2:]
    for row in (start, finish):
        row["value"]["lookup_number"] = 2
    with pytest.raises(ValueError, match="tool_lookup_start_gap_or_overlap"):
        validate(chain, records)
