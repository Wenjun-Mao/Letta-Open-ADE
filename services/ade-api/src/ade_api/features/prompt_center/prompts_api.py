from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ade_api.platform.auth import require_admin
from ade_api.platform.dependencies import PromptPersonaRegistryDependency
from ade_api.platform.feature_flags import ensure_ade_api_enabled
from ade_api.features.prompt_center.contracts import (
    ApiTemplateListResponse,
    ApiTemplateRecordResponse,
    PromptTemplatePatchRequest,
    PromptTemplateWriteRequest,
)
from ade_api.features.prompt_center.mappers import as_template_record
from ade_api.features.prompt_center.template_options import normalize_scenario
from ade_api.features.prompt_center.types import RegistryError
from ade_api.platform.openapi_metadata import TAG_PROMPT_CENTER

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/api/v2/prompt-center/prompts",
    response_model=ApiTemplateListResponse,
    tags=[TAG_PROMPT_CENTER],
    summary="List system prompt templates",
)
async def api_prompt_center_list_prompts(
    registry: PromptPersonaRegistryDependency,
    include_archived: bool = False,
    scenario: str | None = None,
):
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(scenario) if scenario else None

    try:
        records = registry.list_templates(
            "prompt",
            include_archived=include_archived,
            scenario=resolved_scenario,
        )
    except RegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payload = [as_template_record(record) for record in records]
    return {
        "total": len(payload),
        "scenario": resolved_scenario,
        "include_archived": include_archived,
        "items": payload,
    }


@router.get(
    "/api/v2/prompt-center/prompts/{key}",
    response_model=ApiTemplateRecordResponse,
    tags=[TAG_PROMPT_CENTER],
    summary="Get system prompt template",
)
async def api_prompt_center_get_prompt(
    key: str,
    registry: PromptPersonaRegistryDependency,
    archived: bool = False,
    scenario: str | None = None,
):
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(scenario) if scenario else None

    try:
        record = registry.get_template(
            "prompt",
            key,
            archived=archived,
            scenario=resolved_scenario,
        )
    except RegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not record:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return as_template_record(record)


@router.post(
    "/api/v2/prompt-center/prompts",
    response_model=ApiTemplateRecordResponse,
    tags=[TAG_PROMPT_CENTER],
    summary="Create system prompt template",
)
async def api_prompt_center_create_prompt(
    request: PromptTemplateWriteRequest,
    registry: PromptPersonaRegistryDependency,
):
    ensure_ade_api_enabled()
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="content is required")

    try:
        record = registry.create_template(
            "prompt",
            key=request.key,
            content=request.content,
            label=request.label,
            description=request.description,
            scenario=request.scenario,
        )
    except RegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return as_template_record(record)


@router.patch(
    "/api/v2/prompt-center/prompts/{key}",
    response_model=ApiTemplateRecordResponse,
    tags=[TAG_PROMPT_CENTER],
    summary="Update system prompt template",
)
async def api_prompt_center_update_prompt(
    key: str,
    request: PromptTemplatePatchRequest,
    registry: PromptPersonaRegistryDependency,
    scenario: str | None = None,
):
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(scenario) if scenario else None
    if (
        request.label is None
        and request.description is None
        and request.content is None
    ):
        raise HTTPException(
            status_code=400, detail="At least one field must be provided"
        )

    try:
        record = registry.update_template(
            "prompt",
            key=key,
            content=request.content,
            label=request.label,
            description=request.description,
            scenario=resolved_scenario,
        )
    except RegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return as_template_record(record)


@router.post(
    "/api/v2/prompt-center/prompts/{key}/archive",
    response_model=ApiTemplateRecordResponse,
    tags=[TAG_PROMPT_CENTER],
    summary="Archive system prompt template",
)
async def api_prompt_center_archive_prompt(
    key: str,
    registry: PromptPersonaRegistryDependency,
    scenario: str | None = None,
):
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(scenario) if scenario else None

    try:
        record = registry.archive_template("prompt", key, scenario=resolved_scenario)
    except RegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return as_template_record(record)


@router.post(
    "/api/v2/prompt-center/prompts/{key}/restore",
    response_model=ApiTemplateRecordResponse,
    tags=[TAG_PROMPT_CENTER],
    summary="Restore archived system prompt template",
)
async def api_prompt_center_restore_prompt(
    key: str,
    registry: PromptPersonaRegistryDependency,
    scenario: str | None = None,
):
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(scenario) if scenario else None

    try:
        record = registry.restore_template("prompt", key, scenario=resolved_scenario)
    except RegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return as_template_record(record)


@router.delete(
    "/api/v2/prompt-center/prompts/{key}/purge",
    tags=[TAG_PROMPT_CENTER],
    summary="Purge archived system prompt template",
)
async def api_prompt_center_purge_prompt(
    key: str,
    registry: PromptPersonaRegistryDependency,
    scenario: str | None = None,
):
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(scenario) if scenario else None

    try:
        registry.purge_template("prompt", key, scenario=resolved_scenario)
    except RegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"ok": True, "key": key, "kind": "prompt"}
