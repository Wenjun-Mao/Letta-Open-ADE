"""Opt-in development API for the evaluation-owned hands-on history trial."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from ade_api.platform.auth import require_operator, require_reader

from .api_boundary import call_runtime
from .contracts import (
    AgentDefinitionListResponse,
    AgentStudioOptionsResponse,
    AgentStudioSessionListResponse,
    AgentStudioSessionResponse,
    ConversationStateResponse,
    CreateAgentStudioSessionRequest,
    MemorySubjectListResponse,
    SubjectMemoriesResponse,
)
from .dependencies import AgentRuntimeServiceDependency


router = APIRouter(prefix="/api/v3/history-trial", tags=["Agent Runtime"])
PageLimit = Annotated[int, Query(ge=1, le=200)]
PageOffset = Annotated[int, Query(ge=0)]


@router.get(
    "/options",
    response_model=AgentStudioOptionsResponse,
    dependencies=[Depends(require_reader)],
)
async def options(service: AgentRuntimeServiceDependency):
    return await call_runtime(service.history_trial.options())


@router.get(
    "/sessions",
    response_model=AgentStudioSessionListResponse,
    dependencies=[Depends(require_reader)],
)
async def sessions(
    service: AgentRuntimeServiceDependency,
    include_archived: bool = False,
    limit: PageLimit = 100,
    offset: PageOffset = 0,
):
    return await call_runtime(
        service.history_trial.list(
            include_archived=include_archived, limit=limit, offset=offset
        )
    )


@router.post(
    "/sessions",
    response_model=AgentStudioSessionResponse,
    status_code=201,
    dependencies=[Depends(require_operator)],
)
async def create_session(
    request: CreateAgentStudioSessionRequest,
    response: Response,
    service: AgentRuntimeServiceDependency,
):
    result = await call_runtime(service.history_trial.create(request))
    if result.get("idempotent_replay"):
        response.headers["Idempotent-Replay"] = "true"
    return result


@router.get(
    "/sessions/{conversation_id}",
    response_model=AgentStudioSessionResponse,
    dependencies=[Depends(require_reader)],
)
async def get_session(conversation_id: str, service: AgentRuntimeServiceDependency):
    return await call_runtime(service.history_trial.get(conversation_id))


@router.delete(
    "/sessions/{conversation_id}",
    response_model=AgentStudioSessionResponse,
    dependencies=[Depends(require_operator)],
)
async def archive_session(conversation_id: str, service: AgentRuntimeServiceDependency):
    return await call_runtime(
        service.history_trial.set_archived(conversation_id, archived=True)
    )


@router.post(
    "/sessions/{conversation_id}/restore",
    response_model=AgentStudioSessionResponse,
    dependencies=[Depends(require_operator)],
)
async def restore_session(conversation_id: str, service: AgentRuntimeServiceDependency):
    return await call_runtime(
        service.history_trial.set_archived(conversation_id, archived=False)
    )


@router.get(
    "/sessions/{conversation_id}/state",
    response_model=ConversationStateResponse,
    dependencies=[Depends(require_reader)],
)
async def conversation_state(
    conversation_id: str,
    service: AgentRuntimeServiceDependency,
    message_limit: PageLimit = 200,
    before_sequence: Annotated[int | None, Query(ge=1)] = None,
):
    return await call_runtime(
        service.history_trial.conversation_state(
            conversation_id,
            message_limit=message_limit,
            before_sequence=before_sequence,
        )
    )


@router.get(
    "/definitions",
    response_model=AgentDefinitionListResponse,
    dependencies=[Depends(require_reader)],
)
async def definitions(
    service: AgentRuntimeServiceDependency,
    include_archived: bool = False,
    limit: PageLimit = 100,
    offset: PageOffset = 0,
):
    return await call_runtime(
        service.history_trial.list_definitions(
            include_archived=include_archived, limit=limit, offset=offset
        )
    )


@router.get(
    "/subjects",
    response_model=MemorySubjectListResponse,
    dependencies=[Depends(require_reader)],
)
async def subjects(
    service: AgentRuntimeServiceDependency,
    include_archived: bool = False,
    limit: PageLimit = 100,
    offset: PageOffset = 0,
):
    return await call_runtime(
        service.history_trial.list_subjects(
            include_archived=include_archived, limit=limit, offset=offset
        )
    )


@router.get(
    "/subjects/{subject_id}/memories",
    response_model=SubjectMemoriesResponse,
    dependencies=[Depends(require_reader)],
)
async def subject_memories(subject_id: str, service: AgentRuntimeServiceDependency):
    return await call_runtime(service.history_trial.subject_memories(subject_id))
