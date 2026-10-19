"""Synthetic sequential provider/native transcripts, never observed product evidence."""

import copy
import json


BANK = "synthetic-owned-bank"


def memory(identity="memory-1", *, text="Native original meaning"):
    return {
        "id": identity,
        "text": text,
        "occurred_start": "2026-10-01",
        "attribution": {"speaker": "user", "uncertain": True},
    }


def lookup_record(number, *, phase="tool", query="prior history", limit=8, results=()):
    common = {
        "lookup_contract": "ade-memory-lookup-v2",
        "lookup_number": number,
        "phase": phase,
        "bank_id": BANK,
        "query": query,
        "limit": limit,
    }
    return [
        {"type": "memory_lookup.started", "value": common},
        {
            "type": "memory_lookup.completed",
            "value": {
                **common,
                "response": {"results": list(results)},
                "selected_ids": [row["id"] for row in results[:limit]],
            },
        },
    ]


def serial_capture(groups=None):
    groups = groups or [
        [
            {
                "id": "call-1",
                "arguments": {"query": "prior history"},
                "results": [memory()],
            }
        ]
    ]
    records = lookup_record(1, phase="automatic", query="current input", limit=20)
    messages, chain, lookup_number = (
        [{"role": "user", "content": "current input"}],
        [],
        1,
    )
    for request_number in range(1, len(groups) + 2):
        request_id = f"request-{request_number}"
        start = {
            "request_id": request_id,
            "request_number": request_number,
            "stage": "conversation",
        }
        records.append({"type": "model_request.started", "value": start})
        group = groups[request_number - 1] if request_number <= len(groups) else []
        response = {"role": "assistant", "content": "final reply"}
        if group:
            response = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": item["id"],
                        "type": "function",
                        "function": {
                            "name": item.get("name", "search_memory"),
                            "arguments": json.dumps(item["arguments"]),
                        },
                    }
                    for item in group
                ],
            }
        chain.append(
            (
                start,
                {
                    "request": {"body": {"messages": copy.deepcopy(messages)}},
                    "outcome": {
                        "http_status": 200,
                        "visible_response": {
                            "choices": [{"message": copy.deepcopy(response)}]
                        },
                    },
                },
            )
        )
        records.append(
            {
                "type": "model_request.finished",
                "value": {"request_id": request_id, "status": "received"},
            }
        )
        if not group:
            continue
        messages.append(response)
        for item in group:
            name = item.get("name", "search_memory")
            content = {"ok": True, "weather": "synthetic"}
            if name == "search_memory":
                lookup_number += 1
                arguments = item["arguments"]
                limit = arguments.get("limit", 8)
                records.extend(
                    lookup_record(
                        lookup_number,
                        query=arguments["query"].strip(),
                        limit=limit,
                        results=item["results"],
                    )
                )
                content = {
                    "ok": True,
                    "scope": "current_user_character_relationship",
                    "memories": item["results"][:limit],
                }
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item["id"],
                    "name": name,
                    "content": json.dumps(content),
                }
            )
    records = copy.deepcopy(records)
    for sequence, row in enumerate(records, 1):
        row["sequence"] = sequence
    return chain, records


def tool_message(chain, *, request_index=1, call_index=0):
    previous = chain[request_index - 1][1]["request"]["body"]["messages"]
    return chain[request_index][1]["request"]["body"]["messages"][
        len(previous) + 1 + call_index
    ]


def tool_events(records):
    return [
        row
        for row in records
        if row["type"].startswith("memory_lookup.")
        and row["value"].get("phase") == "tool"
    ]
