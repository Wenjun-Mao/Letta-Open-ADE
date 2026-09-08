from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from ade_api.platform.auth import require_operator, require_reader
from ade_api.platform.openapi_metadata import TAG_AGENT_RUNTIME

from .contracts import (
    AcceptTurnRequest,
    CreateEvaluationSessionRequest,
    EvaluationSessionPurgeResponse,
    EvaluationSessionResponse,
    EvaluationSessionStateResponse,
    RunEventListResponse,
    RunListResponse,
    RunResponse,
    RuntimeWorkerHealthResponse,
    TurnAcceptedResponse,
)
from .agent_studio_api import router as agent_studio_router
from .api_boundary import call_runtime
from .dependencies import (
    AgentRuntimeHealthServiceDependency,
    AgentRuntimeServiceDependency,
)
from .errors import AgentRuntimeError


router = APIRouter(
    prefix="/api/v3",
    tags=[TAG_AGENT_RUNTIME],
)
router.include_router(agent_studio_router)


@router.get(
    "/worker-health",
    response_model=RuntimeWorkerHealthResponse,
    responses={
        503: {
            "model": RuntimeWorkerHealthResponse,
            "description": "Database or matching runtime worker is not ready",
        }
    },
    dependencies=[Depends(require_reader)],
    summary="Check agent runtime worker readiness",
)
async def get_worker_health(
    response: Response,
    service: AgentRuntimeHealthServiceDependency,
):
    result = await call_runtime(service.get_health())
    if not result["worker_ready"]:
        response.status_code = 503
    return result


@router.post(
    "/evaluation-sessions",
    response_model=EvaluationSessionResponse,
    status_code=201,
    dependencies=[Depends(require_operator)],
    summary="Atomically provision an isolated evaluation session",
)
async def create_evaluation_session(
    request: CreateEvaluationSessionRequest,
    response: Response,
    service: AgentRuntimeServiceDependency,
):
    result = await call_runtime(service.create_evaluation_session(request))
    if bool(result.get("idempotent_replay")):
        response.headers["Idempotent-Replay"] = "true"
    return result


@router.get(
    "/evaluation-sessions/{conversation_id}/state",
    response_model=EvaluationSessionStateResponse,
    dependencies=[Depends(require_reader)],
    summary="Inspect evaluation conversation, typed memories, and latest run",
)
async def get_evaluation_session_state(
    conversation_id: str,
    service: AgentRuntimeServiceDependency,
    message_limit: Annotated[int, Query(ge=1, le=200)] = 200,
    before_sequence: Annotated[int | None, Query(ge=1)] = None,
):
    return await call_runtime(
        service.get_evaluation_session_state(
            conversation_id,
            message_limit=message_limit,
            before_sequence=before_sequence,
        )
    )


@router.delete(
    "/evaluation-sessions/{conversation_id}",
    response_model=EvaluationSessionPurgeResponse,
    dependencies=[Depends(require_operator)],
    summary="Purge an inactive evaluation session",
)
async def purge_evaluation_session(
    conversation_id: str,
    service: AgentRuntimeServiceDependency,
):
    return await call_runtime(service.purge_evaluation_session(conversation_id))


@router.post(
    "/conversations/{conversation_id}/turns",
    response_model=TurnAcceptedResponse,
    status_code=202,
    dependencies=[Depends(require_operator)],
    summary="Accept an asynchronous conversation turn",
)
async def accept_turn(
    conversation_id: str,
    request: AcceptTurnRequest,
    response: Response,
    service: AgentRuntimeServiceDependency,
):
    result = await call_runtime(service.accept_turn(conversation_id, request))
    if bool(result.get("idempotent_replay")):
        response.headers["Idempotent-Replay"] = "true"
    return result


@router.get(
    "/runs/{run_id}",
    response_model=RunResponse,
    dependencies=[Depends(require_reader)],
    summary="Get an agent runtime run",
)
async def get_run(run_id: str, service: AgentRuntimeServiceDependency):
    return await call_runtime(service.get_run(run_id))


@router.get(
    "/conversations/{conversation_id}/runs",
    response_model=RunListResponse,
    dependencies=[Depends(require_reader)],
    summary="List agent runtime runs for one conversation",
)
async def list_runs(
    conversation_id: str,
    service: AgentRuntimeServiceDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await call_runtime(
        service.list_runs(conversation_id, limit=limit, offset=offset)
    )


@router.post(
    "/runs/{run_id}/cancel",
    response_model=RunResponse,
    dependencies=[Depends(require_operator)],
    summary="Cancel an agent runtime run",
)
async def cancel_run(run_id: str, service: AgentRuntimeServiceDependency):
    return await call_runtime(service.cancel_run(run_id))


@router.get(
    "/runs/{run_id}/event-log",
    response_model=RunEventListResponse,
    dependencies=[Depends(require_reader)],
    summary="Read normalized agent runtime events as JSON",
)
async def list_run_events(
    run_id: str,
    service: AgentRuntimeServiceDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    after_sequence: Annotated[int, Query(ge=0)] = 0,
):
    return await call_runtime(
        service.list_run_events(run_id, limit=limit, after_sequence=after_sequence)
    )


@router.get(
    "/runs/{run_id}/events",
    response_class=StreamingResponse,
    dependencies=[Depends(require_reader)],
    summary="Stream normalized agent runtime events",
)
async def stream_run_events(
    run_id: str,
    service: AgentRuntimeServiceDependency,
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
        except AgentRuntimeError as exc:
            payload = json.dumps({"code": exc.code, "message": str(exc)})
            yield f"event: error\ndata: {payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
