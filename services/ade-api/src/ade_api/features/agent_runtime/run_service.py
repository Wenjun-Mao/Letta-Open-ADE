from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from ade_api.platform.settings import AdeApiSettings

from .contracts import AcceptTurnRequest, RetryRunRequest
from .context import context_budget_from_deployment
from .database_boundary import RuntimeDatabase
from .deployments import definition_deployment, validate_definition_execution
from .errors import (
    ConversationBusy,
    IdempotencyConflict,
    RuntimeNotReady,
    RuntimeValidationError,
)
from .events import TERMINAL_RUN_STATUSES, append_run_event, event_response
from .hindsight_context import validate_input
from .persistence.conversations import ConversationRepository
from .persistence.definitions import DefinitionVersionRepository
from .persistence.leases import ConversationLeaseRepository
from .persistence.memory import MemoryRepository
from .persistence.run_lifecycle import lock_run
from .persistence.runs import RunRepository
from .presenters import run_response, turn_accepted_response
from .release_policy import release_validation_kwargs
from .router_transport import RouterTransport
from .run_retry import retry_saved_input
from .turn_activity import conversation_activity
from .turn_sources import enqueue_message, require_hindsight_definition
from .worker_health import RuntimeWorkerHealthServiceProtocol


class RunService:
    def __init__(
        self,
        *,
        database: RuntimeDatabase,
        settings: AdeApiSettings,
        router_transport: RouterTransport,
        worker_health: RuntimeWorkerHealthServiceProtocol,
    ) -> None:
        self.database = database
        self.settings = settings
        self.router_transport = router_transport
        self.worker_health = worker_health

    async def accept_turn(
        self, conversation_id: str, request: AcceptTurnRequest
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                conversation = await ConversationRepository(connection).get(
                    conversation_id
                )
                self.database.require_workspace(conversation)
                _reject_archived_conversation(conversation)
                subject = await MemoryRepository(connection).get_subject(
                    str(conversation["memory_subject_id"])
                )
                self.database.require_workspace(subject)
                _reject_archived_subject(subject)
                definition = await DefinitionVersionRepository(connection).get(
                    str(conversation["agent_definition_version_id"])
                )
                require_hindsight_definition(definition)
                prior = await RunRepository(connection).get_by_idempotency(
                    conversation_id, request.idempotency_key
                )
                if prior is not None:
                    _validate_idempotent_replay(
                        prior,
                        request=request,
                        conversation=conversation,
                        definition=definition,
                        runtime_mode=self.settings.agent_runtime_mode,
                    )
                    return turn_accepted_response(prior, replayed=True)
            catalog = await self.router_transport.catalog(
                timeout_seconds=self.settings.model_discovery_timeout_seconds
            )
            validate_definition_execution(
                definition,
                catalog,
                mode=self.settings.agent_runtime_mode,
                **release_validation_kwargs(self.settings.agent_runtime_mode),
            )
            validate_input(
                definition,
                request.content,
                context_budget_from_deployment(
                    definition_deployment(definition, "conversation")
                ),
            )
            await _ensure_worker_ready(self.worker_health)
            async with self.database.engine.begin() as connection:
                conversations, runs = (
                    ConversationRepository(connection),
                    RunRepository(connection),
                )
                conversation = await conversations.get_for_update(conversation_id)
                self.database.require_workspace(conversation)
                _reject_archived_conversation(conversation)
                subject = await MemoryRepository(connection).lock_subject(
                    str(conversation["memory_subject_id"])
                )
                _reject_archived_subject(subject)
                definition = await DefinitionVersionRepository(connection).get(
                    str(conversation["agent_definition_version_id"])
                )
                require_hindsight_definition(definition)
                prior = await runs.get_by_idempotency(
                    conversation_id, request.idempotency_key
                )
                if prior is not None:
                    _validate_idempotent_replay(
                        prior,
                        request=request,
                        conversation=conversation,
                        definition=definition,
                        runtime_mode=self.settings.agent_runtime_mode,
                    )
                    return turn_accepted_response(prior, replayed=True)
                if await runs.active_for_conversation(conversation_id) is not None:
                    raise ConversationBusy(
                        "Resolve the pending, running or paused reply before another turn"
                    )
                run_id = str(uuid4())
                run, replayed = await runs.accept(
                    {
                        "id": run_id,
                        "workspace_id": self.database.workspace_id,
                        "conversation_id": conversation_id,
                        "idempotency_key": request.idempotency_key,
                        "request_hash": _turn_request_hash(
                            request, conversation, definition
                        ),
                        "status": "pending",
                        "qualification_state": definition["qualification_state"],
                        "accepted_runtime_mode": self.settings.agent_runtime_mode,
                        "timeout_seconds": request.timeout_seconds,
                        "retry_count": request.retry_count,
                        "accepted_conversation_version": conversation["version"],
                        "accepted_memory_generation": None,
                    }
                )
                if replayed:
                    return turn_accepted_response(run, replayed=True)
                message = await conversations.append_message(
                    {
                        "id": str(uuid4()),
                        "workspace_id": self.database.workspace_id,
                        "conversation_id": conversation_id,
                        "role": "user",
                        "content": request.content,
                        "content_sha256": _sha256(request.content),
                        "run_id": run_id,
                    }
                )
                delivery = await enqueue_message(
                    connection,
                    message=message,
                    conversation=conversation,
                    definition=definition,
                )
                await ConversationLeaseRepository(connection).create_pending(
                    lease_id=str(uuid4()),
                    conversation_id=conversation_id,
                    run_id=run_id,
                    lease_token=str(uuid4()),
                )
                accepted = await append_run_event(
                    runs,
                    run_id=run_id,
                    event_type="run.accepted",
                    payload={
                        "conversation_id": conversation_id,
                        "agent_definition_id": str(definition["id"]),
                        "memory_subject_id": str(conversation["memory_subject_id"]),
                        "timeout_seconds": request.timeout_seconds,
                        "retry_count": request.retry_count,
                        "qualification_state": definition["qualification_state"],
                        "accepted_runtime_mode": self.settings.agent_runtime_mode,
                    },
                )
                committed = await append_run_event(
                    runs,
                    run_id=run_id,
                    event_type="message.committed",
                    payload={"message_id": str(message["id"]), "role": "user"},
                    causation_id=str(accepted["id"]),
                )
                await append_run_event(
                    runs,
                    run_id=run_id,
                    event_type="memory.delivery.queued",
                    payload={
                        "operation_id": str(delivery["operation_id"]),
                        "message_id": str(message["id"]),
                    },
                    causation_id=str(committed["id"]),
                )
        return turn_accepted_response(run, replayed=False)

    async def retry_run(self, run_id: str, request: RetryRunRequest) -> dict:
        return await retry_saved_input(self.database, run_id, request)

    async def get_run(self, run_id: str) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                row = await RunRepository(connection).get(run_id)
                self.database.require_workspace(row)
        return run_response(row)

    async def list_runs(
        self, conversation_id: str, *, limit: int, offset: int
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                conversation = await ConversationRepository(connection).get(
                    conversation_id
                )
                self.database.require_workspace(conversation)
                total, rows = await RunRepository(connection).list_for_conversation(
                    conversation_id, limit=limit, offset=offset
                )
        return {"total": total, "items": [run_response(row) for row in rows]}

    async def list_events(
        self, run_id: str, *, limit: int, after_sequence: int
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                repository = RunRepository(connection)
                run = await repository.get(run_id)
                self.database.require_workspace(run)
                total, rows = await repository.list_event_page(
                    run_id, limit=limit, after_sequence=after_sequence
                )
        return {
            "total": total,
            "items": [
                event_response(row) for row in rows if row["visibility"] == "operator"
            ],
        }

    async def list_conversation_activity(self, conversation_id: str) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                conversation = await ConversationRepository(connection).get(
                    conversation_id
                )
                self.database.require_workspace(conversation)
                rows = await RunRepository(connection).conversation_activity_rows(
                    conversation_id
                )
        return {"items": conversation_activity(*rows)}

    async def cancel_run(self, run_id: str) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                runs, leases = (
                    RunRepository(connection),
                    ConversationLeaseRepository(connection),
                )
                _, current = await lock_run(connection, run_id)
                self.database.require_workspace(current)
                if current["status"] in TERMINAL_RUN_STATUSES:
                    return run_response(current)
                current = await runs.request_cancellation(run_id)
                requested = await append_run_event(
                    runs,
                    run_id=run_id,
                    event_type="run.cancel_requested",
                    payload={"status_at_request": current["status"]},
                )
                if current["status"] in {"pending", "paused"}:
                    count = int(current["attempt_count"])
                    current = await runs.finish(
                        run_id, status="cancelled", attempt_count=count
                    )
                    await leases.release_for_run(run_id)
                    await append_run_event(
                        runs,
                        run_id=run_id,
                        event_type="run.cancelled",
                        payload={"attempt_count": count},
                        causation_id=str(requested["id"]),
                    )
        return run_response(current)

    async def stream_events(
        self, run_id: str, after_sequence: int
    ) -> AsyncIterator[dict[str, Any]]:
        await self.database.ensure_ready()
        heartbeat_deadline = asyncio.get_running_loop().time() + 10.0
        cursor = after_sequence
        while True:
            async with self.database.translated_errors():
                async with self.database.engine.connect() as connection:
                    repository = RunRepository(connection)
                    run = await repository.get(run_id)
                    self.database.require_workspace(run)
                    events = await repository.list_events(run_id, cursor)
            for event in events:
                cursor = max(cursor, int(event["sequence"]))
                if event["visibility"] == "operator":
                    yield event_response(event)
            if run["status"] in TERMINAL_RUN_STATUSES | {"paused"} and not events:
                return
            now = asyncio.get_running_loop().time()
            if now >= heartbeat_deadline:
                yield {"heartbeat": True}
                heartbeat_deadline = now + 10.0
            await asyncio.sleep(0.25)


def _turn_request_hash(
    request: AcceptTurnRequest,
    conversation: dict,
    definition: dict,
    *,
    conversation_version: int | None = None,
) -> str:
    payload = {
        "conversation_id": str(conversation["id"]),
        "conversation_version": conversation["version"]
        if conversation_version is None
        else conversation_version,
        "content": request.content,
        "definition_id": str(definition["id"]),
        "definition_version": definition["version"],
        "deployment_snapshot": definition["deployment_snapshot"],
        "tool_names": definition["tool_names"],
        "memory_policy_version": definition["memory_policy_version"],
        "timeout_seconds": request.timeout_seconds,
        "retry_count": request.retry_count,
    }
    return hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def _validate_idempotent_replay(
    prior: dict,
    *,
    request: AcceptTurnRequest,
    conversation: dict,
    definition: dict,
    runtime_mode: str | None = None,
) -> None:
    if runtime_mode is not None and prior.get("accepted_runtime_mode") != runtime_mode:
        raise IdempotencyConflict("idempotency key is bound to another runtime mode")
    if prior["request_hash"] != _turn_request_hash(
        request,
        conversation,
        definition,
        conversation_version=int(prior["accepted_conversation_version"]),
    ):
        raise IdempotencyConflict("idempotency key is already bound to another turn")


async def _ensure_worker_ready(
    worker_health: RuntimeWorkerHealthServiceProtocol,
) -> None:
    health = await worker_health.get_health()
    if not bool(health.get("worker_ready")):
        raise RuntimeNotReady(
            f"A matching ADE worker is not ready ({health.get('failure_code') or 'worker_unavailable'})"
        )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _reject_archived_conversation(conversation: dict) -> None:
    if conversation.get("archived_at") is not None:
        raise RuntimeValidationError("Archived conversations cannot accept new turns")


def _reject_archived_subject(subject: dict) -> None:
    if subject.get("archived_at") is not None:
        raise RuntimeValidationError("Archived subjects cannot accept new turns")
