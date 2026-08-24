from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ade_api.platform.auth import require_admin, require_operator
from ade_api.platform.dependencies import (
    AgentLifecycleRegistryDependency,
    LettaAgentServiceDependency,
)
from ade_api.platform.feature_flags import ensure_ade_api_enabled
from ade_api.features.prompt_center import append_prompt_persona_revision
from ade_api.features.agent_studio.access import ensure_agent_not_archived
from ade_api.features.agent_studio.contracts import (
    ApiMemoryBlockUpdateResponse,
    ApiModelUpdateResponse,
    ApiRuntimeMessageResponse,
    ApiSystemUpdateResponse,
    ApiToolAttachDetachResponse,
    AgentModelUpdateRequest,
    MemoryBlockUpdateRequest,
    RuntimeMessageRequest,
    SystemPromptUpdateRequest,
)
from ade_api.platform.openapi_metadata import TAG_AGENT_STUDIO

router = APIRouter(dependencies=[Depends(require_operator)])


@router.post(
    "/api/v2/agent-studio/agents/{agent_id}/runtime-messages",
    response_model=ApiRuntimeMessageResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Send runtime message with optional overrides",
)
async def api_send_runtime_message(
    agent_id: str,
    request: RuntimeMessageRequest,
    agent_service: LettaAgentServiceDependency,
    lifecycle_registry: AgentLifecycleRegistryDependency,
):
    ensure_ade_api_enabled()
    ensure_agent_not_archived(agent_id, lifecycle_registry)

    text = request.input.strip()
    if not text:
        raise HTTPException(status_code=400, detail="input is required")

    try:
        return agent_service.send_runtime_message(
            agent_id=agent_id,
            message=text,
            override_model=(request.override_model or "").strip() or None,
            override_system=(request.override_system or "").strip() or None,
            timeout_seconds=request.timeout_seconds,
            retry_count=request.retry_count,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch(
    "/api/v2/agent-studio/agents/{agent_id}/system-prompt",
    response_model=ApiSystemUpdateResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Update persisted system prompt",
    dependencies=[Depends(require_admin)],
)
async def api_update_system_prompt(
    agent_id: str,
    request: SystemPromptUpdateRequest,
    agent_service: LettaAgentServiceDependency,
    lifecycle_registry: AgentLifecycleRegistryDependency,
):
    ensure_ade_api_enabled()
    ensure_agent_not_archived(agent_id, lifecycle_registry)

    system_text = request.system.strip()
    if not system_text:
        raise HTTPException(status_code=400, detail="system is required")

    try:
        payload = agent_service.update_system_prompt(
            agent_id=agent_id, system_prompt=system_text
        )
        append_prompt_persona_revision(
            agent_id=agent_id,
            field="system",
            before=str(payload.get("system_before", "") or ""),
            after=str(payload.get("system_after", "") or ""),
            source="api/v2/agent-studio/agents/{agent_id}/system-prompt",
        )
        return payload
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch(
    "/api/v2/agent-studio/agents/{agent_id}/model",
    response_model=ApiModelUpdateResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Update persisted agent model",
    dependencies=[Depends(require_admin)],
)
async def api_update_agent_model(
    agent_id: str,
    request: AgentModelUpdateRequest,
    agent_service: LettaAgentServiceDependency,
    lifecycle_registry: AgentLifecycleRegistryDependency,
):
    ensure_ade_api_enabled()
    ensure_agent_not_archived(agent_id, lifecycle_registry)

    model_handle = request.model.strip()
    if not model_handle:
        raise HTTPException(status_code=400, detail="model is required")

    try:
        return agent_service.update_agent_model(
            agent_id=agent_id, model_handle=model_handle
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch(
    "/api/v2/agent-studio/agents/{agent_id}/memory/{block_label}",
    response_model=ApiMemoryBlockUpdateResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Update core-memory block value",
    dependencies=[Depends(require_admin)],
)
async def api_update_memory_block(
    agent_id: str,
    block_label: str,
    request: MemoryBlockUpdateRequest,
    agent_service: LettaAgentServiceDependency,
    lifecycle_registry: AgentLifecycleRegistryDependency,
):
    ensure_ade_api_enabled()
    ensure_agent_not_archived(agent_id, lifecycle_registry)

    label = block_label.strip()
    if not label:
        raise HTTPException(status_code=400, detail="block_label is required")

    try:
        payload = agent_service.update_core_memory_block(
            agent_id=agent_id,
            block_label=label,
            value=request.value,
        )
        if label in {"persona", "human"}:
            append_prompt_persona_revision(
                agent_id=agent_id,
                field=label,
                before=str(payload.get("value_before", "") or ""),
                after=str(payload.get("value_after", "") or ""),
                source=f"api/v2/agent-studio/agents/{{agent_id}}/memory/{label}",
            )
        return payload
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch(
    "/api/v2/agent-studio/agents/{agent_id}/tools/{tool_id}/attach",
    response_model=ApiToolAttachDetachResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Attach tool to agent",
    dependencies=[Depends(require_admin)],
)
async def api_attach_tool(
    agent_id: str,
    tool_id: str,
    agent_service: LettaAgentServiceDependency,
    lifecycle_registry: AgentLifecycleRegistryDependency,
):
    ensure_ade_api_enabled()
    ensure_agent_not_archived(agent_id, lifecycle_registry)

    resolved_tool_id = tool_id.strip()
    if not resolved_tool_id:
        raise HTTPException(status_code=400, detail="tool_id is required")

    try:
        return agent_service.attach_tool(agent_id=agent_id, tool_id=resolved_tool_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch(
    "/api/v2/agent-studio/agents/{agent_id}/tools/{tool_id}/detach",
    response_model=ApiToolAttachDetachResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Detach tool from agent",
    dependencies=[Depends(require_admin)],
)
async def api_detach_tool(
    agent_id: str,
    tool_id: str,
    agent_service: LettaAgentServiceDependency,
    lifecycle_registry: AgentLifecycleRegistryDependency,
):
    ensure_ade_api_enabled()
    ensure_agent_not_archived(agent_id, lifecycle_registry)

    resolved_tool_id = tool_id.strip()
    if not resolved_tool_id:
        raise HTTPException(status_code=400, detail="tool_id is required")

    try:
        return agent_service.detach_tool(agent_id=agent_id, tool_id=resolved_tool_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
