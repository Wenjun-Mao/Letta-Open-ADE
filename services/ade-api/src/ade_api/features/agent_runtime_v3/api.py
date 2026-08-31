from __future__ import annotations

import json
from collections.abc import Awaitable
from typing import TypeVar

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.responses import StreamingResponse

from ade_api.platform.auth import require_operator
from ade_api.platform.openapi_metadata import TAG_AGENT_RUNTIME_V3

from .contracts import (
    AcceptTurnRequest,
    AgentDefinitionResponse,
    CreateAgentDefinitionRequest,
    CreateConversationRequest,
    CreateMemorySubjectRequest,
    CreatePreviewSessionRequest,
    ConversationResponse,
    ConversationStateResponse,
    MemorySubjectResponse,
    PreviewSessionResponse,
    RunResponse,
    RuntimeWorkerHealthResponse,
    SubjectMemoriesResponse,
    TurnAcceptedResponse,
)
from .dependencies import (
    AgentRuntimeV3HealthServiceDependency,
    AgentRuntimeV3ServiceDependency,
)
from .errors import AgentRuntimeV3Error
from .router_transport import RouterRequestError


router = APIRouter(
    prefix="/api/v3",
    dependencies=[Depends(require_operator)],
    tags=[TAG_AGENT_RUNTIME_V3],
)
T = TypeVar("T")


async def _call(operation: Awaitable[T]) -> T:
    try:
        return await operation
    except AgentRuntimeV3Error as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except RouterRequestError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "model_router_unavailable",
                "message": "Model Router is not ready",
            },
        ) from exc


@router.get(
    "/worker-health",
    response_model=RuntimeWorkerHealthResponse,
    responses={
        503: {
            "model": RuntimeWorkerHealthResponse,
            "description": "Database or matching runtime worker is not ready",
        }
    },
    summary="Check v3 worker process readiness",
)
async def get_worker_health(
    response: Response,
    service: AgentRuntimeV3HealthServiceDependency,
):
    result = await _call(service.get_health())
    if not result["worker_ready"]:
        response.status_code = 503
    return result


@router.post(
    "/agent-definitions",
    response_model=AgentDefinitionResponse,
    status_code=201,
    summary="Create an immutable v3 agent definition",
)
async def create_agent_definition(
    request: CreateAgentDefinitionRequest,
    service: AgentRuntimeV3ServiceDependency,
):
    return await _call(service.create_agent_definition(request))


@router.get(
    "/agent-definitions/{definition_id}",
    response_model=AgentDefinitionResponse,
    summary="Get a v3 agent definition",
)
async def get_agent_definition(
    definition_id: str,
    service: AgentRuntimeV3ServiceDependency,
):
    return await _call(service.get_agent_definition(definition_id))


@router.post(
    "/preview-sessions",
    response_model=PreviewSessionResponse,
    status_code=201,
    summary="Create an atomic native-runtime preview session",
)
async def create_preview_session(
    request: CreatePreviewSessionRequest,
    response: Response,
    service: AgentRuntimeV3ServiceDependency,
):
    result = await _call(service.create_preview_session(request))
    if bool(result.get("idempotent_replay")):
        response.headers["Idempotent-Replay"] = "true"
    return result


@router.post(
    "/memory-subjects",
    response_model=MemorySubjectResponse,
    status_code=201,
    summary="Create a v3 memory subject",
)
async def create_memory_subject(
    request: CreateMemorySubjectRequest,
    service: AgentRuntimeV3ServiceDependency,
):
    return await _call(service.create_memory_subject(request))


@router.get(
    "/memory-subjects/{subject_id}",
    response_model=MemorySubjectResponse,
    summary="Get a v3 memory subject",
)
async def get_memory_subject(
    subject_id: str,
    service: AgentRuntimeV3ServiceDependency,
):
    return await _call(service.get_memory_subject(subject_id))


@router.get(
    "/memory-subjects/{subject_id}/memories",
    response_model=SubjectMemoriesResponse,
    summary="Inspect typed subject memories",
)
async def get_subject_memories(
    subject_id: str,
    service: AgentRuntimeV3ServiceDependency,
):
    return await _call(service.get_subject_memories(subject_id))


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=201,
    summary="Create a v3 conversation",
)
async def create_conversation(
    request: CreateConversationRequest,
    service: AgentRuntimeV3ServiceDependency,
):
    return await _call(service.create_conversation(request))


@router.get(
    "/conversations/{conversation_id}/state",
    response_model=ConversationStateResponse,
    summary="Get v3 conversation state",
)
async def get_conversation_state(
    conversation_id: str,
    service: AgentRuntimeV3ServiceDependency,
):
    return await _call(service.get_conversation_state(conversation_id))


@router.post(
    "/conversations/{conversation_id}/turns",
    response_model=TurnAcceptedResponse,
    status_code=202,
    summary="Accept an asynchronous v3 conversation turn",
)
async def accept_turn(
    conversation_id: str,
    request: AcceptTurnRequest,
    response: Response,
    service: AgentRuntimeV3ServiceDependency,
):
    result = await _call(service.accept_turn(conversation_id, request))
    if bool(result.get("idempotent_replay")):
        response.headers["Idempotent-Replay"] = "true"
    return result


@router.get(
    "/runs/{run_id}",
    response_model=RunResponse,
    summary="Get a v3 run",
)
async def get_run(run_id: str, service: AgentRuntimeV3ServiceDependency):
    return await _call(service.get_run(run_id))


@router.post(
    "/runs/{run_id}/cancel",
    response_model=RunResponse,
    summary="Cancel a v3 run",
)
async def cancel_run(run_id: str, service: AgentRuntimeV3ServiceDependency):
    return await _call(service.cancel_run(run_id))


@router.get(
    "/runs/{run_id}/events",
    response_class=StreamingResponse,
    summary="Stream normalized v3 run events",
)
async def stream_run_events(
    run_id: str,
    service: AgentRuntimeV3ServiceDependency,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
):
    try:
        after_sequence = max(0, int(last_event_id or 0))
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="Last-Event-ID must be an event sequence integer"
        ) from exc

    async def event_stream():
        try:
            async for event in service.stream_events(run_id, after_sequence):
                if event.get("heartbeat"):
                    yield ": heartbeat\n\n"
                    continue
                sequence = int(event["sequence"])
                event_type = str(event["type"])
                payload = json.dumps(event, ensure_ascii=False, default=str)
                yield f"id: {sequence}\nevent: {event_type}\ndata: {payload}\n\n"
        except AgentRuntimeV3Error as exc:
            payload = json.dumps({"code": exc.code, "message": str(exc)})
            yield f"event: error\ndata: {payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
