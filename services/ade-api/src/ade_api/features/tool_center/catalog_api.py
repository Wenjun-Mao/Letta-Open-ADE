from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ade_api.platform.auth import require_admin
from ade_api.platform.dependencies import (
    CustomToolRegistryDependency,
    LettaToolServiceDependency,
)
from ade_api.platform.feature_flags import ensure_ade_api_enabled
from ade_api.features.tool_center.contracts import (
    ApiToolCenterItemResponse,
    ApiToolCenterListResponse,
)
from ade_api.platform.openapi_metadata import TAG_TOOL_CENTER
from ade_api.features.tool_center.presenters import as_tool_center_item
from ade_api.features.tool_center.registry import ToolRegistryError

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/api/v2/tool-center/tools",
    response_model=ApiToolCenterListResponse,
    tags=[TAG_TOOL_CENTER],
    summary="List Tool Center entries",
)
async def api_tool_center_list_tools(
    custom_tool_registry: CustomToolRegistryDependency,
    tool_service: LettaToolServiceDependency,
    include_archived: bool = False,
    include_builtin: bool = True,
    include_source: bool = False,
    search: str = "",
):
    ensure_ade_api_enabled()
    query = str(search or "").strip().lower()

    def matches_query(*values: str) -> bool:
        if not query:
            return True
        combined = "\n".join(str(value or "") for value in values).lower()
        return query in combined

    managed_records = custom_tool_registry.list_tools(
        include_archived=include_archived,
        include_source=include_source,
    )
    remote_tools = tool_service.list_available_tools(search=None, limit=500)
    remote_by_id = {
        str(tool.get("id", "") or ""): tool
        for tool in remote_tools
        if str(tool.get("id", "") or "").strip()
    }

    items: list[dict[str, Any]] = []
    managed_ids: set[str] = set()
    for managed in managed_records:
        tool_id = str(managed.get("tool_id", "") or "")
        if tool_id:
            managed_ids.add(tool_id)
        if not matches_query(
            str(managed.get("slug", "") or ""),
            str(managed.get("name", "") or ""),
            str(managed.get("description", "") or ""),
        ):
            continue

        remote_tool = (
            None if bool(managed.get("archived", False)) else remote_by_id.get(tool_id)
        )
        items.append(
            as_tool_center_item(
                managed_entry=managed,
                remote_tool=remote_tool,
                include_source=include_source,
            )
        )

    if include_builtin:
        for remote in remote_tools:
            tool_id = str(remote.get("id", "") or "")
            if not tool_id or tool_id in managed_ids:
                continue
            if not matches_query(
                str(remote.get("name", "") or ""),
                str(remote.get("description", "") or ""),
                str(remote.get("tool_type", "") or ""),
            ):
                continue

            items.append(
                as_tool_center_item(
                    managed_entry=None,
                    remote_tool=remote,
                    include_source=False,
                )
            )

    return {
        "total": len(items),
        "include_archived": include_archived,
        "include_builtin": include_builtin,
        "items": items,
    }


@router.get(
    "/api/v2/tool-center/tools/{slug}",
    response_model=ApiToolCenterItemResponse,
    tags=[TAG_TOOL_CENTER],
    summary="Get Tool Center managed custom tool",
)
async def api_tool_center_get_tool(
    slug: str,
    custom_tool_registry: CustomToolRegistryDependency,
    tool_service: LettaToolServiceDependency,
    include_source: bool = True,
):
    ensure_ade_api_enabled()

    try:
        managed = custom_tool_registry.get_tool(slug, include_source=include_source)
    except ToolRegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not managed:
        raise HTTPException(status_code=404, detail="Managed custom tool not found")

    remote_tool: dict[str, Any] | None = None
    if not bool(managed.get("archived", False)):
        tool_id = str(managed.get("tool_id", "") or "")
        if tool_id:
            try:
                remote_tool = tool_service.retrieve_tool(tool_id=tool_id)
            except Exception:
                remote_tool = None

    return as_tool_center_item(
        managed_entry=managed,
        remote_tool=remote_tool,
        include_source=include_source,
    )
