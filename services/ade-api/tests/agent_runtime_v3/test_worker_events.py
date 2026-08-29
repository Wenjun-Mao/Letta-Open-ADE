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
            provider_request_ids=["provider-1"],
            tool_events=[
                {
                    "call_id": "call-1",
                    "name": "search_memory",
                    "arguments": {"query": "Rocky", "limit": 3},
                    "result_count": 1,
                }
            ],
            usage={"total_tokens": 12},
        ),
        reviewer=SimpleNamespace(
            model_request_count=1,
            provider_request_ids=[],
            protocol_repaired=False,
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
    completed = repository.events[-1]
    assert completed["event_type"] == "run.completed"
    assert completed["payload"]["model_request_count"] == 3
