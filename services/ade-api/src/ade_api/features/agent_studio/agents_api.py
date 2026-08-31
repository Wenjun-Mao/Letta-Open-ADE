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
    model_option_identity_sha256,
    runtime_options,
)
from ade_api.features.prompt_center import (
    normalize_scenario,
    persona_content_map,
    prompt_content_map,
    template_content_sha256,
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

    model_option = next(
        option for option in model_options if option["key"] == request.model
    )
    embedding_option = (
        next(
            option for option in embedding_options if option["key"] == request.embedding
        )
        if request.embedding
        else None
    )
    resolved_identities = {
        "model_identity_sha256": model_option_identity_sha256(model_option),
        "embedding_identity_sha256": (
            model_option_identity_sha256(embedding_option)
            if embedding_option is not None
            else None
        ),
        "prompt_content_sha256": template_content_sha256(
            prompt_map[request.prompt_key]
        ),
        "persona_content_sha256": template_content_sha256(
            persona_map[request.persona_key]
        ),
    }
    _verify_expected_identities(request, resolved_identities)

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

    try:
        effective_identities = _verify_created_agent_state(
            client=client,
            agent_id=str(agent.id),
            request=request,
            prompt_content=prompt_map[request.prompt_key],
            persona_content=persona_map[request.persona_key],
            catalog_identities=resolved_identities,
        )
    except Exception as exc:
        try:
            client.agents.delete(agent_id=str(agent.id))
        except Exception:
            pass
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(
            status_code=409,
            detail=(
                "The created Letta agent could not be verified against the selected "
                f"evaluation inputs and was purged: {exc}"
            ),
        ) from exc

    return {
        "id": agent.id,
        "name": agent.name,
        "scenario": "chat",
        "model": request.model,
        "embedding": request.embedding,
        "prompt_key": request.prompt_key,
        "persona_key": request.persona_key,
        **effective_identities,
    }


def _verify_created_agent_state(
    *,
    client: Any,
    agent_id: str,
    request: AgentCreateRequest,
    prompt_content: str,
    persona_content: str,
    catalog_identities: dict[str, str | None],
) -> dict[str, str | None]:
    agent = client.agents.retrieve(agent_id=agent_id)
    blocks = list(client.agents.blocks.list(agent_id=agent_id))
    memory = {
        str(getattr(block, "label", "")): str(getattr(block, "value", ""))
        for block in blocks
    }
    effective_model = str(getattr(agent, "model", "") or "")
    effective_embedding = str(getattr(agent, "embedding", "") or "")
    mismatches: list[str] = []
    if effective_model != request.model:
        mismatches.append("model handle")
    if request.embedding and effective_embedding != request.embedding:
        mismatches.append("embedding handle")
    if template_content_sha256(str(getattr(agent, "system", "") or "")) != (
        template_content_sha256(prompt_content)
    ):
        mismatches.append("system prompt content")
    if template_content_sha256(memory.get("persona", "")) != (
        template_content_sha256(persona_content)
    ):
        mismatches.append("persona memory content")
    if mismatches:
        raise HTTPException(
            status_code=409,
            detail=(
                "Created Letta agent state does not match the selected inputs: "
                + ", ".join(mismatches)
            ),
        )
    return {
        **catalog_identities,
        "prompt_content_sha256": template_content_sha256(
            str(getattr(agent, "system", "") or "")
        ),
        "persona_content_sha256": template_content_sha256(memory["persona"]),
    }


def _verify_expected_identities(
    request: AgentCreateRequest,
    resolved: dict[str, str | None],
) -> None:
    labels = {
        "model_identity_sha256": "Model option",
        "embedding_identity_sha256": "Embedding option",
        "prompt_content_sha256": "Prompt template",
        "persona_content_sha256": "Persona template",
    }
    for field, label in labels.items():
        expected = getattr(request, field)
        if expected is not None and expected != resolved[field]:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{label} changed after the caller selected it. "
                    "Refresh the configuration and start a new run."
                ),
            )
