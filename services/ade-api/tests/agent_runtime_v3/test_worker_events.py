from __future__ import annotations

import asyncio
from types import SimpleNamespace

from ade_api.features.agent_runtime_v3.worker_events import append_success_events


class _RecordingRunRepository:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def append_ordered_event(self, **event):
        row = {
            **event,
            "id": event["event_id"],
            "event_type": event["event_type"],
            "sequence": len(self.events) + 1,
        }
        self.events.append(row)
        return row


def test_success_events_pair_model_and_tool_boundaries() -> None:
    repository = _RecordingRunRepository()
    result = SimpleNamespace(
        context=SimpleNamespace(
            section_tokens={},
            estimated_input_tokens=10,
            omitted_message_ids=[],
            retrieved_fact_ids=[],
        ),
        executor=SimpleNamespace(
            model_request_count=2,
            provider_request_ids=["provider-1", None],
            tool_events=[
                {
                    "request_number": 1,
                    "call_id": "call-1",
                    "name": "search_memory",
                    "arguments": {"query": "Rocky", "limit": 3},
                    "result_count": 1,
                    "succeeded": True,
                    "error_type": None,
                }
            ],
            usage={"total_tokens": 12},
        ),
        reviewer=SimpleNamespace(
            model_request_count=1,
            provider_request_ids=[],
            protocol_repaired=False,
            usage={},
        ),
        review=SimpleNamespace(operations=[]),
    )

    asyncio.run(
        append_success_events(
            repository,
            run_id="run-1",
            attempt=1,
            result=result,
            committed=[],
            assistant_message_id="message-1",
        )
    )

    event_types = [event["event_type"] for event in repository.events]
    assert event_types.count("model.request.started") == 3
    assert event_types.count("model.response.completed") == 3
    assert event_types.count("tool.call.requested") == 1
    assert event_types.count("tool.call.completed") == 1
    conversation_trace = [
        event["event_type"]
        for event in repository.events
        if event["event_type"]
        in {
            "model.request.started",
            "model.response.completed",
            "tool.call.requested",
            "tool.call.completed",
        }
        and event["payload"].get("role") in {None, "conversation"}
    ][:6]
    assert conversation_trace == [
        "model.request.started",
        "model.response.completed",
        "tool.call.requested",
        "tool.call.completed",
        "model.request.started",
        "model.response.completed",
    ]

    for completed_type, requested_type in (
        ("model.response.completed", "model.request.started"),
        ("tool.call.completed", "tool.call.requested"),
    ):
        for completed in (
            event
            for event in repository.events
            if event["event_type"] == completed_type
        ):
            requested = next(
                event
                for event in repository.events
                if event["id"] == completed["causation_id"]
            )
            assert requested["event_type"] == requested_type

    responses = [
        event
        for event in repository.events
        if event["event_type"] == "model.response.completed"
    ]
    assert responses[0]["payload"]["provider_request_id"] == "provider-1"
    assert responses[1]["payload"]["provider_request_id"] is None
    first_tool_request = next(
        event
        for event in repository.events
        if event["event_type"] == "tool.call.requested"
    )
    first_conversation_response = next(
        event
        for event in repository.events
        if event["event_type"] == "model.response.completed"
        and event["payload"]["role"] == "conversation"
        and event["payload"]["request_number"] == 1
    )
    assert first_tool_request["causation_id"] == first_conversation_response["id"]
    completed = repository.events[-1]
    assert completed["event_type"] == "run.completed"
    assert completed["payload"]["model_request_count"] == 3
    assert completed["payload"]["usage"] == {"total_tokens": 12}


def test_compaction_events_and_provenance_are_emitted_in_execution_order() -> None:
    repository = _RecordingRunRepository()
    result = SimpleNamespace(
        context=SimpleNamespace(
            section_tokens={},
            estimated_input_tokens=10,
            omitted_message_ids=[],
            retrieved_fact_ids=[],
        ),
        executor=SimpleNamespace(
            model_request_count=1,
            provider_request_ids=["conversation-request"],
            tool_events=[],
            usage={"prompt_tokens": 10},
        ),
        reviewer=SimpleNamespace(
            model_request_count=1,
            provider_request_ids=["review-request"],
            protocol_repaired=False,
            usage={"completion_tokens": 2},
        ),
        review=SimpleNamespace(operations=[]),
        compaction=SimpleNamespace(
            provider_request_id="summary-request",
            usage={"prompt_tokens": 4, "completion_tokens": 1},
            plan=SimpleNamespace(source_message_ids=("message-1", "message-2")),
        ),
    )
    summary = {
        "id": "summary-1",
        "previous_summary_id": None,
        "version": 1,
        "through_sequence": 2,
        "run_id": "run-1",
        "model_key": "source::model",
        "model_fingerprint": "f" * 64,
        "provider_request_id": "summary-request",
        "content_sha256": "a" * 64,
        "prompt_sha256": "b" * 64,
        "input_sha256": "c" * 64,
        "policy_sha256": "d" * 64,
    }

    asyncio.run(
        append_success_events(
            repository,
            run_id="run-1",
            attempt=1,
            result=result,
            committed=[],
            assistant_message_id="message-3",
            summary=summary,
        )
    )

    event_types = [event["event_type"] for event in repository.events]
    assert event_types[:3] == [
        "model.request.started",
        "model.response.completed",
        "context.built",
    ]
    summary_event = next(
        event
        for event in repository.events
        if event["event_type"] == "summary.committed"
    )
    assert summary_event["payload"]["model_fingerprint"] == "f" * 64
    assert summary_event["payload"]["source_message_ids"] == [
        "message-1",
        "message-2",
    ]
    completed = repository.events[-1]
    assert completed["payload"]["model_request_counts"] == {
        "conversation": 1,
        "reviewer": 1,
        "compaction": 1,
    }
    assert completed["payload"]["usage"] == {
        "prompt_tokens": 14,
        "completion_tokens": 3,
    }
