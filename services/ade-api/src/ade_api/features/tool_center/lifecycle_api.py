from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ade_api.features.tool_center.contracts import ApiToolCenterItemResponse
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
    "/api/v2/tool-center/tools/{slug}/archive",
    response_model=ApiToolCenterItemResponse,
    tags=[TAG_TOOL_CENTER],
    summary="Archive managed custom tool",
)
async def archive_tool(
    slug: str,
    custom_tool_registry: CustomToolRegistryDependency,
    tool_service: LettaToolServiceDependency,
):
    ensure_ade_api_enabled()
    try:
        managed_tool = custom_tool_registry.get_tool(slug, include_source=True)
        if not managed_tool:
            raise HTTPException(status_code=404, detail="Managed custom tool not found")
        if bool(managed_tool.get("archived", False)):
            raise HTTPException(status_code=400, detail="Tool is already archived")

        tool_id = str(managed_tool.get("tool_id", "") or "")
        if not tool_id:
            raise HTTPException(
                status_code=400, detail="Managed custom tool is missing tool_id"
            )
        tool_service.delete_tool(tool_id=tool_id)
        archived_tool = custom_tool_registry.archive_tool(slug)
    except HTTPException:
        raise
    except (ToolRegistryError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return as_tool_center_item(
        managed_entry=archived_tool,
        remote_tool=None,
        include_source=True,
    )


@router.post(
    "/api/v2/tool-center/tools/{slug}/restore",
    response_model=ApiToolCenterItemResponse,
    tags=[TAG_TOOL_CENTER],
    summary="Restore archived managed custom tool",
)
async def restore_tool(
    slug: str,
    custom_tool_registry: CustomToolRegistryDependency,
    tool_service: LettaToolServiceDependency,
):
    ensure_ade_api_enabled()
    try:
        managed_tool = custom_tool_registry.get_tool(slug, include_source=True)
        if not managed_tool:
            raise HTTPException(status_code=404, detail="Managed custom tool not found")
        if not bool(managed_tool.get("archived", False)):
            raise HTTPException(status_code=400, detail="Tool is not archived")

        source_code = str(managed_tool.get("source_code", "") or "")
        if not source_code.strip():
            raise HTTPException(
                status_code=400, detail="Archived source_code is missing"
            )
        tags = managed_tool_tags(
            [
                str(tag)
                for tag in (managed_tool.get("tags", []) or [])
                if str(tag).strip()
            ]
        )
        remote_tool = tool_service.create_tool(
            source_code=source_code,
            description=str(managed_tool.get("description", "") or ""),
            tags=tags,
            source_type=str(managed_tool.get("source_type", "python") or "python"),
        )
        restored_tool = custom_tool_registry.restore_tool(
            slug=slug,
            tool_id=str(remote_tool.get("id", "") or ""),
            name=str(remote_tool.get("name", "") or slug),
            description=str(
                remote_tool.get("description", "")
                or managed_tool.get("description", "")
            ),
            tags=[
                str(tag)
                for tag in (remote_tool.get("tags", tags) or [])
                if str(tag).strip()
            ],
            source_type=str(
                remote_tool.get(
                    "source_type",
                    managed_tool.get("source_type", "python"),
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
        managed_entry=restored_tool,
        remote_tool=remote_tool,
        include_source=True,
    )


@router.delete(
    "/api/v2/tool-center/tools/{slug}/purge",
    tags=[TAG_TOOL_CENTER],
    summary="Purge archived managed custom tool",
)
async def purge_tool(
    slug: str,
    custom_tool_registry: CustomToolRegistryDependency,
):
    ensure_ade_api_enabled()
    try:
        custom_tool_registry.purge_tool(slug)
    except ToolRegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "slug": slug, "kind": "custom_tool"}
