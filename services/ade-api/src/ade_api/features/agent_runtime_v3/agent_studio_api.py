"""Product lifecycle API for the ADE-native Agent Studio."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from ade_api.platform.auth import require_admin, require_operator, require_reader

from .api_boundary import call_runtime
from .contracts import (
    AgentDefinitionListResponse,
    AgentDefinitionResponse,
    AgentStudioOptionsResponse,
    AgentStudioResetRequest,
    AgentStudioResetResponse,
    AgentStudioSessionListResponse,
    AgentStudioSessionResponse,
    ConversationStateResponse,
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
    MemorySubjectListResponse,
    MemorySubjectResponse,
    SubjectMemoriesResponse,
    UpdateMemorySubjectRequest,
)
from .dependencies import AgentRuntimeV3ServiceDependency


router = APIRouter(prefix="/agent-studio")
PageLimit = Annotated[int, Query(ge=1, le=200)]
PageOffset = Annotated[int, Query(ge=0)]


@router.get(
    "/options",
    response_model=AgentStudioOptionsResponse,
    dependencies=[Depends(require_reader)],
    summary="List qualified native Agent Studio bundles",
)
async def get_options(service: AgentRuntimeV3ServiceDependency):
    return await call_runtime(service.get_agent_studio_options())


@router.get(
    "/sessions",
    response_model=AgentStudioSessionListResponse,
    dependencies=[Depends(require_reader)],
    summary="List persisted Agent Studio conversations",
)
async def list_sessions(
    service: AgentRuntimeV3ServiceDependency,
    include_archived: bool = False,
    limit: PageLimit = 100,
    offset: PageOffset = 0,
):
    return await call_runtime(
        service.list_agent_studio_sessions(
            include_archived=include_archived, limit=limit, offset=offset
        )
    )


@router.post(
    "/sessions",
    response_model=AgentStudioSessionResponse,
    status_code=201,
    dependencies=[Depends(require_operator)],
    summary="Create an atomic Agent Studio conversation",
)
async def create_session(
    request: CreateAgentStudioSessionRequest,
    response: Response,
    service: AgentRuntimeV3ServiceDependency,
):
    result = await call_runtime(service.create_agent_studio_session(request))
    if bool(result.get("idempotent_replay")):
        response.headers["Idempotent-Replay"] = "true"
    return result


@router.get(
    "/sessions/{conversation_id}",
    response_model=AgentStudioSessionResponse,
    dependencies=[Depends(require_reader)],
    summary="Get an Agent Studio conversation binding",
)
async def get_session(conversation_id: str, service: AgentRuntimeV3ServiceDependency):
    return await call_runtime(service.get_agent_studio_session(conversation_id))


@router.delete(
    "/sessions/{conversation_id}",
    response_model=AgentStudioSessionResponse,
    dependencies=[Depends(require_operator)],
    summary="Archive an Agent Studio conversation",
)
async def archive_session(
    conversation_id: str, service: AgentRuntimeV3ServiceDependency
):
    return await call_runtime(
        service.set_agent_studio_session_archived(conversation_id, archived=True)
    )


@router.post(
    "/sessions/{conversation_id}/restore",
    response_model=AgentStudioSessionResponse,
    dependencies=[Depends(require_operator)],
    summary="Restore an Agent Studio conversation",
)
async def restore_session(
    conversation_id: str, service: AgentRuntimeV3ServiceDependency
):
    return await call_runtime(
        service.set_agent_studio_session_archived(conversation_id, archived=False)
    )


@router.get(
    "/sessions/{conversation_id}/state",
    response_model=ConversationStateResponse,
    dependencies=[Depends(require_reader)],
    summary="Inspect paginated Agent Studio conversation state",
)
async def get_session_state(
    conversation_id: str,
    service: AgentRuntimeV3ServiceDependency,
    message_limit: PageLimit = 200,
    before_sequence: Annotated[int | None, Query(ge=1)] = None,
):
    return await call_runtime(
        service.get_agent_studio_conversation_state(
            conversation_id,
            message_limit=message_limit,
            before_sequence=before_sequence,
        )
    )


@router.get(
    "/definitions",
    response_model=AgentDefinitionListResponse,
    dependencies=[Depends(require_reader)],
    summary="List current Agent Studio definition versions",
)
async def list_definitions(
    service: AgentRuntimeV3ServiceDependency,
    include_archived: bool = False,
    limit: PageLimit = 100,
    offset: PageOffset = 0,
):
    return await call_runtime(
        service.list_agent_studio_definitions(
            include_archived=include_archived, limit=limit, offset=offset
        )
    )


@router.post(
    "/definitions",
    response_model=AgentDefinitionResponse,
    status_code=201,
    dependencies=[Depends(require_admin)],
    summary="Create the next immutable Agent Studio definition version",
)
async def create_definition(
    request: CreateAgentDefinitionRequest,
    service: AgentRuntimeV3ServiceDependency,
):
    return await call_runtime(service.create_agent_studio_definition(request))


@router.delete(
    "/definitions/{definition_id}",
    response_model=AgentDefinitionResponse,
    dependencies=[Depends(require_admin)],
    summary="Archive an Agent Studio definition",
)
async def archive_definition(
    definition_id: str, service: AgentRuntimeV3ServiceDependency
):
    return await call_runtime(
        service.set_agent_studio_definition_archived(definition_id, archived=True)
    )


@router.post(
    "/definitions/{definition_id}/restore",
    response_model=AgentDefinitionResponse,
    dependencies=[Depends(require_admin)],
    summary="Restore an Agent Studio definition",
)
async def restore_definition(
    definition_id: str, service: AgentRuntimeV3ServiceDependency
):
    return await call_runtime(
        service.set_agent_studio_definition_archived(definition_id, archived=False)
    )


@router.get(
    "/subjects",
    response_model=MemorySubjectListResponse,
    dependencies=[Depends(require_reader)],
    summary="List Agent Studio memory subjects",
)
async def list_subjects(
    service: AgentRuntimeV3ServiceDependency,
    include_archived: bool = False,
    limit: PageLimit = 100,
    offset: PageOffset = 0,
):
    return await call_runtime(
        service.list_agent_studio_subjects(
            include_archived=include_archived, limit=limit, offset=offset
        )
    )


@router.post(
    "/subjects",
    response_model=MemorySubjectResponse,
    status_code=201,
    dependencies=[Depends(require_admin)],
    summary="Create an Agent Studio memory subject",
)
async def create_subject(
    request: CreateMemorySubjectRequest,
    service: AgentRuntimeV3ServiceDependency,
):
    return await call_runtime(service.create_agent_studio_subject(request))


@router.patch(
    "/subjects/{subject_id}",
    response_model=MemorySubjectResponse,
    dependencies=[Depends(require_admin)],
    summary="Rename an Agent Studio memory subject",
)
async def update_subject(
    subject_id: str,
    request: UpdateMemorySubjectRequest,
    service: AgentRuntimeV3ServiceDependency,
):
    return await call_runtime(service.update_agent_studio_subject(subject_id, request))


@router.delete(
    "/subjects/{subject_id}",
    response_model=MemorySubjectResponse,
    dependencies=[Depends(require_admin)],
    summary="Archive an Agent Studio memory subject",
)
async def archive_subject(subject_id: str, service: AgentRuntimeV3ServiceDependency):
    return await call_runtime(
        service.set_agent_studio_subject_archived(subject_id, archived=True)
    )


@router.post(
    "/subjects/{subject_id}/restore",
    response_model=MemorySubjectResponse,
    dependencies=[Depends(require_admin)],
    summary="Restore an Agent Studio memory subject",
)
async def restore_subject(subject_id: str, service: AgentRuntimeV3ServiceDependency):
    return await call_runtime(
        service.set_agent_studio_subject_archived(subject_id, archived=False)
    )


@router.get(
    "/subjects/{subject_id}/memories",
    response_model=SubjectMemoriesResponse,
    dependencies=[Depends(require_reader)],
    summary="Inspect typed Agent Studio memory lineage",
)
async def get_subject_memories(
    subject_id: str, service: AgentRuntimeV3ServiceDependency
):
    return await call_runtime(service.get_agent_studio_subject_memories(subject_id))


@router.post(
    "/reset",
    response_model=AgentStudioResetResponse,
    dependencies=[Depends(require_admin)],
    summary="Reset only fresh-start Agent Studio state",
)
async def reset_agent_studio(
    request: AgentStudioResetRequest,
    response: Response,
    service: AgentRuntimeV3ServiceDependency,
):
    result = await call_runtime(service.reset_agent_studio(request))
    if bool(result.get("idempotent_replay")):
        response.headers["Idempotent-Replay"] = "true"
    return result
