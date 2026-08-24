from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ade_api.platform.auth import require_operator, require_reader
from ade_api.platform.dependencies import (
    AgentLifecycleRegistryDependency,
    CustomToolRegistryDependency,
    LettaAgentServiceDependency,
    LettaClientDependency,
    LettaToolServiceDependency,
)
from ade_api.platform.feature_flags import ensure_ade_api_enabled
from ade_api.features.agent_studio import ensure_agent_not_archived
from ade_api.features.tool_center.contracts import (
    ApiRuntimeToolListResponse,
    ApiToolTestInvokeResponse,
    ToolTestInvokeRequest,
)
from ade_api.platform.openapi_metadata import TAG_TOOL_CENTER

router = APIRouter(dependencies=[Depends(require_reader)])


@router.get(
    "/api/v2/tool-center/runtime-tools",
    response_model=ApiRuntimeToolListResponse,
    tags=[TAG_TOOL_CENTER],
    summary="List tools for Toolbench discovery",
)
async def api_list_runtime_tools(
    client: LettaClientDependency,
    custom_tool_registry: CustomToolRegistryDependency,
    tool_service: LettaToolServiceDependency,
    search: str = "",
    limit: int = 100,
    agent_id: str | None = None,
):
    ensure_ade_api_enabled()

    resolved_limit = max(1, min(limit, 500))
    try:
        tools = tool_service.list_available_tools(
            search=(search or "").strip() or None,
            limit=resolved_limit,
        )
        managed_entries = {
            str(entry.get("tool_id", "") or ""): entry
            for entry in custom_tool_registry.list_tools(
                include_archived=False, include_source=False
            )
            if str(entry.get("tool_id", "") or "").strip()
        }

        attached_ids: set[str] = set()
        if agent_id:
            attached_ids = {
                str(getattr(tool, "id", "") or "")
                for tool in list(client.agents.tools.list(agent_id=agent_id))
                if str(getattr(tool, "id", "") or "").strip()
            }

        for tool in tools:
            tool_id = str(tool.get("id", "") or "")
            managed_entry = managed_entries.get(tool_id)
            tool["attached_to_agent"] = bool(agent_id and tool_id in attached_ids)
            tool["managed"] = bool(managed_entry)
            tool["read_only"] = not bool(managed_entry)
            tool["archived"] = False
            tool["slug"] = (
                str(managed_entry.get("slug", "") or "") if managed_entry else None
            )

        return {
            "total": len(tools),
            "search": (search or "").strip(),
            "limit": resolved_limit,
            "agent_id": agent_id,
            "items": tools,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/v2/tool-center/invocations",
    response_model=ApiToolTestInvokeResponse,
    tags=[TAG_TOOL_CENTER],
    summary="Invoke a runtime message to validate tool-call behavior",
    dependencies=[Depends(require_operator)],
)
async def api_invoke_tool_probe(
    request: ToolTestInvokeRequest,
    agent_service: LettaAgentServiceDependency,
    lifecycle_registry: AgentLifecycleRegistryDependency,
):
    ensure_ade_api_enabled()

    agent_id = request.agent_id.strip()
    text = request.input.strip()
    expected_tool_name = (request.expected_tool_name or "").strip()

    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")
    if not text:
        raise HTTPException(status_code=400, detail="input is required")

    ensure_agent_not_archived(agent_id, lifecycle_registry)

    try:
        payload = agent_service.send_runtime_message(
            agent_id=agent_id,
            message=text,
            override_model=(request.override_model or "").strip() or None,
            override_system=(request.override_system or "").strip() or None,
            timeout_seconds=request.timeout_seconds,
            retry_count=request.retry_count,
        )
        result = payload.get("result", {}) if isinstance(payload, dict) else {}
        sequence = result.get("sequence", []) if isinstance(result, dict) else []
        tool_calls = [
            step
            for step in sequence
            if str(step.get("type", "") or "").strip().lower() == "tool_call"
        ]
        tool_returns = [
            step
            for step in sequence
            if str(step.get("type", "") or "").strip().lower() == "tool_return"
        ]

        expected_matched: bool | None = None
        if expected_tool_name:
            expected_lower = expected_tool_name.lower()
            expected_matched = any(
                str(step.get("name", "") or "").strip().lower() == expected_lower
                for step in tool_calls
            )

        return {
            "agent_id": agent_id,
            "input": text,
            "expected_tool_name": expected_tool_name or None,
            "expected_tool_matched": expected_matched,
            "tool_call_count": len(tool_calls),
            "tool_return_count": len(tool_returns),
            "result": result,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
