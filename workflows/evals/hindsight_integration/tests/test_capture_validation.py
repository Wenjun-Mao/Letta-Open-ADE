"""Portable negative capture checks, not model-quality judgments."""

import copy
import hashlib
import json

import pytest

from ..capture_validation import (
    context_components,
    validate_wire,
    validate_conversation_chain,
)


def wire(body=None):
    body = body or {"messages": [{"role": "user", "content": "current"}]}
    raw = json.dumps(body)
    return {
        "request": {
            "request_id": "router-a",
            "input_complete": True,
            "body": body,
            "raw_body_utf8": raw,
            "request_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        },
        "outcome": {
            "request_id": "router-a",
            "response_capture_complete": True,
            "http_status": 200,
            "visible_response": {
                "choices": [{"message": {"role": "assistant", "content": "reply"}}]
            },
        },
    }


@pytest.mark.parametrize(
    "mutation", ["hash", "body", "private", "outcome", "input", "response"]
)
def test_wire_corruption_or_missing_projection_never_qualifies(mutation):
    value = wire()
    assert validate_wire(value) == value["request"]
    match mutation:
        case "hash":
            value["request"]["request_sha256"] = "0" * 64
        case "body":
            value["request"]["body"] = {"messages": []}
        case "private":
            value["request"]["body"]["api_key"] = "excluded"
        case "outcome":
            value["outcome"] = None
        case "input":
            value["request"]["input_complete"] = False
        case "response":
            value["outcome"]["response_capture_complete"] = False
    with pytest.raises(ValueError):
        validate_wire(value)


def test_manifest_covers_actual_spans_and_exposes_executor_added_policy():
    base = [
        {"role": "system", "content": "persona"},
        {"role": "user", "content": "current"},
    ]
    context = {
        "messages": base,
        "components": [
            {
                "kind": kind,
                "message_index": index,
                "start": 0,
                "end": len(item["content"]),
                "sha256": hashlib.sha256(item["content"].encode()).hexdigest(),
                "source_ids": ["source-a"],
            }
            for index, (item, kind) in enumerate(
                zip(base, ["persona", "current_input"])
            )
        ],
    }
    request = {"messages": [dict(base[0], content="persona\n\ntool policy"), base[1]]}
    parts = context_components(context, request)
    assert parts[-1]["kind"] == "executor_policy"
    assert parts[-1]["start"] == len("persona")
    changed = copy.deepcopy(context)
    changed["components"][0]["end"] -= 1
    with pytest.raises(ValueError):
        context_components(changed, request)


def test_committed_reply_must_equal_actual_final_provider_response():
    value = wire()
    validate_conversation_chain([({"request_number": 1}, value)], "reply", [])
    with pytest.raises(ValueError, match="committed_reply_differs"):
        validate_conversation_chain(
            [({"request_number": 1}, value)], "invented reply", []
        )


def test_dropped_tool_continuation_is_not_a_final_reply():
    value = wire()
    value["outcome"]["visible_response"]["choices"][0]["message"] = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call-a",
                "type": "function",
                "function": {"name": "search_memory", "arguments": "{}"},
            }
        ],
    }
    with pytest.raises(ValueError, match="committed_reply_differs"):
        validate_conversation_chain([({"request_number": 1}, value)], "reply", [])
