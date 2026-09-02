from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ade_api.platform.settings import AdeApiSettings

from .contracts import AcceptTurnRequest
from .context import context_budget_from_deployment, validate_current_user_message
from .database_boundary import (
    DEFAULT_WORKSPACE_ID,
    RuntimeDatabase,
    require_default_workspace,
)
from .deployments import definition_deployment, validate_definition_execution
from .errors import (
    ConversationBusy,
    IdempotencyConflict,
    RuntimeValidationError,
)
from .events import TERMINAL_RUN_STATUSES, append_run_event, event_response
from .persistence.conversations import ConversationRepository
from .persistence.definitions import DefinitionVersionRepository
from .persistence.leases import ConversationLeaseRepository
from .persistence.memory import MemoryRepository
from .persistence.runs import RunRepository
from .presenters import run_response, turn_accepted_response
from .release_policy import (
    ensure_agent_studio_release_ready,
    release_validation_kwargs,
)
from .router_transport import RouterTransport


class RunService:
    def __init__(
        self,
        *,
        database: RuntimeDatabase,
        settings: AdeApiSettings,
        router_transport: RouterTransport,
    ) -> None:
        self.database = database
        self.settings = settings
        self.router_transport = router_transport

    async def accept_turn(
        self, conversation_id: str, request: AcceptTurnRequest
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                conversations = ConversationRepository(connection)
                runs = RunRepository(connection)
                conversation = await conversations.get(conversation_id)
                require_default_workspace(conversation)
                if conversation.get("purpose") == "agent_studio":
                    ensure_agent_studio_release_ready(
                        self.settings.agent_runtime_v3_mode
                    )
                _reject_archived_conversation(conversation)
                subject = await MemoryRepository(connection).get_subject(
                    str(conversation["memory_subject_id"])
                )
                _reject_archived_subject(subject)
                definition = await DefinitionVersionRepository(connection).get(
                    str(conversation["agent_definition_version_id"])
                )
                prior = await runs.get_by_idempotency(
                    conversation_id, request.idempotency_key
                )
                if prior is not None:
                    _validate_idempotent_replay(
                        prior,
                        request=request,
                        conversation=conversation,
                        definition=definition,
                    )
                    return turn_accepted_response(prior, replayed=True)
            catalog = await self.router_transport.catalog(
                timeout_seconds=self.settings.model_discovery_timeout_seconds
            )
            validate_definition_execution(
                definition,
                catalog,
                mode=self.settings.agent_runtime_v3_mode,
                **release_validation_kwargs(self.settings.agent_runtime_v3_mode),
            )
            conversation_deployment = definition_deployment(definition, "conversation")
            try:
                validate_current_user_message(
                    system_prompt=str(definition["prompt_content"]),
                    persona=str(definition["persona_content"]),
                    content=request.content,
                    budget=context_budget_from_deployment(conversation_deployment),
                )
            except ValueError as exc:
                raise RuntimeValidationError(str(exc)) from exc
            async with self.database.engine.begin() as connection:
                conversations = ConversationRepository(connection)
                runs = RunRepository(connection)
                conversation = await conversations.get_for_update(conversation_id)
                require_default_workspace(conversation)
                _reject_archived_conversation(conversation)
                subject = await MemoryRepository(connection).lock_subject(
                    str(conversation["memory_subject_id"])
                )
                _reject_archived_subject(subject)
                definition = await DefinitionVersionRepository(connection).get(
                    str(conversation["agent_definition_version_id"])
                )
                request_hash = _turn_request_hash(request, conversation, definition)
                prior = await runs.get_by_idempotency(
                    conversation_id, request.idempotency_key
                )
                if prior is not None:
                    _validate_idempotent_replay(
                        prior,
                        request=request,
                        conversation=conversation,
                        definition=definition,
                    )
                    return turn_accepted_response(prior, replayed=True)
                if await runs.active_for_conversation(conversation_id) is not None:
                    raise ConversationBusy(
                        "conversation already has a pending or running turn"
                    )
                run_id = str(uuid4())
                run, replayed = await runs.accept(
                    {
                        "id": run_id,
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "conversation_id": conversation_id,
                        "idempotency_key": request.idempotency_key,
                        "request_hash": request_hash,
                        "status": "pending",
                        "qualification_state": definition["qualification_state"],
                        "timeout_seconds": request.timeout_seconds,
                        "retry_count": request.retry_count,
                        "accepted_conversation_version": conversation["version"],
                    }
                )
                if replayed:
                    return turn_accepted_response(run, replayed=True)
                user_message = await conversations.append_message(
                    {
                        "id": str(uuid4()),
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "conversation_id": conversation_id,
                        "role": "user",
                        "content": request.content,
                        "content_sha256": _sha256(request.content),
                        "run_id": run_id,
                    }
                )
                await ConversationLeaseRepository(connection).create_pending(
                    lease_id=str(uuid4()),
                    conversation_id=conversation_id,
                    run_id=run_id,
                    lease_token=str(uuid4()),
                    expires_at=datetime.now(UTC),
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
                    },
                )
                await append_run_event(
                    runs,
                    run_id=run_id,
                    event_type="message.committed",
                    payload={"message_id": str(user_message["id"]), "role": "user"},
                    causation_id=str(accepted["id"]),
                )
        return turn_accepted_response(run, replayed=False)

    async def get_run(self, run_id: str) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                row = await RunRepository(connection).get(run_id)
                require_default_workspace(row)
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
                require_default_workspace(conversation)
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
                require_default_workspace(run)
                total, rows = await repository.list_event_page(
                    run_id, limit=limit, after_sequence=after_sequence
                )
        return {
            "total": total,
            "items": [
                event_response(row) for row in rows if row["visibility"] == "operator"
            ],
        }

    async def cancel_run(self, run_id: str) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                runs = RunRepository(connection)
                leases = ConversationLeaseRepository(connection)
                current = await runs.get_for_update(run_id)
                require_default_workspace(current)
                if current["status"] in TERMINAL_RUN_STATUSES:
                    return run_response(current)
                current = await runs.request_cancellation(run_id)
                requested = await append_run_event(
                    runs,
                    run_id=run_id,
                    event_type="run.cancel_requested",
                    payload={"status_at_request": current["status"]},
                )
                if current["status"] == "pending":
                    current = await runs.finish(
                        run_id, status="cancelled", attempt_count=0
                    )
                    await leases.release_for_run(run_id)
                    await append_run_event(
                        runs,
                        run_id=run_id,
                        event_type="run.cancelled",
                        payload={"attempt_count": 0},
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
                    require_default_workspace(run)
                    events = await repository.list_events(run_id, cursor)
            for event in events:
                cursor = max(cursor, int(event["sequence"]))
                if event["visibility"] == "operator":
                    yield event_response(event)
            if run["status"] in TERMINAL_RUN_STATUSES and not events:
                return
            now = asyncio.get_running_loop().time()
            if now >= heartbeat_deadline:
                yield {"heartbeat": True}
                heartbeat_deadline = now + 10.0
            await asyncio.sleep(0.25)


def _turn_request_hash(
    request: AcceptTurnRequest,
    conversation: dict[str, Any],
    definition: dict[str, Any],
    *,
    conversation_version: int | None = None,
) -> str:
    payload = {
        "conversation_id": str(conversation["id"]),
        "conversation_version": (
            conversation["version"]
            if conversation_version is None
            else conversation_version
        ),
        "content": request.content,
        "definition_id": str(definition["id"]),
        "definition_version": definition["version"],
        "deployment_snapshot": definition["deployment_snapshot"],
        "tool_names": definition["tool_names"],
        "memory_policy_version": definition["memory_policy_version"],
        "timeout_seconds": request.timeout_seconds,
        "retry_count": request.retry_count,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_idempotent_replay(
    prior: dict[str, Any],
    *,
    request: AcceptTurnRequest,
    conversation: dict[str, Any],
    definition: dict[str, Any],
) -> None:
    request_hash = _turn_request_hash(
        request,
        conversation,
        definition,
        conversation_version=int(prior["accepted_conversation_version"]),
    )
    if prior["request_hash"] != request_hash:
        raise IdempotencyConflict("idempotency key is already bound to another turn")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _reject_archived_conversation(conversation: dict[str, Any]) -> None:
    if conversation.get("archived_at") is not None:
        raise RuntimeValidationError("archived conversations cannot accept new turns")


def _reject_archived_subject(subject: dict[str, Any]) -> None:
    require_default_workspace(subject)
    if subject.get("archived_at") is not None:
        raise RuntimeValidationError(
            "conversations for archived memory subjects cannot accept new turns"
        )
