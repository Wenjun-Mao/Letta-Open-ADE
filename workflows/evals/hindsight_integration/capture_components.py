"""Component spans and continuation provenance in actual provider requests."""

import hashlib
import json

from .wire_capture import require


def context_components(context: dict, request: dict) -> list[dict]:
    """Index recorded composer spans against actual sent messages and continuations."""
    base, actual = context["messages"], request["messages"]
    require(len(actual) >= len(base), "request_lost_context")
    parts = list(context["components"])
    coverage = {index: [] for index in range(len(base))}
    for part in parts:
        index, start, end = part["message_index"], part["start"], part["end"]
        require(
            index in coverage and 0 <= start <= end <= len(base[index]["content"]),
            "component_range_invalid",
        )
        text = base[index]["content"][start:end]
        require(
            hashlib.sha256(text.encode()).hexdigest() == part["sha256"],
            "component_hash_mismatch",
        )
        coverage[index].append((start, end))
    for index, item in enumerate(base):
        spans = sorted(coverage[index])
        offset = 0
        for start, end in spans:
            require(start == offset, "component_gap_or_overlap")
            offset = end
        require(offset == len(item["content"]), "component_content_uncovered")
        require(item["role"] == actual[index]["role"], "context_role_changed")
        if index == 0:
            require(
                actual[index]["content"].startswith(item["content"]),
                "context_system_changed",
            )
            if actual[index]["content"] != item["content"]:
                text = actual[index]["content"][len(item["content"]) :]
                parts.append(
                    {
                        "kind": "executor_policy",
                        "message_index": 0,
                        "start": len(item["content"]),
                        "end": len(actual[index]["content"]),
                        "sha256": hashlib.sha256(text.encode()).hexdigest(),
                        "source_ids": [],
                    }
                )
        else:
            require(item == actual[index], "context_dialogue_changed")
    for index in range(len(base), len(actual)):
        item = actual[index]
        require(item["role"] in {"assistant", "tool"}, "unexpected_continuation_role")
        source_ids = []
        if item["role"] == "tool":
            value = json.loads(item["content"])
            source_ids = [row["id"] for row in value.get("memories", [])]
        text = item.get("content") or ""
        parts.append(
            {
                "kind": "tool_recall"
                if item["role"] == "tool"
                else "model_continuation",
                "message_index": index,
                "start": 0,
                "end": len(text),
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "source_ids": source_ids,
                "tool_call_id": item.get("tool_call_id"),
            }
        )
    return parts


def validate_conversation_chain(chain: list, reply: str, lookups: list[dict]) -> None:
    require(bool(chain), "successful_attempt_has_no_conversation_request")
    memory_ids = {
        value
        for row in lookups
        if row["phase"] == "tool"
        for value in row["selected_ids"]
    }
    for index, (start, wire) in enumerate(chain):
        require(start["request_number"] == index + 1, "continuation_number_gap")
        outcome = wire["outcome"]
        require(
            outcome["http_status"] == 200,
            "successful_attempt_has_failed_provider_request",
        )
        message = outcome["visible_response"]["choices"][0]["message"]
        calls = message.get("tool_calls") or []
        if index == len(chain) - 1:
            require(
                not calls and (message.get("content") or "").strip() == reply,
                "committed_reply_differs_from_provider",
            )
            continue
        require(bool(calls), "continuation_without_tool_request")
        current = wire["request"]["body"]["messages"]
        following = chain[index + 1][1]["request"]["body"]["messages"]
        require(
            following[: len(current)] == current
            and len(following) == len(current) + 1 + len(calls),
            "continuation_history_mismatch",
        )
        assistant = following[len(current)]
        require(
            all(assistant.get(key) == value for key, value in message.items()),
            "tool_request_response_mismatch",
        )
        tools = following[len(current) + 1 :]
        require(
            [row.get("tool_call_id") for row in tools]
            == [call["id"] for call in calls],
            "tool_call_identity_mismatch",
        )
        for row in tools:
            value = json.loads(row["content"])
            require(
                all(item["id"] in memory_ids for item in value.get("memories", [])),
                "unobserved_tool_memory",
            )
