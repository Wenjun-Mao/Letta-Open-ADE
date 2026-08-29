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
    BuiltContext,
    CancellationSignal,
    ExecutorAdapter,
    ExecutorRequest,
    MemoryReviewTrace,
    Message,
    MessageRole,
    RunEventType,
    RunStatus,
    TurnRequest,
    TurnResult,
)
from .memory import MemoryPolicy, MemoryRetriever
from .memory_review import (
    MemoryReviewCoordinator,
    MemoryReviewError,
    MemoryReviewRequest,
    MemoryReviewer,
    NoopMemoryReviewer,
)
from .repository import InMemoryStudyRepository
from .semantic_retrieval import EmbeddingRequestError
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
        memory_reviewer: MemoryReviewer | None = None,
        memory_retriever: MemoryRetriever | None = None,
    ) -> None:
        self.repository = repository
        self.executor = executor
        self.memory_reviewer = memory_reviewer or NoopMemoryReviewer()
        self.memory_policy = MemoryPolicy(repository)
        self.memory_review_coordinator = MemoryReviewCoordinator(repository)
        self.memory_retriever = memory_retriever or MemoryRetriever(repository)
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
                    "memory_reviewer": self.memory_reviewer.model_key,
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
        last_reasoning: tuple[str, ...] = ()
        last_usage: dict[str, int] = {}
        last_candidate_assistant_text: str | None = None
        last_error: Exception | None = None
        last_review_trace: MemoryReviewTrace | None = None
        for attempt in range(1, request.policy.retry_count + 2):
            attempts = attempt
            last_raw_messages = ()
            last_reasoning = ()
            last_usage = {}
            last_candidate_assistant_text = None
            last_review_trace = None
            attempt_deadline = time.monotonic() + request.policy.timeout_seconds
            if cancellation.is_set():
                return self._cancelled_result(
                    run_id=run.id,
                    attempts=attempts,
                    user_message=user_message,
                    context=last_context,
                    tool_executions=all_tool_executions,
                    started=started,
                )
            try:
                last_context = await self._build_context_with_controls(
                    conversation_id=conversation.id,
                    user_message=user_message,
                    request=request,
                    timeout_seconds=self._remaining(attempt_deadline),
                    cancellation=cancellation,
                )
            except _CancellationRequested:
                return self._cancelled_result(
                    run_id=run.id,
                    attempts=attempts,
                    user_message=user_message,
                    context=last_context,
                    tool_executions=all_tool_executions,
                    started=started,
                )
            except TimeoutError as exc:
                last_error = exc
                if attempt <= request.policy.retry_count:
                    self.repository.append_event(
                        run.id,
                        RunEventType.RETRY_SCHEDULED,
                        {
                            "completed_attempt": attempt,
                            "next_attempt": attempt + 1,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "stage": "context_retrieval",
                        },
                    )
                    continue
                break
            except EmbeddingRequestError as exc:
                last_error = exc
                if exc.retryable and attempt <= request.policy.retry_count:
                    self.repository.append_event(
                        run.id,
                        RunEventType.RETRY_SCHEDULED,
                        {
                            "completed_attempt": attempt,
                            "next_attempt": attempt + 1,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "stage": "context_retrieval",
                        },
                    )
                    continue
                break
            except Exception as exc:
                last_error = exc
                break
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
                    timeout_seconds=self._remaining(attempt_deadline),
                    cancellation=cancellation,
                )
                last_candidate_assistant_text = executor_result.assistant_text
                last_raw_messages = executor_result.raw_messages
                last_reasoning = executor_result.reasoning
                last_usage = executor_result.usage
                self._append_executor_events(run.id, executor_result.events, attempt)
                self.repository.append_event(
                    run.id,
                    RunEventType.MEMORY_REVIEW_REQUEST,
                    {
                        "attempt": attempt,
                        "reviewer_model_key": self.memory_reviewer.model_key,
                        "active_fact_count": len(
                            self.repository.list_subject_facts(
                                conversation.memory_subject_id,
                                active_only=True,
                            )
                        ),
                    },
                )
                review_request = MemoryReviewRequest(
                    current_user_message=user_message,
                    recent_user_messages=tuple(
                        message
                        for message in self.repository.list_messages(conversation.id)
                        if message.id != user_message.id
                        and message.role is MessageRole.USER
                    )[-8:],
                    active_facts=self.repository.list_subject_facts(
                        conversation.memory_subject_id,
                        active_only=True,
                    ),
                    entities=self.repository.list_subject_entities(
                        conversation.memory_subject_id
                    ),
                    timeout_seconds=self._remaining(attempt_deadline),
                )
                review_decision = await self._review_with_controls(
                    review_request,
                    timeout_seconds=self._remaining(attempt_deadline),
                    cancellation=cancellation,
                )
                last_review_trace = MemoryReviewTrace(
                    reviewer_model_key=review_decision.reviewer_model_key,
                    model_request_count=review_decision.model_request_count,
                    protocol_repaired=review_decision.protocol_repaired,
                    proposal_count=len(review_decision.proposals),
                    raw_responses=review_decision.raw_responses,
                    usage=review_decision.usage,
                )
                if cancellation.is_set():
                    raise _CancellationRequested()
                if review_decision.protocol_repaired:
                    self.repository.append_event(
                        run.id,
                        RunEventType.MEMORY_REVIEW_REPAIR,
                        {
                            "attempt": attempt,
                            "reviewer_model_key": review_decision.reviewer_model_key,
                            "model_request_count": (
                                review_decision.model_request_count
                            ),
                        },
                    )
                prepared_review = self.memory_review_coordinator.prepare(
                    subject_id=conversation.memory_subject_id,
                    current_user_message=user_message,
                    decision=review_decision,
                )
                self.repository.append_event(
                    run.id,
                    RunEventType.MEMORY_REVIEWED,
                    {
                        "attempt": attempt,
                        "reviewer_model_key": review_decision.reviewer_model_key,
                        "model_request_count": review_decision.model_request_count,
                        "proposal_count": len(prepared_review.proposals),
                        "new_entity_count": len(prepared_review.new_entities),
                    },
                )
                for proposal in prepared_review.proposals:
                    self.repository.append_event(
                        run.id,
                        RunEventType.MEMORY_PROPOSED,
                        {
                            "attempt": attempt,
                            "operation": proposal.operation.value,
                            "fact_type": proposal.fact_type,
                            "entity_id": proposal.entity_id,
                            "qualifier": proposal.qualifier,
                            "fact_id": proposal.fact_id,
                            "target_fact_ids": list(proposal.target_fact_ids),
                            "evidence_quote": proposal.evidence_quote,
                        },
                    )
                async with self.locks.acquire(
                    f"subject:{conversation.memory_subject_id}"
                ):
                    with self.repository.transaction():
                        if cancellation.is_set():
                            raise _CancellationRequested()
                        for entity in prepared_review.new_entities:
                            self.repository.add_memory_entity(entity)
                            self.repository.append_event(
                                run.id,
                                RunEventType.MEMORY_ENTITY_CREATED,
                                {
                                    "attempt": attempt,
                                    "entity_id": entity.id,
                                    "entity_kind": entity.kind.value,
                                },
                            )
                        revisions = self.memory_policy.apply_batch(
                            subject_id=conversation.memory_subject_id,
                            proposals=prepared_review.proposals,
                            source_messages=(user_message,),
                            run_id=run.id,
                        )
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
                            memory_review=last_review_trace,
                            candidate_assistant_text=executor_result.assistant_text,
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
            except MemoryReviewError as exc:
                last_error = exc
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
                            "stage": "memory_review",
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
                reasoning=last_reasoning,
                raw_model_messages=last_raw_messages,
                usage=last_usage,
                elapsed_seconds=round(time.monotonic() - started, 6),
                memory_review=last_review_trace,
                candidate_assistant_text=last_candidate_assistant_text,
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

    async def _build_context_with_controls(
        self,
        *,
        conversation_id: str,
        user_message: Message,
        request: TurnRequest,
        timeout_seconds: float,
        cancellation: CancellationSignal,
    ) -> BuiltContext:
        context_task = asyncio.create_task(
            asyncio.to_thread(
                self.context_builder.build,
                conversation_id=conversation_id,
                current_user_message=user_message,
                budget=request.policy.context_budget,
                search_limit=request.policy.memory_search_limit,
                include_episodes=request.policy.include_episodes,
            )
        )
        cancellation_task = asyncio.create_task(self._wait_for_cancel(cancellation))
        try:
            done, _ = await asyncio.wait(
                {context_task, cancellation_task},
                timeout=timeout_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if cancellation_task in done:
                context_task.cancel()
                with suppress(asyncio.CancelledError):
                    await context_task
                raise _CancellationRequested("Run cancelled during context build")
            if context_task not in done:
                context_task.cancel()
                with suppress(asyncio.CancelledError):
                    await context_task
                raise TimeoutError("Context construction timed out")
            return await context_task
        finally:
            cancellation_task.cancel()
            with suppress(asyncio.CancelledError):
                await cancellation_task

    async def _review_with_controls(
        self,
        request: MemoryReviewRequest,
        *,
        timeout_seconds: float,
        cancellation: CancellationSignal,
    ):
        review_task = asyncio.create_task(self.memory_reviewer.review(request))
        cancellation_task = asyncio.create_task(self._wait_for_cancel(cancellation))
        try:
            done, _ = await asyncio.wait(
                {review_task, cancellation_task},
                timeout=timeout_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if cancellation_task in done:
                review_task.cancel()
                with suppress(asyncio.CancelledError):
                    await review_task
                raise _CancellationRequested()
            if review_task not in done:
                review_task.cancel()
                with suppress(asyncio.CancelledError):
                    await review_task
                raise TimeoutError("whole runtime attempt timed out")
            return await review_task
        finally:
            cancellation_task.cancel()
            with suppress(asyncio.CancelledError):
                await cancellation_task

    @staticmethod
    def _remaining(deadline: float) -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("whole runtime attempt timed out")
        return remaining

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
