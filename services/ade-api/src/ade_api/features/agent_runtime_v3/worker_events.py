from __future__ import annotations

from typing import Any

from .events import append_run_event
from .persistence.runs import RunRepository
from .provider_tracing import AttemptTrace
from .turn_execution import AttemptResult


async def append_attempt_trace(
    runs: RunRepository,
    *,
    run_id: str,
    attempt: int,
    trace: AttemptTrace,
    causation_id: str | None,
) -> str | None:
    """Persist the safe partial provider trace inside attempt finalization."""

    last_event_id = causation_id
    for trace_event in trace.normalized_events():
        event = await append_run_event(
            runs,
            run_id=run_id,
            event_type=trace_event.event_type,
            payload=trace_event.payload,
            attempt=attempt,
            causation_id=last_event_id,
        )
        last_event_id = str(event["id"])
    return last_event_id


async def append_success_events(
    runs: RunRepository,
    *,
    run_id: str,
    attempt: int,
    result: AttemptResult,
    committed: list[dict[str, Any]],
    assistant_message_id: str,
    summary: dict[str, Any] | None = None,
) -> None:
    compaction = getattr(result, "compaction", None)
    compaction_event_id: str | None = None
    if compaction is not None:
        compaction_event_id = await _append_model_rounds(
            runs,
            run_id=run_id,
            attempt=attempt,
            role="compaction",
            request_count=1,
            provider_request_ids=[compaction.provider_request_id],
        )
    context_event = await append_run_event(
        runs,
        run_id=run_id,
        event_type="context.built",
        payload={
            "section_tokens": result.context.section_tokens,
            "estimated_input_tokens": result.context.estimated_input_tokens,
            "omitted_message_ids": result.context.omitted_message_ids,
            "retrieved_fact_ids": result.context.retrieved_fact_ids,
        },
        attempt=attempt,
        causation_id=compaction_event_id,
    )
    conversation_event_id = await _append_conversation_trace(
        runs,
        run_id=run_id,
        attempt=attempt,
        request_count=result.executor.model_request_count,
        provider_request_ids=result.executor.provider_request_ids,
        tool_events=result.executor.tool_events,
        causation_id=str(context_event["id"]),
    )
    reviewer_event_id = await _append_model_rounds(
        runs,
        run_id=run_id,
        attempt=attempt,
        role="reviewer",
        request_count=result.reviewer.model_request_count,
        provider_request_ids=result.reviewer.provider_request_ids,
        causation_id=conversation_event_id,
    )
    if result.reviewer.protocol_repaired:
        repaired = await append_run_event(
            runs,
            run_id=run_id,
            event_type="model.protocol_repaired",
            payload={"role": "reviewer", "repair_count": 1},
            attempt=attempt,
            causation_id=reviewer_event_id,
        )
        reviewer_event_id = str(repaired["id"])
    proposal_events = []
    for operation in result.review.operations:
        proposal_events.append(
            await append_run_event(
                runs,
                run_id=run_id,
                event_type="memory.proposed",
                payload={
                    "operation": operation.proposal.operation.value,
                    "fact_type": operation.fact_type,
                    "fact_id": getattr(operation.proposal, "fact_id", None),
                    "target_fact_ids": getattr(
                        operation.proposal, "target_fact_ids", []
                    ),
                },
                attempt=attempt,
                causation_id=reviewer_event_id,
            )
        )
    for index, memory in enumerate(committed):
        causation_id = (
            str(proposal_events[index]["id"]) if index < len(proposal_events) else None
        )
        await append_run_event(
            runs,
            run_id=run_id,
            event_type="memory.committed",
            payload=memory,
            attempt=attempt,
            causation_id=causation_id,
        )
    message_event = await append_run_event(
        runs,
        run_id=run_id,
        event_type="message.committed",
        payload={"message_id": assistant_message_id, "role": "assistant"},
        attempt=attempt,
        causation_id=reviewer_event_id,
    )
    terminal_causation_id = str(message_event["id"])
    if summary is not None:
        summary_event = await append_run_event(
            runs,
            run_id=run_id,
            event_type="summary.committed",
            payload={
                "summary_id": str(summary["id"]),
                "previous_summary_id": summary["previous_summary_id"],
                "version": int(summary["version"]),
                "through_sequence": int(summary["through_sequence"]),
                "run_id": str(summary["run_id"]),
                "model_key": summary["model_key"],
                "model_fingerprint": summary["model_fingerprint"],
                "provider_request_id": summary["provider_request_id"],
                "content_sha256": summary["content_sha256"],
                "prompt_sha256": summary["prompt_sha256"],
                "input_sha256": summary["input_sha256"],
                "policy_sha256": summary["policy_sha256"],
                "source_message_ids": list(compaction.plan.source_message_ids),
            },
            attempt=attempt,
            causation_id=compaction_event_id,
        )
        terminal_causation_id = str(summary_event["id"])
    conversation_requests = result.executor.model_request_count
    reviewer_requests = result.reviewer.model_request_count
    compaction_requests = 1 if compaction is not None else 0
    usage_by_role = {
        "conversation": result.executor.usage,
        "reviewer": result.reviewer.usage,
        "compaction": compaction.usage if compaction is not None else {},
    }
    await append_run_event(
        runs,
        run_id=run_id,
        event_type="run.completed",
        payload={
            "attempt_count": attempt,
            "model_request_count": conversation_requests
            + reviewer_requests
            + compaction_requests,
            "model_request_counts": {
                "conversation": conversation_requests,
                "reviewer": reviewer_requests,
                "compaction": compaction_requests,
            },
            "memory_revision_count": len(committed),
            "usage": _combined_usage(usage_by_role.values()),
            "usage_by_role": usage_by_role,
        },
        attempt=attempt,
        causation_id=terminal_causation_id,
    )


async def _append_model_rounds(
    runs: RunRepository,
    *,
    run_id: str,
    attempt: int,
    role: str,
    request_count: int,
    provider_request_ids: list[str | None],
    causation_id: str | None = None,
) -> str | None:
    last_event_id = causation_id
    for index in range(1, request_count + 1):
        requested = await append_run_event(
            runs,
            run_id=run_id,
            event_type="model.request.started",
            payload={"role": role, "request_number": index},
            attempt=attempt,
            causation_id=last_event_id,
        )
        provider_request_id = (
            provider_request_ids[index - 1]
            if index <= len(provider_request_ids)
            else None
        )
        completed = await append_run_event(
            runs,
            run_id=run_id,
            event_type="model.response.completed",
            payload={
                "role": role,
                "request_number": index,
                "provider_request_id": provider_request_id,
            },
            attempt=attempt,
            causation_id=str(requested["id"]),
        )
        last_event_id = str(completed["id"])
    return last_event_id


async def _append_conversation_trace(
    runs: RunRepository,
    *,
    run_id: str,
    attempt: int,
    request_count: int,
    provider_request_ids: list[str | None],
    tool_events: list[dict[str, Any]],
    causation_id: str | None,
) -> str | None:
    last_event_id = causation_id
    for request_number in range(1, request_count + 1):
        requested = await append_run_event(
            runs,
            run_id=run_id,
            event_type="model.request.started",
            payload={"role": "conversation", "request_number": request_number},
            attempt=attempt,
            causation_id=last_event_id,
        )
        provider_request_id = (
            provider_request_ids[request_number - 1]
            if request_number <= len(provider_request_ids)
            else None
        )
        response = await append_run_event(
            runs,
            run_id=run_id,
            event_type="model.response.completed",
            payload={
                "role": "conversation",
                "request_number": request_number,
                "provider_request_id": provider_request_id,
            },
            attempt=attempt,
            causation_id=str(requested["id"]),
        )
        last_event_id = str(response["id"])
        for tool in (
            item
            for item in tool_events
            if int(item["request_number"]) == request_number
        ):
            last_event_id = await _append_tool_call(
                runs,
                run_id=run_id,
                attempt=attempt,
                tool=tool,
                causation_id=str(response["id"]),
            )
    return last_event_id


async def _append_tool_call(
    runs: RunRepository,
    *,
    run_id: str,
    attempt: int,
    tool: dict[str, Any],
    causation_id: str,
) -> str:
    requested = await append_run_event(
        runs,
        run_id=run_id,
        event_type="tool.call.requested",
        payload={
            "call_id": tool["call_id"],
            "name": tool["name"],
            "arguments": tool["arguments"],
            "request_number": tool["request_number"],
        },
        attempt=attempt,
        causation_id=causation_id,
    )
    completed = await append_run_event(
        runs,
        run_id=run_id,
        event_type="tool.call.completed",
        payload={
            "call_id": tool["call_id"],
            "name": tool["name"],
            "request_number": tool["request_number"],
            "result_count": tool["result_count"],
            "succeeded": tool["succeeded"],
            "error_type": tool["error_type"],
        },
        attempt=attempt,
        causation_id=str(requested["id"]),
    )
    return str(completed["id"])


def _combined_usage(values) -> dict[str, int]:
    total: dict[str, int] = {}
    for usage in values:
        for key, value in usage.items():
            if isinstance(value, int) and not isinstance(value, bool):
                total[str(key)] = total.get(str(key), 0) + value
    return total
