from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ade_api.features.tool_center.contracts import (
    ApiToolCenterItemResponse,
    ToolCenterCreateRequest,
    ToolCenterUpdateRequest,
)
from ade_api.features.tool_center.presenters import (
    as_tool_center_item,
    managed_tool_tags,
)
from ade_api.features.tool_center.registry import ToolRegistryError
from ade_api.platform.auth import require_admin
from ade_api.platform.dependencies import (
    CustomToolRegistryDependency,
    LettaToolServiceDependency,
)
from ade_api.platform.feature_flags import ensure_ade_api_enabled
from ade_api.platform.openapi_metadata import TAG_TOOL_CENTER

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post(
    "/api/v2/tool-center/tools",
    response_model=ApiToolCenterItemResponse,
    tags=[TAG_TOOL_CENTER],
    summary="Create managed custom tool",
)
async def create_tool(
    request: ToolCenterCreateRequest,
    custom_tool_registry: CustomToolRegistryDependency,
    tool_service: LettaToolServiceDependency,
):
    ensure_ade_api_enabled()
    if not request.source_code.strip():
        raise HTTPException(status_code=400, detail="source_code is required")

    tags = managed_tool_tags(request.tags)
    try:
        remote_tool = tool_service.create_tool(
            source_code=request.source_code,
            description=request.description,
            tags=tags,
            source_type=request.source_type,
            enable_parallel_execution=request.enable_parallel_execution,
            default_requires_approval=request.default_requires_approval,
            return_char_limit=request.return_char_limit,
            pip_requirements=request.pip_requirements,
            npm_requirements=request.npm_requirements,
        )
        managed_tool = custom_tool_registry.create_tool(
            slug=request.slug,
            tool_id=str(remote_tool.get("id", "") or ""),
            name=str(remote_tool.get("name", "") or request.slug),
            description=str(remote_tool.get("description", "") or request.description),
            source_code=request.source_code,
            tags=[
                str(tag)
                for tag in (remote_tool.get("tags", tags) or [])
                if str(tag).strip()
            ],
            source_type=str(
                remote_tool.get("source_type", request.source_type)
                or request.source_type
            ),
            tool_type=str(remote_tool.get("tool_type", "custom") or "custom"),
        )
    except (ToolRegistryError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return as_tool_center_item(
        managed_entry=managed_tool,
        remote_tool=remote_tool,
        include_source=True,
    )


@router.patch(
    "/api/v2/tool-center/tools/{slug}",
    response_model=ApiToolCenterItemResponse,
    tags=[TAG_TOOL_CENTER],
    summary="Update managed custom tool",
)
async def update_tool(
    slug: str,
    request: ToolCenterUpdateRequest,
    custom_tool_registry: CustomToolRegistryDependency,
    tool_service: LettaToolServiceDependency,
):
    ensure_ade_api_enabled()
    if all(
        value is None
        for value in (
            request.source_code,
            request.description,
            request.tags,
            request.source_type,
            request.enable_parallel_execution,
            request.default_requires_approval,
            request.return_char_limit,
            request.pip_requirements,
            request.npm_requirements,
        )
    ):
        raise HTTPException(
            status_code=400, detail="At least one updatable field is required"
        )

    try:
        managed_tool = custom_tool_registry.get_tool(slug, include_source=True)
        if not managed_tool:
            raise HTTPException(status_code=404, detail="Managed custom tool not found")
        if bool(managed_tool.get("archived", False)):
            raise HTTPException(
                status_code=400, detail="Archived tool must be restored before update"
            )

        tool_id = str(managed_tool.get("tool_id", "") or "")
        if not tool_id:
            raise HTTPException(
                status_code=400, detail="Managed custom tool is missing tool_id"
            )

        merged_tags = (
            managed_tool_tags(request.tags) if request.tags is not None else None
        )
        remote_tool = tool_service.update_tool(
            tool_id=tool_id,
            source_code=request.source_code,
            description=request.description,
            tags=merged_tags,
            source_type=request.source_type,
            enable_parallel_execution=request.enable_parallel_execution,
            default_requires_approval=request.default_requires_approval,
            return_char_limit=request.return_char_limit,
            pip_requirements=request.pip_requirements,
            npm_requirements=request.npm_requirements,
        )
        updated_managed_tool = custom_tool_registry.update_tool(
            slug=slug,
            tool_id=str(remote_tool.get("id", "") or tool_id),
            name=str(remote_tool.get("name", "") or managed_tool.get("name", "")),
            description=str(
                remote_tool.get("description", "")
                or request.description
                or managed_tool.get("description", "")
            ),
            source_code=request.source_code,
            tags=[
                str(tag)
                for tag in (
                    remote_tool.get(
                        "tags",
                        merged_tags or managed_tool.get("tags", []),
                    )
                    or []
                )
                if str(tag).strip()
            ],
            source_type=str(
                remote_tool.get(
                    "source_type",
                    request.source_type or managed_tool.get("source_type", "python"),
                )
                or "python"
            ),
            tool_type=str(
                remote_tool.get(
                    "tool_type",
                    managed_tool.get("tool_type", "custom"),
                )
                or "custom"
            ),
        )
    except HTTPException:
        raise
    except (ToolRegistryError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return as_tool_center_item(
        managed_entry=updated_managed_tool,
        remote_tool=remote_tool,
        include_source=True,
    )
