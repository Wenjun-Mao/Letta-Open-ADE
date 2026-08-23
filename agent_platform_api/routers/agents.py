from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from agent_platform_api.agent_context import derive_last_interaction_at
from agent_platform_api.dependencies import agent_lifecycle_registry, client
from agent_platform_api.feature_flags import ensure_platform_api_enabled
from agent_platform_api.models.agents import AgentCreateRequest, ApiAgentCreateResponse, ApiAgentListResponse
from agent_platform_api.openapi_metadata import TAG_AGENT_STUDIO
from agent_platform_api.options import runtime_options
from agent_platform_api.settings import get_settings
from agent_platform_api.template_options import normalize_scenario, persona_content_map, prompt_content_map
from prompts.persona import HUMAN_TEMPLATE

router = APIRouter()


def _router_llm_config_for_model(
    model_handle: str,
    *,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
) -> dict[str, Any] | None:
    handle = str(model_handle or "").strip()
    if not handle.startswith("openai-proxy/") or "::" not in handle:
        return None
    router_base_url = get_settings().model_router_v1_base_url()
    if not router_base_url:
        return None
    provider_model_id = handle.split("/", 1)[1].strip()
    if not provider_model_id:
        return None
    config: dict[str, Any] = {
        "context_window": 16384,
        "model": provider_model_id,
        "model_endpoint_type": "openai",
        "model_endpoint": router_base_url,
        "handle": handle,
        "max_tokens": 16384,
        "parallel_tool_calls": False,
    }
    if temperature is not None:
        config["temperature"] = float(temperature)
    if top_p is not None:
        config["top_p"] = float(top_p)
    if top_k is not None:
        config["top_k"] = int(top_k)
    return config


@router.get(
    "/api/v1/agents",
    response_model=ApiAgentListResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="List Agent Studio agents",
)
async def api_list_agents(
    limit: int = 100,
    include_last_interaction: bool = False,
    include_archived: bool = False,
):
    """List existing agents so the UI can pull and inspect prior state."""
    ensure_platform_api_enabled()

    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be >= 1")
    if limit > 500:
        limit = 500

    archived_agent_ids = agent_lifecycle_registry.archived_agent_ids()
    items = []
    for agent in client.agents.list():
        agent_id = str(getattr(agent, "id", ""))
        is_archived = agent_id in archived_agent_ids
        if is_archived and not include_archived:
            continue
        last_updated_at = str(getattr(agent, "last_updated_at", ""))
        if include_last_interaction:
            last_interaction_at = derive_last_interaction_at(agent_id, last_updated_at)
        else:
            last_interaction_at = last_updated_at or str(getattr(agent, "created_at", ""))
        items.append(
            {
                "id": agent_id,
                "name": str(getattr(agent, "name", "")),
                "model": str(getattr(agent, "model", "")),
                "created_at": str(getattr(agent, "created_at", "")),
                "last_updated_at": last_updated_at,
                "last_interaction_at": last_interaction_at,
                "archived": is_archived,
            }
        )

    items.sort(key=lambda item: (item["last_updated_at"] or item["created_at"]), reverse=True)
    return {"total": len(items), "items": items[:limit]}


@router.post(
    "/api/v1/agents",
    response_model=ApiAgentCreateResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Create an Agent Studio agent",
)
async def api_create_agent(request: AgentCreateRequest):
    ensure_platform_api_enabled()
    resolved_scenario = normalize_scenario(request.scenario)
    if resolved_scenario != "chat":
        raise HTTPException(
            status_code=400,
            detail=(
                "/api/v1/agents supports only scenario='chat'. "
                "Use /api/v1/commenting/generate for stateless comments "
                "or /api/v1/labeling/generate for stateless labeling."
            ),
        )

    model_options, embedding_options = runtime_options("chat")
    prompt_map = prompt_content_map("chat")
    persona_map = persona_content_map("chat")
    allowed_models = {option["key"] for option in model_options}
    allowed_embeddings = {option["key"] for option in embedding_options}

    if not request.model.strip():
        raise HTTPException(status_code=400, detail="Model is required. Please choose one.")
    if request.model not in allowed_models:
        raise HTTPException(status_code=400, detail=f"Invalid model: {request.model}")
    if not request.prompt_key.startswith("chat_"):
        raise HTTPException(
            status_code=400,
            detail=f"Prompt key '{request.prompt_key}' is not valid for scenario 'chat'",
        )
    if not request.persona_key.startswith("chat_"):
        raise HTTPException(
            status_code=400,
            detail=f"Persona key '{request.persona_key}' is not valid for scenario 'chat'",
        )
    if request.prompt_key not in prompt_map:
        raise HTTPException(status_code=400, detail=f"Invalid prompt key: {request.prompt_key}")
    if request.persona_key not in persona_map:
        raise HTTPException(status_code=400, detail=f"Invalid persona key: {request.persona_key}")
    if request.embedding and request.embedding not in allowed_embeddings:
        raise HTTPException(status_code=400, detail=f"Invalid embedding handle: {request.embedding}")

    create_args: dict[str, Any] = {
        "name": request.name,
        "system": prompt_map[request.prompt_key],
        "model": request.model,
        "timezone": "Asia/Shanghai",
        "context_window_limit": 16384,
        "memory_blocks": [
            {"label": "persona", "value": persona_map[request.persona_key]},
            {"label": "human", "value": HUMAN_TEMPLATE},
        ],
    }
    if request.embedding:
        create_args["embedding"] = request.embedding
    router_llm_config = _router_llm_config_for_model(
        request.model,
        temperature=request.temperature,
        top_p=request.top_p,
        top_k=request.top_k,
    )
    if router_llm_config is not None:
        create_args["llm_config"] = router_llm_config

    try:
        agent = client.agents.create(**create_args)
    except Exception as exc:
        error_text = str(exc)
        if "Handle" in error_text and "not found" in error_text:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{error_text}. This handle is not registered on the current Letta server. "
                    "Refresh the model router and Letta catalog before creating this agent."
                ),
            ) from exc
        raise HTTPException(status_code=400, detail=error_text) from exc

    return {
        "id": agent.id,
        "name": agent.name,
        "scenario": "chat",
        "model": request.model,
        "embedding": request.embedding,
        "prompt_key": request.prompt_key,
        "persona_key": request.persona_key,
    }
