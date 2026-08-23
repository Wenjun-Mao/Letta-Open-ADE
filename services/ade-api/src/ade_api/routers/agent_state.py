from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ade_api.agent_context import derive_last_interaction_at
from ade_api.dependencies import client
from ade_api.feature_flags import ensure_platform_api_enabled
from ade_api.models.agents import (
    ApiAgentDetailsResponse,
    ApiPersistentStateResponse,
    ApiRawPromptResponse,
)
from ade_api.openapi_metadata import TAG_AGENT_STUDIO
from ade_api.serialization import normalize_text, serialize_message, to_jsonable

router = APIRouter()


@router.get(
    "/api/v2/agent-studio/agents/{agent_id}",
    response_model=ApiAgentDetailsResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Get Agent Studio agent details",
)
async def api_get_agent_details(agent_id: str):
    ensure_platform_api_enabled()

    agent = client.agents.retrieve(agent_id=agent_id)
    tools_raw = list(client.agents.tools.list(agent_id=agent.id))
    tools = {tool.name: tool.description for tool in tools_raw}
    blocks = client.agents.blocks.list(agent_id=agent_id)
    memory = {block.label: block.value for block in blocks}

    last_updated_at = str(getattr(agent, "last_updated_at", ""))
    return {
        "id": getattr(agent, "id", agent_id),
        "name": getattr(agent, "name", "Unknown"),
        "agent_type": str(getattr(agent, "agent_type", "Unknown")),
        "model": getattr(agent, "model", "Unknown"),
        "embedding": getattr(agent, "embedding", None),
        "llm_config": to_jsonable(getattr(agent, "llm_config", None)),
        "embedding_config": to_jsonable(getattr(agent, "embedding_config", None)),
        "tool_rules": to_jsonable(getattr(agent, "tool_rules", None)),
        "description": getattr(agent, "description", None),
        "created_at": str(getattr(agent, "created_at", "")),
        "last_updated_at": last_updated_at,
        "last_interaction_at": derive_last_interaction_at(agent_id, last_updated_at),
        "context_window_limit": getattr(agent, "context_window_limit", None),
        "tools": tools,
        "system": getattr(agent, "system", "Unknown"),
        "memory": memory,
    }


@router.get(
    "/api/v2/agent-studio/agents/{agent_id}/persistent-state",
    response_model=ApiPersistentStateResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Get persisted Agent Studio state",
)
async def api_get_agent_persistent_state(agent_id: str, limit: int = 120, include_system: bool = False):
    ensure_platform_api_enabled()
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be >= 1")
    if limit > 500:
        limit = 500

    agent = client.agents.retrieve(agent_id=agent_id)
    blocks = list(client.agents.blocks.list(agent_id=agent_id))
    tools_raw = list(client.agents.tools.list(agent_id=agent_id))
    messages = list(client.agents.messages.list(agent_id=agent_id))

    serialized_messages = []
    type_counts: dict[str, int] = {}
    for message in messages:
        message_type = str(getattr(message, "message_type", "unknown"))
        if not include_system and message_type == "system_message":
            continue
        serialized_messages.append(serialize_message(message))
        type_counts[message_type] = type_counts.get(message_type, 0) + 1

    total_persisted = len(serialized_messages)
    if len(serialized_messages) > limit:
        serialized_messages = serialized_messages[-limit:]

    return {
        "source": "letta_backend_persistent_storage",
        "agent": {
            "id": getattr(agent, "id", agent_id),
            "name": getattr(agent, "name", ""),
            "agent_type": str(getattr(agent, "agent_type", "")),
            "model": getattr(agent, "model", ""),
            "embedding": getattr(agent, "embedding", None),
            "created_at": str(getattr(agent, "created_at", "")),
            "last_updated_at": str(getattr(agent, "last_updated_at", "")),
            "context_window_limit": getattr(agent, "context_window_limit", None),
            "tool_rules": normalize_text(getattr(agent, "tool_rules", None)),
        },
        "memory_blocks": [
            {
                "label": getattr(block, "label", ""),
                "description": getattr(block, "description", ""),
                "limit": getattr(block, "limit", None),
                "value": getattr(block, "value", ""),
            }
            for block in blocks
        ],
        "tools": [
            {
                "id": getattr(tool, "id", ""),
                "name": getattr(tool, "name", ""),
                "description": getattr(tool, "description", ""),
            }
            for tool in tools_raw
        ],
        "conversation_history": {
            "total_persisted": total_persisted,
            "displayed": len(serialized_messages),
            "limit": limit,
            "counts_by_type": type_counts,
            "items": serialized_messages,
        },
    }


@router.get(
    "/api/v2/agent-studio/agents/{agent_id}/raw-prompt",
    response_model=ApiRawPromptResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Get raw prompt messages for an Agent Studio agent",
)
async def api_get_raw_prompt(agent_id: str):
    ensure_platform_api_enabled()
    messages = list(client.agents.messages.list(agent_id=agent_id))
    formatted_messages = []
    for message in messages[-10:]:
        content = getattr(message, "content", "") or getattr(message, "reasoning", str(message))
        role = getattr(message, "role", getattr(message, "message_type", "unknown"))
        formatted_messages.append({"role": role, "content": normalize_text(content)})
    return {"messages": formatted_messages}
