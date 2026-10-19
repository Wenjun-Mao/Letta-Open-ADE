"""Exact tool-to-native joins for the source-bound sequential executor trace."""

import json

from .records import json_bytes
from .wire_capture import require


LOOKUP_CONTRACT = "ade-memory-lookup-v2"
LOOKUP_FIELDS = (
    "lookup_contract",
    "lookup_number",
    "phase",
    "bank_id",
    "query",
    "limit",
)
LOOKUP_EVENTS = {
    "memory_lookup.started",
    "memory_lookup.completed",
    "memory_lookup.failed",
}


def lookup_pairs(records, bank_id, *, successful):
    events = [row for row in records if row["type"] in LOOKUP_EVENTS]
    if not any(row["value"].get("phase") == "tool" for row in events):
        return []
    require(isinstance(bank_id, str) and bool(bank_id), "tool_lookup_scope_missing")
    pending, pairs, number = None, [], 0
    for row in events:
        value = row["value"]
        require(
            value.get("lookup_contract") == LOOKUP_CONTRACT,
            "tool_lookup_contract_missing",
        )
        require(
            type(value.get("lookup_number")) is int
            and value["lookup_number"] > 0
            and value.get("phase") in {"automatic", "tool"}
            and value.get("bank_id") == bank_id
            and isinstance(value.get("query"), str)
            and bool(value["query"].strip())
            and type(value.get("limit")) is int
            and 1 <= value["limit"] <= 20,
            "tool_lookup_identity_invalid",
        )
        if row["type"] == "memory_lookup.started":
            require(
                pending is None and value["lookup_number"] == number + 1,
                "tool_lookup_start_gap_or_overlap",
            )
            number += 1
            pending = row
            continue
        require(pending is not None, "tool_lookup_finish_without_start")
        require(
            json_bytes({key: pending["value"].get(key) for key in LOOKUP_FIELDS})
            == json_bytes({key: value.get(key) for key in LOOKUP_FIELDS})
            and pending["sequence"] < row["sequence"],
            "tool_lookup_lifecycle_mismatch",
        )
        if value["phase"] == "tool":
            pairs.append((pending, row))
        pending = None
    if pending is not None:
        require(
            not successful and pending["value"]["phase"] == "tool",
            "tool_lookup_unfinished",
        )
        # Cancellation may leave only a start; keep it observable, not completed.
        pairs.append((pending, None))
    return pairs


def request_record(records, request_id, event):
    matches = [
        row
        for row in records
        if row["type"] == event and row["value"].get("request_id") == request_id
    ]
    require(len(matches) == 1, "tool_parent_request_lifecycle_missing_or_duplicated")
    return matches[0]


def effective_arguments(call):
    arguments = call["function"].get("arguments", "{}")
    if isinstance(arguments, str):
        arguments = json.loads(arguments)
    require(
        isinstance(arguments, dict) and not set(arguments) - {"query", "limit"},
        "tool_lookup_arguments_invalid",
    )
    query, limit = arguments.get("query"), arguments.get("limit", 8)
    require(
        isinstance(query, str)
        and bool(query.strip())
        and type(limit) is int
        and 1 <= limit <= 20,
        "tool_lookup_arguments_invalid",
    )
    return query.strip(), limit


def selected_memories(finish):
    value = finish["value"]
    require(
        finish["type"] == "memory_lookup.completed",
        "failed_tool_lookup_has_continuation",
    )
    response = value.get("response")
    results = response.get("results") if isinstance(response, dict) else None
    require(
        isinstance(results, list)
        and all(
            isinstance(row, dict)
            and isinstance(row.get("id"), str)
            and isinstance(row.get("text"), str)
            for row in results
        ),
        "tool_lookup_response_invalid",
    )
    selected = results[: value["limit"]]
    require(
        value.get("selected_ids") == [row["id"] for row in selected],
        "tool_lookup_selection_mismatch",
    )
    return selected


def validate_tool_provenance(chain, records, bank_id, *, successful):
    """Join each serial call by its causal request window, call order and arguments."""
    require(
        all(
            type(row.get("sequence")) is int and row["sequence"] == index
            for index, row in enumerate(records, 1)
        ),
        "tool_record_sequence_invalid",
    )
    pairs = lookup_pairs(records, bank_id, successful=successful)
    consumed, bindings = 0, {}
    for index, (start, wire) in enumerate(chain):
        outcome = wire["outcome"]
        if outcome.get("http_status") != 200:
            require(
                not successful and index == len(chain) - 1,
                "failed_character_request_has_continuation",
            )
            continue
        message = outcome["visible_response"]["choices"][0]["message"]
        calls = message.get("tool_calls") or []
        ids = [call.get("id") for call in calls]
        require(
            all(isinstance(identity, str) and identity for identity in ids)
            and len(ids) == len(set(ids)),
            "ambiguous_tool_call_identity",
        )
        following = chain[index + 1] if index + 1 < len(chain) else None
        next_messages = (
            following[1]["request"]["body"]["messages"] if following else None
        )
        current_messages = wire["request"]["body"]["messages"]
        if following is not None:
            require(
                calls
                and next_messages[: len(current_messages)] == current_messages
                and len(next_messages) == len(current_messages) + 1 + len(calls),
                "continuation_history_mismatch",
            )
            assistant = next_messages[len(current_messages)]
            require(
                all(assistant.get(key) == value for key, value in message.items()),
                "tool_request_response_mismatch",
            )
            tools = next_messages[len(current_messages) + 1 :]
            require(
                all(
                    row.get("role") == "tool"
                    and row.get("tool_call_id") == call["id"]
                    and row.get("name") == call["function"]["name"]
                    for call, row in zip(calls, tools, strict=True)
                ),
                "tool_result_identity_mismatch",
            )
        previous_finish = None
        for call_index, call in enumerate(calls):
            if call["function"].get("name") != "search_memory":
                continue
            if consumed >= len(pairs):
                require(
                    not successful and following is None, "tool_lookup_missing_for_call"
                )
                continue
            begin, finish = pairs[consumed]
            require(
                finish is not None or (not successful and following is None),
                "unfinished_tool_lookup_has_continuation",
            )
            parent = request_record(
                records, start["request_id"], "model_request.finished"
            )
            require(
                parent["value"].get("status") == "received",
                "tool_parent_response_not_received",
            )
            parent_finish = parent["sequence"]
            dispatches = [
                row
                for row in records
                if row["type"] == "model_request.started"
                and row["sequence"] > parent_finish
            ]
            if following is not None:
                require(
                    dispatches
                    and dispatches[0]["value"].get("request_id")
                    == following[0]["request_id"]
                    and dispatches[0]["value"].get("stage") == "conversation",
                    "tool_next_dispatch_is_not_bound_continuation",
                )
                next_start = dispatches[0]["sequence"]
            else:
                require(not dispatches, "tool_interrupted_attempt_has_unbound_dispatch")
                next_start = float("inf")
            require(
                parent_finish < begin["sequence"] < next_start
                and (
                    finish is None
                    or begin["sequence"] < finish["sequence"] < next_start
                )
                and (previous_finish is None or previous_finish < begin["sequence"]),
                "tool_lookup_outside_parent_request_window",
            )
            query, limit = effective_arguments(call)
            require(
                begin["value"]["query"] == query and begin["value"]["limit"] == limit,
                "tool_lookup_arguments_mismatch",
            )
            consumed += 1
            previous_finish = finish["sequence"] if finish else begin["sequence"]
            if following is None:
                require(not successful, "tool_call_has_no_continuation")
                if finish is None:
                    require(consumed == len(pairs), "tool_lookup_after_interruption")
                elif finish["type"] == "memory_lookup.completed":
                    selected_memories(finish)
                else:
                    require(
                        consumed == len(pairs), "tool_lookup_continued_after_failure"
                    )
                continue
            selected = selected_memories(finish)
            message_index = len(current_messages) + 1 + call_index
            require(message_index < len(next_messages), "tool_result_missing")
            tool = next_messages[message_index]
            require(
                tool.get("role") == "tool"
                and tool.get("name") == "search_memory"
                and tool.get("tool_call_id") == call["id"],
                "tool_result_identity_mismatch",
            )
            expected = {
                "ok": True,
                "scope": "current_user_character_relationship",
                "memories": selected,
            }
            require(
                json_bytes(json.loads(tool["content"])) == json_bytes(expected),
                "tool_lookup_projection_mismatch",
            )
            bindings[message_index] = {
                "lookup_contract": LOOKUP_CONTRACT,
                "lookup_number": begin["value"]["lookup_number"],
                "parent_request_number": start["request_number"],
                "call_index": call_index,
                "tool_call_id": call["id"],
            }
    require(consumed == len(pairs), "unmatched_tool_lookup")
    return bindings
