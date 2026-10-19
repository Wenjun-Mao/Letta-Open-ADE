"""Commit product outcomes and delivery intent without cross-service transactions."""

from __future__ import annotations

import hashlib
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine

from .events import append_run_event
from .persistence.base import OptimisticLockError
from .persistence.conversations import ConversationRepository
from .persistence.definitions import DefinitionVersionRepository
from .persistence.leases import ConversationLeaseRepository
from .persistence.memory import MemoryRepository
from .persistence.run_lifecycle import RunLifecycleRepository, lock_run
from .persistence.runs import RunRepository
from .provider_tracing import AttemptTrace
from .turn_recall import MemoryLookupError
from .turn_result import AttemptResult
from .turn_sources import enqueue_message
from .worker_claims import ClaimedRun
from .worker_control import LeaseLost, RunCancelled, utc_now, worker_error_payload
from .worker_events import append_attempt_trace, append_success_events


class RunFinalizer:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def commit_success(
        self,
        claim: ClaimedRun,
        attempt_id: str,
        result: AttemptResult,
        trace: AttemptTrace | None = None,
    ) -> None:
        run_id = str(claim.run["id"])
        async with self.engine.begin() as connection:
            conversation, run = await lock_run(connection, run_id)
            runs, conversations, leases = (
                RunRepository(connection),
                ConversationRepository(connection),
                ConversationLeaseRepository(connection),
            )
            if not await leases.owns(claim.lease_token, run_id):
                raise LeaseLost("Conversation lease was lost before final commit")
            if run["status"] != "running" or run["cancellation_requested_at"]:
                raise RunCancelled("Cancellation won before final commit")
            subject = await MemoryRepository(connection).lock_subject(
                str(conversation["memory_subject_id"])
            )
            if (
                conversation["archived_at"]
                or subject["archived_at"]
                or int(conversation["version"])
                != int(run["accepted_conversation_version"])
            ):
                raise OptimisticLockError("Conversation changed before reply commit")
            definition = await DefinitionVersionRepository(connection).get(
                str(conversation["agent_definition_version_id"])
            )
            assistant = await conversations.append_message(
                {
                    "id": str(uuid4()),
                    "workspace_id": str(run["workspace_id"]),
                    "conversation_id": str(conversation["id"]),
                    "role": "assistant",
                    "content": result.assistant_text,
                    "content_sha256": hashlib.sha256(
                        result.assistant_text.encode()
                    ).hexdigest(),
                    "run_id": run_id,
                }
            )
            delivery = await enqueue_message(
                connection,
                message=assistant,
                conversation=conversation,
                definition=definition,
            )
            summary = await _commit_compaction(
                conversations,
                result,
                conversation_id=str(conversation["id"]),
                run_id=run_id,
            )
            await conversations.advance_version(
                str(conversation["id"]), int(run["accepted_conversation_version"])
            )
            await runs.finish_attempt(
                attempt_id,
                status="succeeded",
                provider_outcome={
                    "conversation_request_ids": result.executor.provider_request_ids,
                    "memory_lookups": list(result.memory_lookups),
                    "compaction_request_id": result.compaction.provider_request_id
                    if result.compaction
                    else None,
                },
                finished_at=utc_now(),
            )
            await runs.finish(
                run_id, status="succeeded", attempt_count=int(run["attempt_count"])
            )
            await append_success_events(
                runs,
                run_id=run_id,
                attempt=int(run["attempt_count"]),
                result=result,
                assistant_message_id=str(assistant["id"]),
                delivery_operation_id=str(delivery["operation_id"]),
                summary=summary,
                trace=trace,
            )
            if not await leases.release_owned(claim.lease_token, run_id):
                raise LeaseLost("Conversation lease expired during reply finalization")
        if trace is not None:
            try:
                async with self.engine.begin() as connection:
                    await append_attempt_trace(
                        RunRepository(connection),
                        run_id=run_id,
                        attempt=trace.attempt,
                        trace=trace,
                        causation_id=None,
                    )
            except Exception:
                # Safe observational failure cannot rewrite a committed reply.
                pass

    async def commit_cancellation(
        self,
        claim: ClaimedRun,
        attempt_id: str | None,
        *,
        causation_id: str | None = None,
        trace: AttemptTrace | None = None,
        trace_causation_id: str | None = None,
    ) -> None:
        await self._finish_unsuccessful(
            claim,
            attempt_id,
            cancelled=True,
            causation_id=causation_id,
            trace=trace,
            trace_causation_id=trace_causation_id,
        )

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
        await self._finish_unsuccessful(
            claim,
            attempt_id,
            exc=exc,
            causation_id=causation_id,
            trace=trace,
            trace_causation_id=trace_causation_id,
        )

    async def _finish_unsuccessful(
        self,
        claim,
        attempt_id,
        *,
        exc=None,
        cancelled=False,
        causation_id=None,
        trace=None,
        trace_causation_id=None,
    ):
        run_id = str(claim.run["id"])
        async with self.engine.begin() as connection:
            _, run = await lock_run(connection, run_id)
            runs, leases = (
                RunRepository(connection),
                ConversationLeaseRepository(connection),
            )
            if run["status"] not in {"pending", "running"}:
                return
            if not await leases.owns(claim.lease_token, run_id):
                raise LeaseLost("Conversation lease was lost before outcome commit")
            cancelled = cancelled or run["cancellation_requested_at"] is not None
            paused = not cancelled and isinstance(exc, MemoryLookupError)
            status = "cancelled" if cancelled else "paused" if paused else "failed"
            payload = (
                {"error_code": "run_cancelled"}
                if cancelled
                else worker_error_payload(exc)
            )
            if attempt_id:
                await runs.finish_attempt(
                    attempt_id,
                    status="cancelled" if cancelled else "failed",
                    provider_outcome=payload,
                    finished_at=utc_now(),
                )
                if trace is not None:
                    causation_id = await append_attempt_trace(
                        runs,
                        run_id=run_id,
                        attempt=int(run["attempt_count"]),
                        trace=trace,
                        causation_id=trace_causation_id or causation_id,
                    )
            if paused:
                await RunLifecycleRepository(connection).pause(
                    run_id, detail_code=exc.detail_code
                )
            else:
                await runs.finish(
                    run_id,
                    status=status,
                    attempt_count=int(run["attempt_count"]),
                    error_code=None if cancelled else payload["error_code"],
                    error_message=None
                    if cancelled
                    else f"ADE reply failed ({payload['error_code']})",
                )
            await append_run_event(
                runs,
                run_id=run_id,
                event_type=f"run.{status}",
                payload={"attempt_count": int(run["attempt_count"]), **payload},
                attempt=int(run["attempt_count"]) or None,
                causation_id=causation_id,
            )
            # The paused run's unique active-conversation index remains its input
            # guard; releasing this lease lets the worker serve unrelated replies.
            if not await leases.release_owned(claim.lease_token, run_id):
                raise LeaseLost(
                    "Conversation lease expired during outcome finalization"
                )


async def _commit_compaction(conversations, result, *, conversation_id, run_id):
    compaction = result.compaction
    if compaction is None:
        return None
    return await conversations.create_compaction(
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
