from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ade_api.platform.auth import require_admin
from ade_api.platform.dependencies import (
    AgentLifecycleRegistryDependency,
    LettaClientDependency,
    ModelRouterClientDependency,
    PromptPersonaRegistryDependency,
)
from ade_api.platform.feature_flags import ensure_ade_api_enabled
from ade_api.features.agent_studio.context import derive_last_interaction_at
from ade_api.features.agent_studio.contracts import (
    AgentCreateRequest,
    ApiAgentCreateResponse,
    ApiAgentListResponse,
)
from ade_api.features.model_catalog import (
    agent_studio_llm_config_for_model,
    runtime_options,
)
from ade_api.features.prompt_center import (
    normalize_scenario,
    persona_content_map,
    prompt_content_map,
)
from ade_api.platform.openapi_metadata import TAG_AGENT_STUDIO
from content.personas import HUMAN_TEMPLATE

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/api/v2/agent-studio/agents",
    response_model=ApiAgentListResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="List Agent Studio agents",
)
async def api_list_agents(
    client: LettaClientDependency,
    lifecycle_registry: AgentLifecycleRegistryDependency,
    limit: int = 100,
    include_last_interaction: bool = False,
    include_archived: bool = False,
):
    """List existing agents so the UI can pull and inspect prior state."""
    ensure_ade_api_enabled()

    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be >= 1")
    if limit > 500:
        limit = 500

    archived_agent_ids = lifecycle_registry.archived_agent_ids()
    items = []
    for agent in client.agents.list():
        agent_id = str(getattr(agent, "id", ""))
        is_archived = agent_id in archived_agent_ids
        if is_archived and not include_archived:
            continue
        last_updated_at = str(getattr(agent, "last_updated_at", ""))
        if include_last_interaction:
            last_interaction_at = derive_last_interaction_at(
                agent_id,
                client,
                last_updated_at,
            )
        else:
            last_interaction_at = last_updated_at or str(
                getattr(agent, "created_at", "")
            )
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

    items.sort(
        key=lambda item: item["last_updated_at"] or item["created_at"], reverse=True
    )
    return {"total": len(items), "items": items[:limit]}


@router.post(
    "/api/v2/agent-studio/agents",
    response_model=ApiAgentCreateResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Create an Agent Studio agent",
)
async def api_create_agent(
    request: AgentCreateRequest,
    client: LettaClientDependency,
    model_router_client: ModelRouterClientDependency,
    prompt_registry: PromptPersonaRegistryDependency,
):
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(request.scenario)
    if resolved_scenario != "chat":
        raise HTTPException(
            status_code=400,
            detail=(
                "/api/v2/agent-studio/agents supports only scenario='chat'. "
                "Use /api/v2/comment-lab/generations for stateless comments "
                "or /api/v2/label-lab/generations for stateless labeling."
            ),
        )

    model_options, embedding_options = runtime_options(
        "chat",
        model_router_client=model_router_client,
        letta_client=client,
    )
    prompt_map = prompt_content_map(prompt_registry, "chat")
    persona_map = persona_content_map(prompt_registry, "chat")
    allowed_models = {option["key"] for option in model_options}
    allowed_embeddings = {option["key"] for option in embedding_options}

    if not request.model.strip():
        raise HTTPException(
            status_code=400, detail="Model is required. Please choose one."
        )
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
        raise HTTPException(
            status_code=400, detail=f"Invalid prompt key: {request.prompt_key}"
        )
    if request.persona_key not in persona_map:
        raise HTTPException(
            status_code=400, detail=f"Invalid persona key: {request.persona_key}"
        )
    if request.embedding and request.embedding not in allowed_embeddings:
        raise HTTPException(
            status_code=400, detail=f"Invalid embedding handle: {request.embedding}"
        )

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
    router_llm_config = agent_studio_llm_config_for_model(
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
