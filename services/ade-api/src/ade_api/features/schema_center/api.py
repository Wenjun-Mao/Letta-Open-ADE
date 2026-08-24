from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ade_api.platform.auth import require_admin
from ade_api.platform.dependencies import LabelSchemaRegistryDependency
from ade_api.platform.feature_flags import ensure_ade_api_enabled
from ade_api.features.schema_center.contracts import (
    ApiLabelSchemaListResponse,
    ApiLabelSchemaRecordResponse,
    LabelSchemaPatchRequest,
    LabelSchemaWriteRequest,
)
from ade_api.platform.openapi_metadata import TAG_SCHEMA_CENTER
from ade_api.features.schema_center.presenters import as_label_schema_record
from ade_api.features.schema_center.registry import LabelSchemaRegistryError

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/api/v2/schema-center/label-schemas",
    response_model=ApiLabelSchemaListResponse,
    tags=[TAG_SCHEMA_CENTER],
    summary="List Label Lab JSON schemas",
)
async def api_schema_center_list_label_schemas(
    registry: LabelSchemaRegistryDependency,
    include_archived: bool = False,
):
    ensure_ade_api_enabled()
    records = registry.list_schemas(include_archived=include_archived)
    items = [as_label_schema_record(record) for record in records]
    return {
        "total": len(items),
        "include_archived": include_archived,
        "items": items,
    }


@router.get(
    "/api/v2/schema-center/label-schemas/{key}",
    response_model=ApiLabelSchemaRecordResponse,
    tags=[TAG_SCHEMA_CENTER],
    summary="Get Label Lab JSON schema",
)
async def api_schema_center_get_label_schema(
    key: str,
    registry: LabelSchemaRegistryDependency,
    archived: bool = False,
):
    ensure_ade_api_enabled()
    try:
        record = registry.get_schema(key, archived=archived)
    except LabelSchemaRegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Label schema not found")
    return as_label_schema_record(record)


@router.post(
    "/api/v2/schema-center/label-schemas",
    response_model=ApiLabelSchemaRecordResponse,
    tags=[TAG_SCHEMA_CENTER],
    summary="Create Label Lab JSON schema",
)
async def api_schema_center_create_label_schema(
    request: LabelSchemaWriteRequest,
    registry: LabelSchemaRegistryDependency,
):
    ensure_ade_api_enabled()
    try:
        record = registry.create_schema(
            key=request.key,
            schema=request.schema_,
            label=request.label,
            description=request.description,
        )
    except LabelSchemaRegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return as_label_schema_record(record)


@router.patch(
    "/api/v2/schema-center/label-schemas/{key}",
    response_model=ApiLabelSchemaRecordResponse,
    tags=[TAG_SCHEMA_CENTER],
    summary="Update Label Lab JSON schema",
)
async def api_schema_center_update_label_schema(
    key: str,
    request: LabelSchemaPatchRequest,
    registry: LabelSchemaRegistryDependency,
):
    ensure_ade_api_enabled()
    if (
        request.label is None
        and request.description is None
        and request.schema_ is None
    ):
        raise HTTPException(
            status_code=400, detail="At least one field must be provided"
        )
    try:
        record = registry.update_schema(
            key=key,
            schema=request.schema_,
            label=request.label,
            description=request.description,
        )
    except LabelSchemaRegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return as_label_schema_record(record)


@router.post(
    "/api/v2/schema-center/label-schemas/{key}/archive",
    response_model=ApiLabelSchemaRecordResponse,
    tags=[TAG_SCHEMA_CENTER],
    summary="Archive Label Lab JSON schema",
)
async def api_schema_center_archive_label_schema(
    key: str,
    registry: LabelSchemaRegistryDependency,
):
    ensure_ade_api_enabled()
    try:
        record = registry.archive_schema(key)
    except LabelSchemaRegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return as_label_schema_record(record)


@router.post(
    "/api/v2/schema-center/label-schemas/{key}/restore",
    response_model=ApiLabelSchemaRecordResponse,
    tags=[TAG_SCHEMA_CENTER],
    summary="Restore archived Label Lab JSON schema",
)
async def api_schema_center_restore_label_schema(
    key: str,
    registry: LabelSchemaRegistryDependency,
):
    ensure_ade_api_enabled()
    try:
        record = registry.restore_schema(key)
    except LabelSchemaRegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return as_label_schema_record(record)


@router.delete(
    "/api/v2/schema-center/label-schemas/{key}/purge",
    tags=[TAG_SCHEMA_CENTER],
    summary="Purge archived Label Lab JSON schema",
)
async def api_schema_center_purge_label_schema(
    key: str,
    registry: LabelSchemaRegistryDependency,
):
    ensure_ade_api_enabled()
    try:
        registry.purge_schema(key)
    except LabelSchemaRegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "key": key, "kind": "label_schema"}
