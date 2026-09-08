from __future__ import annotations

from fastapi import APIRouter, Depends

from ade_api.platform.auth import require_reader
from ade_api.platform.dependencies import (
    CommentingServiceDependency,
    LabelingServiceDependency,
    LabelSchemaRegistryDependency,
    ModelRouterClientDependency,
    PromptPersonaRegistryDependency,
)
from ade_api.platform.feature_flags import ensure_ade_api_enabled
from ade_api.features.prompt_center import (
    normalize_scenario,
    persona_option_entries,
    prompt_option_entries,
    resolve_default_persona_key,
    resolve_default_prompt_key,
)
from ade_api.features.schema_center import (
    label_schema_option_entries,
    resolve_default_label_schema_key,
)
from ade_api.platform.openapi_metadata import TAG_MODEL_CATALOG

from .catalog import model_catalog
from .contracts import ApiOptionsResponse, ModelCatalogResponse
from .resolution import runtime_options
from .runtime_defaults import (
    agent_studio_runtime_defaults,
    commenting_runtime_defaults,
    labeling_runtime_defaults,
)

router = APIRouter(dependencies=[Depends(require_reader)])


@router.get(
    "/api/v2/model-catalog/options",
    response_model=ApiOptionsResponse,
    tags=[TAG_MODEL_CATALOG],
    summary="List runtime options for an ADE scenario",
)
async def api_get_options(
    model_router_client: ModelRouterClientDependency,
    prompt_registry: PromptPersonaRegistryDependency,
    schema_registry: LabelSchemaRegistryDependency,
    commenting_service: CommentingServiceDependency,
    labeling_service: LabelingServiceDependency,
    refresh: bool = False,
    scenario: str = "chat",
):
    """Return the resolved model and content options for one ADE scenario."""
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(scenario)

    model_options, embedding_options = runtime_options(
        resolved_scenario,
        model_router_client=model_router_client,
        force_refresh=refresh,
    )
    prompt_options = prompt_option_entries(prompt_registry, resolved_scenario)
    persona_options = persona_option_entries(prompt_registry, resolved_scenario)
    schema_options = (
        label_schema_option_entries(schema_registry)
        if resolved_scenario == "label"
        else []
    )
    for option in embedding_options:
        option["is_default"] = False

    return {
        "scenario": resolved_scenario,
        "models": model_options,
        "embeddings": embedding_options,
        "prompts": prompt_options,
        "personas": persona_options,
        "schemas": schema_options,
        "defaults": {
            "scenario": resolved_scenario,
            "model": "",
            "prompt_key": resolve_default_prompt_key(
                prompt_options,
                resolved_scenario,
            ),
            "persona_key": resolve_default_persona_key(
                persona_options,
                resolved_scenario,
            ),
            "embedding": "",
            "schema_key": (
                resolve_default_label_schema_key(schema_options)
                if resolved_scenario == "label"
                else ""
            ),
        },
        "agent_studio": (
            agent_studio_runtime_defaults().model_dump()
            if resolved_scenario == "chat"
            else None
        ),
        "commenting": (
            commenting_runtime_defaults(commenting_service).model_dump()
            if resolved_scenario == "comment"
            else None
        ),
        "labeling": (
            labeling_runtime_defaults(labeling_service).model_dump()
            if resolved_scenario == "label"
            else None
        ),
    }


@router.get(
    "/api/v2/model-catalog/models",
    response_model=ModelCatalogResponse,
    tags=[TAG_MODEL_CATALOG],
    summary="Get unified model-catalog diagnostics",
)
async def get_model_catalog(
    model_router_client: ModelRouterClientDependency,
    refresh: bool = False,
):
    ensure_ade_api_enabled()
    return model_catalog(
        model_router_client=model_router_client,
        force_refresh=refresh,
    )
