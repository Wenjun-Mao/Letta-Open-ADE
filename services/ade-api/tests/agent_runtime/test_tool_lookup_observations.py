"""Real executor/recall private chronology with controlled, offline boundaries."""

import asyncio
import copy
import time

import pytest

from ade_api.features.agent_runtime.executor import ConversationExecutor, curated_tools
from ade_api.features.agent_runtime.provider_tracing import AttemptTrace
from ade_api.features.agent_runtime.turn_recall import MemoryLookupError, TurnRecall
from ade_api.integrations.hindsight import HindsightError
from workflows.evals.hindsight_integration.capture_components import (
    validate_conversation_chain,
)
from workflows.evals.hindsight_integration.tool_provenance import (
    validate_tool_provenance,
)


class Banks:
    async def ensure_ready(self, *args, **kwargs):
        return {"state": "ready"}


class Native:
    def __init__(self, *, fail_tool=False, interrupt_tool=False):
        self.calls = 0
        self.fail_tool = fail_tool
        self.interrupt_tool = interrupt_tool

    async def recall(self, bank, payload):
        self.calls += 1
        if self.interrupt_tool and self.calls > 1:
            await asyncio.Future()
        if self.fail_tool and self.calls > 1:
            raise HindsightError("hindsight_unavailable")
        return {
            "results": [
                {"id": "same-id", "text": f"Native value for lookup {self.calls}"},
                {"id": "second-id", "text": "Second native row"},
            ]
        }


class Character:
    def __init__(self):
        self.requests = []
        self.responses = []

    async def chat_completion(self, payload, **kwargs):
        self.requests.append(copy.deepcopy(payload))
        if len(self.requests) == 1:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-a",
                        "type": "function",
                        "function": {
                            "name": "search_memory",
                            "arguments": '{"query":"  same query  ","limit":1}',
                        },
                    },
                    {
                        "id": "call-b",
                        "type": "function",
                        "function": {
                            "name": "search_memory",
                            "arguments": '{"query":"same query","limit":1}',
                        },
                    },
                ],
            }
        else:
            message = {"role": "assistant", "content": "final reply"}
        self.responses.append(message)
        return {
            "choices": [
                {
                    "message": message,
                    "finish_reason": "tool_calls"
                    if len(self.requests) == 1
                    else "stop",
                }
            ]
        }


async def collect(*, fail_tool=False, interrupt_tool=False):
    records, native, character = (
        [],
        Native(fail_tool=fail_tool, interrupt_tool=interrupt_tool),
        Character(),
    )
    trace = AttemptTrace(attempt=1)

    def record(event, value):
        records.append(
            {"sequence": len(records) + 1, "type": event, "value": copy.deepcopy(value)}
        )

    trace.record_private = record
    recall = TurnRecall(
        banks=Banks(),
        client=native,
        bank_id="owned-bank",
        deadline=time.monotonic() + 10,
        trace=trace,
    )
    await recall.lookup("immutable current input")
    failure = None
    try:
        async with asyncio.timeout(0.05 if interrupt_tool else 2):
            await ConversationExecutor(
                trace.transport(character, stage="conversation")
            ).execute(
                model_key="synthetic::character",
                messages=[{"role": "user", "content": "immutable current input"}],
                timeout_seconds=1,
                max_output_tokens=256,
                tools=curated_tools(["search_memory"], search_memory=recall.search),
            )
    except (MemoryLookupError, TimeoutError) as error:
        failure = error
    assert trace.observation_incomplete is False
    assert trace.memory_lookup_active is False
    starts = [row["value"] for row in records if row["type"] == "model_request.started"]
    chain = [
        (
            start,
            {
                "request": {"body": request},
                "outcome": {
                    "http_status": 200,
                    "visible_response": {"choices": [{"message": response}]},
                },
            },
        )
        for start, request, response in zip(
            starts, character.requests, character.responses, strict=True
        )
    ]
    return chain, records, native, failure


def test_executor_serial_chronology_binds_repeated_queries_to_exact_native_objects():
    chain, records, native, failure = asyncio.run(collect())
    assert failure is None and native.calls == 3
    bindings = validate_conversation_chain(
        chain, "final reply", records, bank_id="owned-bank"
    )
    assert [binding["lookup_number"] for binding in bindings.values()] == [2, 3]
    starts = [row["value"] for row in records if row["type"] == "memory_lookup.started"]
    assert starts[0]["query"] == "immutable current input" and starts[0]["limit"] == 20
    assert [value["query"] for value in starts[1:]] == ["same query", "same query"]
    assert [value["limit"] for value in starts[1:]] == [1, 1]
    changed = copy.deepcopy(chain)
    tools = [
        row
        for row in changed[1][1]["request"]["body"]["messages"]
        if row["role"] == "tool"
    ]
    tools[0]["content"], tools[1]["content"] = tools[1]["content"], tools[0]["content"]
    with pytest.raises(ValueError, match="tool_lookup_projection_mismatch"):
        validate_conversation_chain(
            changed, "final reply", records, bank_id="owned-bank"
        )


def test_failed_native_tool_lookup_has_no_apology_dispatch_or_false_empty_projection():
    chain, records, native, failure = asyncio.run(collect(fail_tool=True))
    assert isinstance(failure, MemoryLookupError)
    assert len(chain) == 1 and native.calls == 2
    assert records[-1]["type"] == "memory_lookup.failed"
    assert records[-1]["value"]["lookup_number"] == 2
    assert (
        validate_tool_provenance(chain, records, "owned-bank", successful=False) == {}
    )


def test_attempt_timeout_during_native_tool_lookup_preserves_interrupted_prefix():
    chain, records, native, failure = asyncio.run(collect(interrupt_tool=True))
    assert isinstance(failure, TimeoutError)
    assert len(chain) == 1 and native.calls == 2
    assert records[-1]["type"] == "memory_lookup.started"
    assert records[-1]["value"]["lookup_number"] == 2
    assert (
        validate_tool_provenance(chain, records, "owned-bank", successful=False) == {}
    )
    with pytest.raises(ValueError, match="tool_lookup_unfinished"):
        validate_tool_provenance(chain, records, "owned-bank", successful=True)
