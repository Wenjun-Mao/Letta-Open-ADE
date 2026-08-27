from __future__ import annotations

import asyncio
import hashlib
import json
import time
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict
from typing import Any

from .adapters.base import ExecutorError
from .context import ContextBuilder
from .contracts import (
    CancellationSignal,
    ExecutorAdapter,
    ExecutorRequest,
    MessageRole,
    RunEventType,
    RunStatus,
    TurnRequest,
    TurnResult,
)
from .memory import MemoryPolicy, MemoryRetriever
from .repository import InMemoryStudyRepository
from .tools import TurnToolSession, curated_tools


class NeverCancelled:
    def is_set(self) -> bool:
        return False


class _CancellationRequested(RuntimeError):
    pass


class RuntimeLockManager:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def _for_key(self, key: str) -> asyncio.Lock:
        async with self._guard:
            return self._locks.setdefault(key, asyncio.Lock())

    @asynccontextmanager
    async def acquire(self, *keys: str):
        locks = [await self._for_key(key) for key in sorted(set(keys))]
        for lock in locks:
            await lock.acquire()
        try:
            yield
        finally:
            for lock in reversed(locks):
                lock.release()


class StudyAgentRuntime:
    """ADE-owned orchestration around a replaceable model/tool executor."""

    def __init__(
        self,
        *,
        repository: InMemoryStudyRepository,
        executor: ExecutorAdapter,
    ) -> None:
        self.repository = repository
        self.executor = executor
        self.memory_policy = MemoryPolicy(repository)
        self.memory_retriever = MemoryRetriever(repository)
        self.context_builder = ContextBuilder(repository, self.memory_retriever)
        self.locks = RuntimeLockManager()

    async def run_turn(self, request: TurnRequest) -> TurnResult:
        if not request.user_content.strip():
            raise ValueError("user_content is required")
        if not request.idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        conversation = self.repository.get_conversation(request.conversation_id)
        async with self.locks.acquire(f"conversation:{conversation.id}"):
            return await self._run_locked(request)

    async def _run_locked(self, request: TurnRequest) -> TurnResult:
        started = time.monotonic()
        conversation = self.repository.get_conversation(request.conversation_id)
        agent = self.repository.get_agent_definition(conversation.agent_definition_id)
        cancellation = request.cancellation or NeverCancelled()
        with self.repository.transaction():
            run, existing_result = self.repository.start_run(
                conversation_id=request.conversation_id,
                idempotency_key=request.idempotency_key,
                request_hash=_request_hash(request, agent),
            )
            if existing_result:
                return existing_result
            self.repository.append_event(
                run.id,
                RunEventType.RUN_STARTED,
                {
                    "conversation_id": conversation.id,
                    "agent_definition_id": agent.id,
                    "memory_subject_id": conversation.memory_subject_id,
                    "executor": self.executor.name,
                    "retry_count": request.policy.retry_count,
                    "timeout_seconds": request.policy.timeout_seconds,
                },
            )
            user_message = self.repository.append_message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=request.user_content,
                run_id=run.id,
            )
            self.repository.append_event(
                run.id,
                RunEventType.MESSAGE_COMMITTED,
                {"message_id": user_message.id, "role": "user"},
            )

        attempts = 0
        last_context = None
        all_tool_executions = []
        last_raw_messages: tuple[dict[str, Any], ...] = ()
        last_error: Exception | None = None
        for attempt in range(1, request.policy.retry_count + 2):
            attempts = attempt
            if cancellation.is_set():
                return self._cancelled_result(
                    run_id=run.id,
                    attempts=attempts,
                    user_message=user_message,
                    context=last_context,
                    tool_executions=all_tool_executions,
                    started=started,
                )
            last_context = self.context_builder.build(
                conversation_id=conversation.id,
                current_user_message=user_message,
                budget=request.policy.context_budget,
                search_limit=request.policy.memory_search_limit,
                include_episodes=request.policy.include_episodes,
            )
            self.repository.append_event(
                run.id,
                RunEventType.CONTEXT_BUILT,
                {
                    "attempt": attempt,
                    "estimated_input_tokens": last_context.estimated_input_tokens,
                    "section_tokens": {
                        section.name: section.estimated_tokens
                        for section in last_context.sections
                    },
                    "omitted_message_count": len(last_context.omitted_message_ids),
                    "retrieved_fact_ids": list(last_context.retrieved_fact_ids),
                    "retrieved_episode_ids": list(last_context.retrieved_episode_ids),
                },
            )
            session = TurnToolSession(
                subject_id=conversation.memory_subject_id,
                conversation_id=conversation.id,
                source_messages=(user_message,),
                memory_policy=self.memory_policy,
                memory_retriever=self.memory_retriever,
                search_limit=request.policy.memory_search_limit,
                include_episodes=request.policy.include_episodes,
            )
            executor_request = ExecutorRequest(
                run_id=run.id,
                model_key=agent.model_key,
                context=last_context,
                tools=curated_tools(agent.tool_names),
                tool_session=session,
                timeout_seconds=request.policy.timeout_seconds,
                max_output_tokens=request.policy.max_output_tokens,
                max_model_requests=request.policy.max_model_requests,
                cancellation=cancellation,
            )
            try:
                executor_result = await self._execute_with_controls(
                    executor_request,
                    timeout_seconds=request.policy.timeout_seconds,
                    cancellation=cancellation,
                )
                self._append_executor_events(run.id, executor_result.events, attempt)
                for proposal in session.pending_proposals:
                    self.repository.append_event(
                        run.id,
                        RunEventType.MEMORY_PROPOSED,
                        {
                            "attempt": attempt,
                            "operation": proposal.operation.value,
                            "key": proposal.key,
                            "fact_id": proposal.fact_id,
                            "target_fact_ids": list(proposal.target_fact_ids),
                            "evidence_quote": proposal.evidence_quote,
                        },
                    )
                async with self.locks.acquire(
                    f"subject:{conversation.memory_subject_id}"
                ):
                    with self.repository.transaction():
                        revisions = session.commit(run_id=run.id)
                        assistant_message = self.repository.append_message(
                            conversation_id=conversation.id,
                            role=MessageRole.ASSISTANT,
                            content=executor_result.assistant_text,
                            run_id=run.id,
                        )
                        for revision in revisions:
                            self.repository.append_event(
                                run.id,
                                RunEventType.MEMORY_COMMITTED,
                                {
                                    "attempt": attempt,
                                    "revision_id": revision.id,
                                    "fact_id": revision.fact_id,
                                    "operation": revision.operation.value,
                                    "fact_version": revision.fact_version,
                                    "source_message_ids": list(
                                        revision.source_message_ids
                                    ),
                                },
                            )
                        self.repository.append_event(
                            run.id,
                            RunEventType.MESSAGE_COMMITTED,
                            {
                                "attempt": attempt,
                                "message_id": assistant_message.id,
                                "role": "assistant",
                            },
                        )
                        completed_run = self.repository.finish_run(
                            run.id,
                            status=RunStatus.SUCCEEDED,
                            attempt_count=attempts,
                        )
                        self.repository.append_event(
                            run.id,
                            RunEventType.RUN_COMPLETED,
                            {
                                "attempt": attempt,
                                "attempt_count": attempts,
                                "model_request_count": (
                                    executor_result.model_request_count
                                ),
                                "memory_revision_count": len(revisions),
                            },
                        )
                        result = TurnResult(
                            run=completed_run,
                            user_message=user_message,
                            assistant_message=assistant_message,
                            memory_revisions=revisions,
                            context=last_context,
                            events=self.repository.list_events(run.id),
                            tool_executions=tuple(
                                (*all_tool_executions, *session.executions)
                            ),
                            reasoning=executor_result.reasoning,
                            raw_model_messages=executor_result.raw_messages,
                            usage=executor_result.usage,
                            elapsed_seconds=round(time.monotonic() - started, 6),
                        )
                        self.repository.save_result(result)
                return result
            except _CancellationRequested:
                all_tool_executions.extend(session.executions)
                return self._cancelled_result(
                    run_id=run.id,
                    attempts=attempts,
                    user_message=user_message,
                    context=last_context,
                    tool_executions=all_tool_executions,
                    started=started,
                )
            except ExecutorError as exc:
                last_error = exc
                last_raw_messages = exc.raw_messages
                self._append_executor_events(run.id, exc.events, attempt)
                all_tool_executions.extend(session.executions)
                if exc.retryable and attempt <= request.policy.retry_count:
                    self.repository.append_event(
                        run.id,
                        RunEventType.RETRY_SCHEDULED,
                        {
                            "completed_attempt": attempt,
                            "next_attempt": attempt + 1,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        },
                    )
                    continue
                break
            except TimeoutError as exc:
                last_error = exc
                all_tool_executions.extend(session.executions)
                if attempt <= request.policy.retry_count:
                    self.repository.append_event(
                        run.id,
                        RunEventType.RETRY_SCHEDULED,
                        {
                            "completed_attempt": attempt,
                            "next_attempt": attempt + 1,
                            "error_type": "TimeoutError",
                            "error": "whole runtime attempt timed out",
                        },
                    )
                    continue
                break
            except Exception as exc:
                last_error = exc
                all_tool_executions.extend(session.executions)
                break

        with self.repository.transaction():
            failed_run = self.repository.finish_run(
                run.id,
                status=RunStatus.FAILED,
                attempt_count=attempts,
                error=last_error,
            )
            self.repository.append_event(
                run.id,
                RunEventType.RUN_FAILED,
                {
                    "attempt": attempts,
                    "attempt_count": attempts,
                    "error_type": (
                        type(last_error).__name__ if last_error else "UnknownError"
                    ),
                    "error": str(last_error or "unknown runtime failure"),
                },
            )
            result = TurnResult(
                run=failed_run,
                user_message=user_message,
                assistant_message=None,
                memory_revisions=(),
                context=last_context,
                events=self.repository.list_events(run.id),
                tool_executions=tuple(all_tool_executions),
                reasoning=(),
                raw_model_messages=last_raw_messages,
                usage={},
                elapsed_seconds=round(time.monotonic() - started, 6),
            )
            self.repository.save_result(result)
        return result

    async def _execute_with_controls(
        self,
        request: ExecutorRequest,
        *,
        timeout_seconds: float,
        cancellation: CancellationSignal,
    ):
        execution_task = asyncio.create_task(self.executor.execute(request))
        cancellation_task = asyncio.create_task(self._wait_for_cancel(cancellation))
        try:
            done, _ = await asyncio.wait(
                {execution_task, cancellation_task},
                timeout=timeout_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if cancellation_task in done:
                execution_task.cancel()
                with suppress(asyncio.CancelledError):
                    await execution_task
                raise _CancellationRequested()
            if execution_task not in done:
                execution_task.cancel()
                with suppress(asyncio.CancelledError):
                    await execution_task
                raise TimeoutError("whole runtime attempt timed out")
            return await execution_task
        finally:
            cancellation_task.cancel()
            with suppress(asyncio.CancelledError):
                await cancellation_task

    @staticmethod
    async def _wait_for_cancel(cancellation: CancellationSignal) -> None:
        while not cancellation.is_set():
            await asyncio.sleep(0.01)

    def _append_executor_events(
        self,
        run_id: str,
        events: tuple[tuple[RunEventType, dict[str, Any]], ...],
        attempt: int,
    ) -> None:
        for event_type, payload in events:
            self.repository.append_event(
                run_id, event_type, {"attempt": attempt, **payload}
            )

    def _cancelled_result(
        self,
        *,
        run_id: str,
        attempts: int,
        user_message,
        context,
        tool_executions,
        started: float,
    ) -> TurnResult:
        with self.repository.transaction():
            run = self.repository.finish_run(
                run_id,
                status=RunStatus.CANCELLED,
                attempt_count=attempts,
            )
            self.repository.append_event(
                run_id,
                RunEventType.RUN_CANCELLED,
                {"attempt": attempts, "attempt_count": attempts},
            )
            result = TurnResult(
                run=run,
                user_message=user_message,
                assistant_message=None,
                memory_revisions=(),
                context=context,
                events=self.repository.list_events(run_id),
                tool_executions=tuple(tool_executions),
                reasoning=(),
                raw_model_messages=(),
                usage={},
                elapsed_seconds=round(time.monotonic() - started, 6),
            )
            self.repository.save_result(result)
        return result


def _request_hash(request: TurnRequest, agent) -> str:
    payload = {
        "conversation_id": request.conversation_id,
        "user_content": request.user_content,
        "agent_definition_id": agent.id,
        "agent_definition_version": agent.version,
        "model_key": agent.model_key,
        "tool_names": list(agent.tool_names),
        "policy": asdict(request.policy),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def event_payload(result: TurnResult) -> list[dict[str, Any]]:
    return [
        {
            **asdict(event),
            "type": event.type.value,
            "visibility": event.visibility.value,
            "occurred_at": event.occurred_at.isoformat(),
        }
        for event in result.events
    ]
