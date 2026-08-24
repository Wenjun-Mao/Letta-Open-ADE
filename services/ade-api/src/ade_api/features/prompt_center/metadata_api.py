from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ade_api.platform.auth import AdePrincipal, require_admin, require_reader
from ade_api.platform.dependencies import PromptPersonaRegistryDependency
from ade_api.platform.feature_flags import ensure_ade_api_enabled
from ade_api.platform.openapi_metadata import TAG_PROMPT_CENTER

from .contracts import (
    ApiPromptPersonaMetadataResponse,
    ApiPromptPersonaRevisionsResponse,
)
from .revision_log import read_prompt_persona_revisions
from .template_options import (
    active_persona_records,
    active_prompt_records,
    normalize_scenario,
    persona_option_entries,
    prompt_option_entries,
    resolve_default_persona_key,
    resolve_default_prompt_key,
)


router = APIRouter(dependencies=[Depends(require_reader)])


@router.get(
    "/api/v2/prompt-center/catalog",
    response_model=ApiPromptPersonaMetadataResponse,
    tags=[TAG_PROMPT_CENTER],
    summary="Get prompt and persona metadata",
)
async def prompt_persona_metadata(
    registry: PromptPersonaRegistryDependency,
    scenario: str = "chat",
):
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(scenario)

    prompts: list[dict[str, Any]] = [
        {
            "scenario": str(record.get("scenario", "") or resolved_scenario),
            "key": str(record.get("key", "") or ""),
            "label": str(record.get("label", "") or ""),
            "description": str(record.get("description", "") or ""),
            "preview": str(record.get("preview", "") or ""),
            "length": int(record.get("length", 0) or 0),
        }
        for record in active_prompt_records(registry, resolved_scenario)
    ]
    personas: list[dict[str, Any]] = [
        {
            "scenario": str(record.get("scenario", "") or resolved_scenario),
            "key": str(record.get("key", "") or ""),
            "preview": str(record.get("preview", "") or ""),
            "length": int(record.get("length", 0) or 0),
        }
        for record in active_persona_records(registry, resolved_scenario)
    ]
    default_prompt_key = resolve_default_prompt_key(
        prompt_option_entries(registry, resolved_scenario),
        resolved_scenario,
    )
    default_persona_key = resolve_default_persona_key(
        persona_option_entries(registry, resolved_scenario),
        resolved_scenario,
    )
    return {
        "defaults": {
            "scenario": resolved_scenario,
            "prompt_key": default_prompt_key,
            "persona_key": default_persona_key,
        },
        "prompts": prompts,
        "personas": personas,
    }


@router.get(
    "/api/v2/prompt-center/revisions",
    response_model=ApiPromptPersonaRevisionsResponse,
    tags=[TAG_PROMPT_CENTER],
    summary="Get prompt/persona revision history timeline",
)
async def prompt_persona_revisions(
    agent_id: str | None = None,
    field: str | None = None,
    limit: int = 80,
    _principal: AdePrincipal = Depends(require_admin),
):
    ensure_ade_api_enabled()
    resolved_field = (field or "").strip().lower() or None
    if resolved_field and resolved_field not in {"system", "persona", "human"}:
        raise HTTPException(
            status_code=400,
            detail="field must be one of: system, persona, human",
        )
    resolved_limit = max(1, min(limit, 500))
    resolved_agent_id = (agent_id or "").strip() or None
    items = read_prompt_persona_revisions(
        agent_id=resolved_agent_id,
        field=resolved_field,
        limit=resolved_limit,
    )
    return {
        "total": len(items),
        "limit": resolved_limit,
        "agent_id": resolved_agent_id,
        "field": resolved_field,
        "items": items,
    }
