from __future__ import annotations

from typing import Any

from .events import append_run_event
from .persistence.runs import RunRepository
from .turn_execution import AttemptResult


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
    await append_run_event(
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
    )
    await _append_model_rounds(
        runs,
        run_id=run_id,
        attempt=attempt,
        role="conversation",
        request_count=result.executor.model_request_count,
        provider_request_ids=result.executor.provider_request_ids,
    )
    await _append_tool_calls(
        runs,
        run_id=run_id,
        attempt=attempt,
        tool_events=result.executor.tool_events,
    )
    await _append_model_rounds(
        runs,
        run_id=run_id,
        attempt=attempt,
        role="reviewer",
        request_count=result.reviewer.model_request_count,
        provider_request_ids=result.reviewer.provider_request_ids,
    )
    if result.reviewer.protocol_repaired:
        await append_run_event(
            runs,
            run_id=run_id,
            event_type="model.protocol_repaired",
            payload={"role": "reviewer", "repair_count": 1},
            attempt=attempt,
        )
    if compaction is not None:
        await _append_model_rounds(
            runs,
            run_id=run_id,
            attempt=attempt,
            role="compaction",
            request_count=1,
            provider_request_ids=[compaction.provider_request_id]
            if compaction.provider_request_id
            else [],
        )
    proposal_events = []
    for operation in result.review.operations:
        proposal_events.append(
            await append_run_event(
                runs,
                run_id=run_id,
                event_type="memory.proposed",
                payload={
                    "operation": operation.proposal.operation.value,
                    "fact_type": operation.proposal.fact_type,
                    "fact_id": getattr(operation.proposal, "fact_id", None),
                    "target_fact_ids": getattr(
                        operation.proposal, "target_fact_ids", []
                    ),
                },
                attempt=attempt,
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
    await append_run_event(
        runs,
        run_id=run_id,
        event_type="message.committed",
        payload={"message_id": assistant_message_id, "role": "assistant"},
        attempt=attempt,
    )
    if summary is not None:
        await append_run_event(
            runs,
            run_id=run_id,
            event_type="conversation.compacted",
            payload={
                "summary_id": str(summary["id"]),
                "previous_summary_id": summary["previous_summary_id"],
                "version": int(summary["version"]),
                "through_sequence": int(summary["through_sequence"]),
                "model_key": summary["model_key"],
                "provider_request_id": summary["provider_request_id"],
                "prompt_sha256": summary["prompt_sha256"],
                "input_sha256": summary["input_sha256"],
            },
            attempt=attempt,
        )
    conversation_requests = result.executor.model_request_count
    reviewer_requests = result.reviewer.model_request_count
    compaction_requests = 1 if compaction is not None else 0
    await append_run_event(
        runs,
        run_id=run_id,
        event_type="run.completed",
        payload={
            "attempt_count": attempt,
            "model_request_count": conversation_requests + reviewer_requests + compaction_requests,
            "model_request_counts": {
                "conversation": conversation_requests,
                "reviewer": reviewer_requests,
                "compaction": compaction_requests,
            },
            "memory_revision_count": len(committed),
            "usage": result.executor.usage,
        },
        attempt=attempt,
    )


async def _append_model_rounds(
    runs: RunRepository,
    *,
    run_id: str,
    attempt: int,
    role: str,
    request_count: int,
    provider_request_ids: list[str],
) -> None:
    for index in range(1, request_count + 1):
        requested = await append_run_event(
            runs,
            run_id=run_id,
            event_type="model.request.started",
            payload={"role": role, "request_number": index},
            attempt=attempt,
        )
        provider_request_id = (
            provider_request_ids[index - 1]
            if index <= len(provider_request_ids)
            else None
        )
        await append_run_event(
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


async def _append_tool_calls(
    runs: RunRepository,
    *,
    run_id: str,
    attempt: int,
    tool_events: list[dict[str, Any]],
) -> None:
    for tool in tool_events:
        requested = await append_run_event(
            runs,
            run_id=run_id,
            event_type="tool.call.requested",
            payload={
                "call_id": tool["call_id"],
                "name": tool["name"],
                "arguments": tool["arguments"],
            },
            attempt=attempt,
        )
        await append_run_event(
            runs,
            run_id=run_id,
            event_type="tool.call.completed",
            payload={
                "call_id": tool["call_id"],
                "name": tool["name"],
                "result_count": tool["result_count"],
            },
            attempt=attempt,
            causation_id=str(requested["id"]),
        )
