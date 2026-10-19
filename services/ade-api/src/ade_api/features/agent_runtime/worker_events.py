from __future__ import annotations

from typing import Any

from .events import append_run_event
from .persistence.runs import RunRepository
from .provider_tracing import AttemptTrace
from .request_counts import dispatch_counts
from .tool_policy import ToolRequirement
from .turn_result import AttemptResult


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

    async def persist() -> None:
        nonlocal last_event_id
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

    try:
        connection = getattr(runs, "_connection", None)
        if connection is None:
            await persist()
        else:
            async with connection.begin_nested():
                await persist()
    except Exception:
        return causation_id
    return last_event_id


async def append_success_events(
    runs: RunRepository,
    *,
    run_id: str,
    attempt: int,
    result: AttemptResult,
    assistant_message_id: str,
    delivery_operation_id: str,
    trace: AttemptTrace | None = None,
    summary: dict[str, Any] | None = None,
) -> None:
    compaction = getattr(result, "compaction", None)
    context_event = await append_run_event(
        runs,
        run_id=run_id,
        event_type="context.built",
        payload={
            "section_tokens": result.context.section_tokens,
            "estimated_input_tokens": result.context.estimated_input_tokens,
            "omitted_message_ids": result.context.omitted_message_ids,
            "current_chat": result.context.current_chat,
            "automatic_memory_ids": result.context.retrieved_fact_ids,
            "tool_memory_ids": list(
                dict.fromkeys(
                    identity
                    for lookup in result.memory_lookups
                    if lookup["phase"] == "tool"
                    for identity in lookup["result_ids"]
                )
            ),
        },
        attempt=attempt,
        causation_id=None,
    )
    conversation_event_id = await _append_conversation_trace(
        runs,
        run_id=run_id,
        attempt=attempt,
        tool_events=result.executor.tool_events,
        tool_requirement=result.executor.tool_requirement,
        tool_requirement_satisfied=result.executor.tool_requirement_satisfied,
        causation_id=str(context_event["id"]),
    )
    message_event = await append_run_event(
        runs,
        run_id=run_id,
        event_type="message.committed",
        payload={"message_id": assistant_message_id, "role": "assistant"},
        attempt=attempt,
        causation_id=conversation_event_id,
    )
    await append_run_event(
        runs,
        run_id=run_id,
        event_type="memory.delivery.queued",
        payload={
            "operation_id": delivery_operation_id,
            "message_id": assistant_message_id,
        },
        attempt=attempt,
        causation_id=str(message_event["id"]),
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
            causation_id=terminal_causation_id,
        )
        terminal_causation_id = str(summary_event["id"])
    conversation_requests = result.executor.model_request_count
    compaction_requests = 1 if compaction is not None else 0
    usage_by_role = {
        "conversation": result.executor.usage,
        "compaction": compaction.usage if compaction is not None else {},
    }
    await append_run_event(
        runs,
        run_id=run_id,
        event_type="run.completed",
        payload={
            "attempt_count": attempt,
            "model_request_count": conversation_requests + compaction_requests,
            "model_request_counts": {
                "conversation": conversation_requests,
                "compaction": compaction_requests,
            },
            "memory_lookups": list(result.memory_lookups),
            "usage": _combined_usage(usage_by_role.values()),
            "usage_by_role": usage_by_role,
            "dispatch_counts": dispatch_counts(
                (
                    {"event_type": event.event_type, "payload": event.payload}
                    for event in trace.normalized_events()
                ),
                observation_incomplete=trace.observation_incomplete,
            )
            if trace is not None
            else {"complete": False, "groups": []},
        },
        attempt=attempt,
        causation_id=terminal_causation_id,
    )


async def _append_conversation_trace(
    runs: RunRepository,
    *,
    run_id: str,
    attempt: int,
    tool_events: list[dict[str, Any]],
    tool_requirement: ToolRequirement | None,
    tool_requirement_satisfied: bool,
    causation_id: str | None,
) -> str | None:
    last_event_id = causation_id
    requirement_event_written = False
    if tool_requirement is not None:
        resolved = await append_run_event(
            runs,
            run_id=run_id,
            event_type="tool.requirement.resolved",
            payload=tool_requirement.safe_payload(),
            attempt=attempt,
            causation_id=last_event_id,
        )
        last_event_id = str(resolved["id"])
    for tool in tool_events:
        last_event_id = await _append_tool_call(
            runs,
            run_id=run_id,
            attempt=attempt,
            tool=tool,
            causation_id=str(last_event_id),
        )
        if (
            tool_requirement is not None
            and not requirement_event_written
            and str(tool["name"]) == tool_requirement.tool_name
        ):
            satisfied = await append_run_event(
                runs,
                run_id=run_id,
                event_type="tool.requirement.satisfied",
                payload=tool_requirement.safe_payload(),
                attempt=attempt,
                causation_id=last_event_id,
            )
            last_event_id = str(satisfied["id"])
            requirement_event_written = True
    if tool_requirement is not None and (
        not tool_requirement_satisfied or not requirement_event_written
    ):
        raise ValueError(
            "successful executor result did not satisfy its tool requirement"
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
