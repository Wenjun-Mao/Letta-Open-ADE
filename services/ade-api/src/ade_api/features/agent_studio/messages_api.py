from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ade_api.platform.auth import require_operator
from ade_api.platform.dependencies import (
    AgentLifecycleRegistryDependency,
    LettaAgentServiceDependency,
)
from ade_api.platform.feature_flags import ensure_ade_api_enabled
from ade_api.features.agent_studio.access import ensure_agent_not_archived
from ade_api.features.agent_studio.context import (
    is_datetime_query,
    runtime_datetime_system_hint,
)
from ade_api.features.agent_studio.contracts import ApiChatResponse, ChatRequest
from ade_api.platform.openapi_metadata import TAG_AGENT_STUDIO

router = APIRouter()


@router.post(
    "/api/v2/agent-studio/agents/{agent_id}/messages",
    response_model=ApiChatResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Send a chat message to a persistent Agent Studio agent",
    dependencies=[Depends(require_operator)],
)
async def api_chat(
    agent_id: str,
    request: ChatRequest,
    agent_service: LettaAgentServiceDependency,
    lifecycle_registry: AgentLifecycleRegistryDependency,
):
    ensure_ade_api_enabled()
    ensure_agent_not_archived(agent_id, lifecycle_registry)

    try:
        return agent_service.send_chat_message(
            agent_id=agent_id,
            message=request.message,
            datetime_system_hint=runtime_datetime_system_hint()
            if is_datetime_query(request.message)
            else None,
            timeout_seconds=request.timeout_seconds,
            retry_count=request.retry_count,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
