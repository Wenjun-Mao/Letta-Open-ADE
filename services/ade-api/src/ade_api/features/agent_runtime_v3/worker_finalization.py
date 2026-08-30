from __future__ import annotations

import hashlib
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine

from .database_boundary import DEFAULT_WORKSPACE_ID
from .events import append_run_event
from .memory_commit import commit_memory_review
from .memory_policy import prepare_memory_review
from .persistence.base import OptimisticLockError
from .persistence.conversations import ConversationRepository
from .persistence.leases import ConversationLeaseRepository
from .persistence.memory import MemoryRepository
from .persistence.runs import RunRepository
from .provider_tracing import AttemptTrace
from .turn_execution import AttemptResult
from .worker_claims import ClaimedRun
from .worker_control import LeaseLost, RunCancelled, utc_now, worker_error_code
from .worker_events import append_attempt_trace, append_success_events


class RunFinalizer:
    """Commits one terminal run outcome and releases its conversation lease."""

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def commit_success(
        self, claim: ClaimedRun, attempt_id: str, result: AttemptResult
    ) -> None:
        run_id = str(claim.run["id"])
        conversation_id = str(claim.run["conversation_id"])
        async with self.engine.begin() as connection:
            runs = RunRepository(connection)
            conversations = ConversationRepository(connection)
            memory = MemoryRepository(connection)
            leases = ConversationLeaseRepository(connection)
            run = await runs.get_for_update(run_id)
            if run["status"] != "running" or run["cancellation_requested_at"]:
                raise RunCancelled("cancellation won before final commit")
            if not await leases.owns(claim.lease_token, run_id):
                raise LeaseLost("conversation lease was lost before final commit")
            conversation = await conversations.get(conversation_id)
            subject_id = str(conversation["memory_subject_id"])
            conversation, _ = await _lock_conversation_and_subject(
                conversations, memory, conversation_id, subject_id
            )
            if int(conversation["version"]) != int(
                run["accepted_conversation_version"]
            ):
                raise OptimisticLockError(
                    "conversation changed before the run could commit"
                )
            messages = await conversations.list_messages(conversation_id)
            current_user = _current_user_message(messages, run_id)
            prepared = prepare_memory_review(
                decision=result.reviewer.decision,
                subject_id=subject_id,
                current_user_message=current_user,
                active_facts=await memory.list_active_facts(subject_id),
                entities=await memory.list_entities(subject_id),
            )
            committed = await commit_memory_review(
                connection,
                workspace_id=DEFAULT_WORKSPACE_ID,
                subject_id=subject_id,
                run_id=run_id,
                review=prepared,
                operation_embeddings=result.operation_embeddings,
                embedding_fingerprint=result.embedding_fingerprint,
                embedding_dimensions=result.embedding_dimensions,
                retrieval_policy_version=result.retrieval_policy_version,
            )
            assistant = await conversations.append_message(
                {
                    "id": str(uuid4()),
                    "workspace_id": DEFAULT_WORKSPACE_ID,
                    "conversation_id": conversation_id,
                    "role": "assistant",
                    "content": result.assistant_text,
                    "content_sha256": _sha256(result.assistant_text),
                    "run_id": run_id,
                }
            )
            summary = None
            if result.compaction is not None:
                compaction = result.compaction
                summary = await conversations.create_compaction(
                    payload={
                        "id": str(uuid4()),
                        "conversation_id": conversation_id,
                        "version": compaction.plan.expected_summary_version + 1,
                        "through_sequence": compaction.plan.through_sequence,
                        "content": compaction.content,
                        "run_id": run_id,
                        "previous_summary_id": compaction.plan.previous_summary_id,
                        "model_key": compaction.model_key,
                        "model_fingerprint": compaction.model_fingerprint,
                        "provider_request_id": compaction.provider_request_id,
                        "content_sha256": compaction.content_sha256,
                        "prompt_sha256": compaction.prompt_sha256,
                        "input_sha256": compaction.input_sha256,
                        "policy_sha256": compaction.policy_sha256,
                    },
                    source_message_ids=compaction.plan.source_message_ids,
                    expected_summary_version=compaction.plan.expected_summary_version,
                    expected_previous_summary_id=compaction.plan.previous_summary_id,
                )
            await conversations.advance_version(
                conversation_id, int(run["accepted_conversation_version"])
            )
            await runs.finish_attempt(
                attempt_id,
                status="succeeded",
                provider_outcome={
                    "conversation_request_ids": result.executor.provider_request_ids,
                    "reviewer_request_ids": result.reviewer.provider_request_ids,
                    "compaction_request_id": (
                        result.compaction.provider_request_id
                        if result.compaction is not None
                        else None
                    ),
                },
                finished_at=utc_now(),
            )
            await runs.finish(
                run_id,
                status="succeeded",
                attempt_count=int(run["attempt_count"]),
            )
            await append_success_events(
                runs,
                run_id=run_id,
                attempt=int(run["attempt_count"]),
                result=result,
                committed=committed,
                assistant_message_id=str(assistant["id"]),
                summary=summary,
            )
            await leases.release(claim.lease_token)

    async def commit_cancellation(
        self,
        claim: ClaimedRun,
        attempt_id: str | None,
        *,
        causation_id: str | None = None,
        trace: AttemptTrace | None = None,
        trace_causation_id: str | None = None,
    ) -> None:
        async with self.engine.begin() as connection:
            runs = RunRepository(connection)
            leases = ConversationLeaseRepository(connection)
            run = await runs.get_for_update(str(claim.run["id"]))
            if run["status"] not in {"pending", "running"}:
                return
            if not await leases.owns(claim.lease_token, str(run["id"])):
                raise LeaseLost(
                    "conversation lease was lost before cancellation commit"
                )
            if run["status"] in {"pending", "running"}:
                if attempt_id:
                    causation_id = await _finish_open_attempt(
                        runs,
                        run=run,
                        attempt_id=attempt_id,
                        status="cancelled",
                        error_code="run_cancelled",
                        trace=trace,
                        trace_causation_id=trace_causation_id or causation_id,
                    )
                run = await runs.finish(
                    str(run["id"]),
                    status="cancelled",
                    attempt_count=int(run["attempt_count"]),
                )
                await append_run_event(
                    runs,
                    run_id=str(run["id"]),
                    event_type="run.cancelled",
                    payload={"attempt_count": int(run["attempt_count"])},
                    causation_id=causation_id,
                )
            await leases.release(claim.lease_token)

    async def commit_failure(
        self,
        claim: ClaimedRun,
        attempt_id: str | None,
        exc: Exception,
        *,
        causation_id: str | None = None,
        trace: AttemptTrace | None = None,
        trace_causation_id: str | None = None,
    ) -> None:
        async with self.engine.begin() as connection:
            runs = RunRepository(connection)
            leases = ConversationLeaseRepository(connection)
            run = await runs.get_for_update(str(claim.run["id"]))
            if run["status"] not in {"pending", "running"}:
                return
            if not await leases.owns(claim.lease_token, str(run["id"])):
                raise LeaseLost("conversation lease was lost before failure commit")
            if run["cancellation_requested_at"] is not None:
                if attempt_id:
                    causation_id = await _finish_open_attempt(
                        runs,
                        run=run,
                        attempt_id=attempt_id,
                        status="cancelled",
                        error_code="run_cancelled",
                        trace=trace,
                        trace_causation_id=trace_causation_id or causation_id,
                    )
                await runs.finish(
                    str(run["id"]),
                    status="cancelled",
                    attempt_count=int(run["attempt_count"]),
                )
                await append_run_event(
                    runs,
                    run_id=str(run["id"]),
                    event_type="run.cancelled",
                    payload={"attempt_count": int(run["attempt_count"])},
                    causation_id=causation_id,
                )
            elif run["status"] in {"pending", "running"}:
                error_code = worker_error_code(exc)
                if attempt_id:
                    causation_id = await _finish_open_attempt(
                        runs,
                        run=run,
                        attempt_id=attempt_id,
                        status="failed",
                        error_code=error_code,
                        trace=trace,
                        trace_causation_id=trace_causation_id or causation_id,
                    )
                await runs.finish(
                    str(run["id"]),
                    status="failed",
                    attempt_count=int(run["attempt_count"]),
                    error_code=error_code,
                    error_message=f"Agent Runtime v3 run failed ({error_code})",
                )
                await append_run_event(
                    runs,
                    run_id=str(run["id"]),
                    event_type="run.failed",
                    payload={
                        "attempt_count": int(run["attempt_count"]),
                        "error_code": error_code,
                    },
                    attempt=int(run["attempt_count"]) or None,
                    causation_id=causation_id,
                )
            await leases.release(claim.lease_token)


async def _finish_open_attempt(
    runs: RunRepository,
    *,
    run: dict[str, Any],
    attempt_id: str,
    status: str,
    error_code: str,
    trace: AttemptTrace | None,
    trace_causation_id: str | None,
) -> str | None:
    await runs.finish_attempt(
        attempt_id,
        status=status,
        provider_outcome={"error_code": error_code},
        finished_at=utc_now(),
    )
    if trace is None:
        return trace_causation_id
    return await append_attempt_trace(
        runs,
        run_id=str(run["id"]),
        attempt=int(run["attempt_count"]),
        trace=trace,
        causation_id=trace_causation_id,
    )


async def _lock_conversation_and_subject(
    conversations: ConversationRepository,
    memory: MemoryRepository,
    conversation_id: str,
    subject_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if conversation_id <= subject_id:
        conversation = await conversations.get_for_update(conversation_id)
        subject = await memory.lock_subject(subject_id)
    else:
        subject = await memory.lock_subject(subject_id)
        conversation = await conversations.get_for_update(conversation_id)
    return conversation, subject


def _current_user_message(
    messages: list[dict[str, Any]], run_id: str
) -> dict[str, Any]:
    matches = [
        message
        for message in messages
        if message["role"] == "user" and str(message.get("run_id")) == run_id
    ]
    if len(matches) != 1:
        raise RuntimeError("run has no unique immutable user message")
    return matches[0]


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
