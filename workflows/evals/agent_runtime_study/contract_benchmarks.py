from __future__ import annotations

import asyncio
from typing import Any

from .contracts import (
    AgentDefinition,
    Conversation,
    MemoryOperation,
    MemorySubject,
    RunEventType,
    RunStatus,
    RuntimePolicy,
    TurnRequest,
)
from .memory_review import (
    MemoryReviewDecision,
    MemoryReviewProposal,
    MemoryReviewRequest,
)
from .repository import InMemoryStudyRepository
from .runtime import StudyAgentRuntime
from .scripted import (
    ScriptStep,
    ScriptToolCall,
    SharedScript,
    scripted_adapter,
)
from .tools import CURATED_TOOL_DEFINITIONS


class _ContractMemoryReviewer:
    model_key = "scripted-reviewer"

    async def review(self, request: MemoryReviewRequest) -> MemoryReviewDecision:
        proposals = ()
        if "My name is Alice" in request.current_user_message.content:
            proposals = (
                MemoryReviewProposal(
                    operation=MemoryOperation.ADD,
                    fact_type="person.name",
                    value="Alice",
                    evidence_quote="My name is Alice",
                ),
            )
        return MemoryReviewDecision(
            reviewer_model_key=self.model_key,
            proposals=proposals,
            raw_responses=(),
            usage={},
            model_request_count=1,
            protocol_repaired=False,
        )


def _runtime(adapter_name: str, script: SharedScript):
    repository = InMemoryStudyRepository()
    repository.add_agent_definition(
        AgentDefinition(
            id="agent_contract",
            name="contract",
            model_key="scripted-model",
            system_prompt="Use tools when requested.",
            persona="Concise test persona.",
            tool_names=tuple(tool.name for tool in CURATED_TOOL_DEFINITIONS),
        )
    )
    repository.add_subject(
        MemorySubject(id="subject_contract", external_key="contract")
    )
    repository.add_conversation(
        Conversation(
            id="conversation_contract",
            agent_definition_id="agent_contract",
            memory_subject_id="subject_contract",
        )
    )
    runtime = StudyAgentRuntime(
        repository=repository,
        executor=scripted_adapter(adapter_name, script),
        memory_reviewer=_ContractMemoryReviewer(),
    )
    return runtime, repository


async def _single(
    adapter_name: str,
    steps: tuple[ScriptStep, ...],
    *,
    user: str = "hello",
    policy: RuntimePolicy | None = None,
    cancellation: asyncio.Event | None = None,
):
    script = SharedScript(steps)
    runtime, repository = _runtime(adapter_name, script)
    result = await runtime.run_turn(
        TurnRequest(
            conversation_id="conversation_contract",
            user_content=user,
            idempotency_key="contract-turn",
            policy=policy or RuntimePolicy(timeout_seconds=2.0),
            cancellation=cancellation,
        )
    )
    return result, script, repository, runtime


async def run_contract_benchmarks(
    adapter_names: tuple[str, ...] = ("custom_loop", "pydantic_ai"),
) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for adapter_name in adapter_names:
        checks: list[dict[str, Any]] = []

        normal, normal_script, _, _ = await _single(
            adapter_name,
            (ScriptStep(text="hello", reasoning="private plan"),),
        )
        checks.append(
            _check(
                "normal_reply_and_reasoning",
                normal.run.status is RunStatus.SUCCEEDED
                and normal.assistant_message is not None
                and normal.assistant_message.content == "hello"
                and normal.reasoning == ("private plan",)
                and normal_script.request_count == 1,
                normal,
            )
        )

        empty_repaired, empty_script, _, _ = await _single(
            adapter_name,
            (
                ScriptStep(reasoning="unfinished private reasoning"),
                ScriptStep(text="repaired answer"),
            ),
        )
        checks.append(
            _check(
                "reasoning_only_completion_recovers",
                empty_repaired.run.status is RunStatus.SUCCEEDED
                and empty_repaired.assistant_message is not None
                and empty_repaired.assistant_message.content == "repaired answer"
                and empty_script.request_count == 2
                and _event_count(empty_repaired, RunEventType.PROTOCOL_REPAIR) == 1,
                empty_repaired,
            )
        )

        multi, _, multi_repo, _ = await _single(
            adapter_name,
            (
                ScriptStep(
                    tool_calls=(
                        ScriptToolCall(
                            name="get_weather",
                            arguments={"city": "Toronto"},
                            call_id="weather-1",
                        ),
                    )
                ),
                ScriptStep(text="Alice, Toronto is clear at 21 C."),
            ),
            user="My name is Alice. Check Toronto weather.",
        )
        active = multi_repo.list_subject_facts("subject_contract", active_only=True)
        checks.append(
            _check(
                "multiple_tool_steps",
                multi.run.status is RunStatus.SUCCEEDED
                and len(multi.tool_executions) == 1
                and len(active) == 1
                and active[0].value == "Alice",
                multi,
            )
        )

        malformed, malformed_script, _, _ = await _single(
            adapter_name,
            (
                ScriptStep(
                    tool_calls=(
                        ScriptToolCall(
                            name="get_weather",
                            arguments="{not-json",
                            call_id="malformed-1",
                        ),
                    )
                ),
                ScriptStep(text="I could not parse that tool call."),
            ),
        )
        checks.append(
            _check(
                "malformed_arguments_are_traceable",
                malformed_script.request_count in {1, 2}
                and bool(malformed.events)
                and (
                    malformed.run.status is RunStatus.SUCCEEDED
                    or malformed.run.status is RunStatus.FAILED
                ),
                malformed,
                diagnostic_only=True,
            )
        )
        checks.append(
            _check(
                "malformed_arguments_recover",
                malformed.run.status is RunStatus.SUCCEEDED
                and malformed_script.request_count == 2,
                malformed,
            )
        )

        retried, retry_script, _, _ = await _single(
            adapter_name,
            (ScriptStep(error_status=503), ScriptStep(text="recovered")),
            policy=RuntimePolicy(timeout_seconds=2.0, retry_count=1),
        )
        checks.append(
            _check(
                "one_additional_retry_is_exact",
                retried.run.status is RunStatus.SUCCEEDED
                and retried.run.attempt_count == 2
                and retry_script.request_count == 2
                and _event_count(retried, RunEventType.RETRY_SCHEDULED) == 1,
                retried,
            )
        )

        no_retry, no_retry_script, _, _ = await _single(
            adapter_name,
            (ScriptStep(error_status=503), ScriptStep(text="must-not-run")),
            policy=RuntimePolicy(timeout_seconds=2.0, retry_count=0),
        )
        checks.append(
            _check(
                "zero_retry_is_exact",
                no_retry.run.status is RunStatus.FAILED
                and no_retry.run.attempt_count == 1
                and no_retry_script.request_count == 1,
                no_retry,
            )
        )

        nontransient, nontransient_script, _, _ = await _single(
            adapter_name,
            (ScriptStep(error_status=400), ScriptStep(text="must-not-run")),
            policy=RuntimePolicy(timeout_seconds=2.0, retry_count=2),
        )
        checks.append(
            _check(
                "nontransient_error_is_not_retried",
                nontransient.run.status is RunStatus.FAILED
                and nontransient_script.request_count == 1,
                nontransient,
            )
        )

        timeout, timeout_script, _, _ = await _single(
            adapter_name,
            (
                ScriptStep(text="late", delay_seconds=0.08),
                ScriptStep(text="late-again", delay_seconds=0.08),
            ),
            policy=RuntimePolicy(timeout_seconds=0.02, retry_count=1),
        )
        checks.append(
            _check(
                "whole_attempt_timeout_is_exact",
                timeout.run.status is RunStatus.FAILED
                and timeout.run.attempt_count == 2
                and timeout_script.request_count == 2,
                timeout,
            )
        )

        cancel_event = asyncio.Event()
        cancel_task = asyncio.create_task(
            _single(
                adapter_name,
                (ScriptStep(text="too late", delay_seconds=1.0),),
                policy=RuntimePolicy(timeout_seconds=2.0),
                cancellation=cancel_event,
            )
        )
        await asyncio.sleep(0.02)
        cancel_event.set()
        cancelled, _, cancel_repo, _ = await cancel_task
        checks.append(
            _check(
                "cancellation_has_no_partial_assistant_or_memory_commit",
                cancelled.run.status is RunStatus.CANCELLED
                and cancelled.assistant_message is None
                and not cancel_repo.list_subject_facts(
                    "subject_contract", active_only=False
                ),
                cancelled,
            )
        )

        failed_tool, _, _, _ = await _single(
            adapter_name,
            (
                ScriptStep(
                    tool_calls=(
                        ScriptToolCall(
                            name="get_weather",
                            arguments={"city": "FAIL_CITY"},
                            call_id="weather-fail",
                        ),
                    )
                ),
                ScriptStep(text="The weather tool failed."),
            ),
        )
        checks.append(
            _check(
                "tool_failure_is_returned_and_traced",
                failed_tool.run.status is RunStatus.SUCCEEDED
                and any(
                    not execution.succeeded for execution in failed_tool.tool_executions
                )
                and _event_count(failed_tool, RunEventType.TOOL_RESULT) >= 1,
                failed_tool,
            )
        )

        idempotent_script = SharedScript((ScriptStep(text="once"),))
        idempotent_runtime, _ = _runtime(adapter_name, idempotent_script)
        idempotent_request = TurnRequest(
            conversation_id="conversation_contract",
            user_content="hello",
            idempotency_key="same-key",
            policy=RuntimePolicy(timeout_seconds=2.0),
        )
        first = await idempotent_runtime.run_turn(idempotent_request)
        second = await idempotent_runtime.run_turn(idempotent_request)
        checks.append(
            _check(
                "idempotency_replays_terminal_result",
                first.run.id == second.run.id and idempotent_script.request_count == 1,
                second,
            )
        )

        rows[adapter_name] = {
            "adapter": adapter_name,
            "checks": checks,
            "passed": sum(1 for check in checks if check["pass"]),
            "failed": sum(1 for check in checks if not check["pass"]),
            "mandatory_pass": all(
                check["pass"]
                for check in checks
                if not check.get("diagnostic_only", False)
            ),
        }
    return rows


def _event_count(result, event_type: RunEventType) -> int:
    return sum(1 for event in result.events if event.type is event_type)


def _check(
    name: str,
    passed: bool,
    result,
    *,
    diagnostic_only: bool = False,
) -> dict[str, Any]:
    tool_call_ids = [
        str(event.payload.get("call_id"))
        for event in result.events
        if event.type is RunEventType.TOOL_CALL
    ]
    tool_result_ids = [
        str(event.payload.get("call_id"))
        for event in result.events
        if event.type is RunEventType.TOOL_RESULT
    ]
    return {
        "name": name,
        "pass": bool(passed),
        "diagnostic_only": diagnostic_only,
        "run_status": result.run.status.value,
        "attempt_count": result.run.attempt_count,
        "event_types": [event.type.value for event in result.events],
        "tool_executions": len(result.tool_executions),
        "tool_call_ids": tool_call_ids,
        "tool_result_ids": tool_result_ids,
        "tool_execution_call_ids": [
            execution.call_id for execution in result.tool_executions
        ],
        "tool_trace_correlated": (
            sorted(tool_call_ids)
            == sorted(tool_result_ids)
            == sorted(execution.call_id for execution in result.tool_executions)
        ),
        "error_type": result.run.error_type,
        "error_message": result.run.error_message,
    }
