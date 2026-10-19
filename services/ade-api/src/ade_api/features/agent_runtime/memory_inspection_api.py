"""Public read-only Memory scopes shared by Studio and evaluation clients."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ade_api.platform.auth import require_operator, require_reader

from .api_boundary import call_runtime
from .dependencies import AgentRuntimeServiceDependency
from .inspection_contracts import (
    DeliveryListResponse,
    DeliveryResponse,
    DeliveryRetryRequest,
    RelationshipMemoriesResponse,
    SourceResponse,
    NativeOperationResponse,
    NativeOperationsResponse,
)


router = APIRouter(
    prefix="/memory/subjects/{subject_id}/characters/{character_root_id}"
)
PageLimit = Annotated[int, Query(ge=1, le=200)]
OperationPageLimit = Annotated[int, Query(ge=1, le=100)]
PageOffset = Annotated[int, Query(ge=0)]


@router.get(
    "/deliveries",
    response_model=DeliveryListResponse,
    summary="Inspect relationship delivery state independently of Memory availability",
    dependencies=[Depends(require_reader)],
)
async def list_deliveries(
    subject_id: UUID,
    character_root_id: UUID,
    service: AgentRuntimeServiceDependency,
    limit: PageLimit = 100,
    offset: PageOffset = 0,
):
    return await call_runtime(
        service.memory_inspection.deliveries(
            str(subject_id), str(character_root_id), limit=limit, offset=offset
        )
    )


@router.get(
    "/memories",
    response_model=RelationshipMemoriesResponse,
    summary="List learned memories for one person and character",
    dependencies=[Depends(require_reader)],
)
async def list_memories(
    subject_id: UUID,
    character_root_id: UUID,
    service: AgentRuntimeServiceDependency,
    limit: PageLimit = 100,
    offset: PageOffset = 0,
):
    return await call_runtime(
        service.memory_inspection.memories(
            str(subject_id), str(character_root_id), limit=limit, offset=offset
        )
    )


@router.get(
    "/sources/{document_id}",
    response_model=SourceResponse,
    summary="Inspect an original source within the selected relationship",
    dependencies=[Depends(require_reader)],
)
async def get_source(
    subject_id: UUID,
    character_root_id: UUID,
    document_id: str,
    service: AgentRuntimeServiceDependency,
):
    return await call_runtime(
        service.memory_inspection.source(
            str(subject_id), str(character_root_id), document_id
        )
    )


@router.post(
    "/deliveries/{operation_id}/retry",
    response_model=DeliveryResponse,
    summary="Retry an immutable delivery within the selected relationship",
    dependencies=[Depends(require_operator)],
)
async def retry_delivery(
    subject_id: UUID,
    character_root_id: UUID,
    operation_id: UUID,
    request: DeliveryRetryRequest,
    service: AgentRuntimeServiceDependency,
):
    return await call_runtime(
        service.memory_inspection.retry_delivery(
            str(subject_id), str(character_root_id), str(operation_id), request
        )
    )


@router.get(
    "/operations",
    response_model=NativeOperationsResponse,
    summary="List native processing and consolidation for one relationship",
    dependencies=[Depends(require_reader)],
)
async def list_operations(
    subject_id: UUID,
    character_root_id: UUID,
    service: AgentRuntimeServiceDependency,
    limit: OperationPageLimit = 100,
    offset: PageOffset = 0,
):
    return await call_runtime(
        service.memory_inspection.operations(
            str(subject_id), str(character_root_id), limit=limit, offset=offset
        )
    )


@router.get(
    "/operations/{operation_id}",
    response_model=NativeOperationResponse,
    summary="Inspect a native operation within the selected relationship",
    dependencies=[Depends(require_reader)],
)
async def get_operation(
    subject_id: UUID,
    character_root_id: UUID,
    operation_id: UUID,
    service: AgentRuntimeServiceDependency,
):
    return await call_runtime(
        service.memory_inspection.operation(
            str(subject_id), str(character_root_id), str(operation_id)
        )
    )
