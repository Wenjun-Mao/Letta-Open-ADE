from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ade_api.features.prompt_center.contracts import (
    ApiTemplateListResponse,
    ApiTemplateRecordResponse,
    PersonaTemplatePatchRequest,
    PersonaTemplateWriteRequest,
)
from ade_api.features.prompt_center.mappers import as_template_record
from ade_api.features.prompt_center.template_options import normalize_scenario
from ade_api.features.prompt_center.types import RegistryError
from ade_api.platform.auth import require_admin
from ade_api.platform.dependencies import PromptPersonaRegistryDependency
from ade_api.platform.feature_flags import ensure_ade_api_enabled
from ade_api.platform.openapi_metadata import TAG_PROMPT_CENTER

router = APIRouter(dependencies=[Depends(require_admin)])


def _is_label_persona_selector(*, scenario: str | None, key: str | None = None) -> bool:
    resolved_scenario = str(scenario or "").strip().lower()
    resolved_key = str(key or "").strip().lower()
    return resolved_scenario == "label" or resolved_key.startswith("label_")


@router.get(
    "/api/v2/prompt-center/personas",
    response_model=ApiTemplateListResponse,
    tags=[TAG_PROMPT_CENTER],
    summary="List persona templates",
)
async def list_personas(
    registry: PromptPersonaRegistryDependency,
    include_archived: bool = False,
    scenario: str | None = None,
    search: str = "",
):
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(scenario) if scenario else None
    if _is_label_persona_selector(scenario=resolved_scenario):
        return {
            "total": 0,
            "scenario": resolved_scenario,
            "include_archived": include_archived,
            "items": [],
        }

    try:
        records = registry.list_templates(
            "persona",
            include_archived=include_archived,
            scenario=resolved_scenario,
            search=search,
        )
    except RegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    items = [as_template_record(record) for record in records]
    return {
        "total": len(items),
        "scenario": resolved_scenario,
        "include_archived": include_archived,
        "items": items,
    }


@router.get(
    "/api/v2/prompt-center/personas/{key}",
    response_model=ApiTemplateRecordResponse,
    tags=[TAG_PROMPT_CENTER],
    summary="Get persona template",
)
async def get_persona(
    key: str,
    registry: PromptPersonaRegistryDependency,
    archived: bool = False,
    scenario: str | None = None,
):
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(scenario) if scenario else None
    if _is_label_persona_selector(scenario=resolved_scenario, key=key):
        raise HTTPException(
            status_code=404,
            detail="Label scenario does not expose persona templates",
        )

    try:
        record = registry.get_template(
            "persona",
            key,
            archived=archived,
            scenario=resolved_scenario,
        )
    except RegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not record:
        raise HTTPException(status_code=404, detail="Persona template not found")
    return as_template_record(record)


@router.post(
    "/api/v2/prompt-center/personas",
    response_model=ApiTemplateRecordResponse,
    tags=[TAG_PROMPT_CENTER],
    summary="Create persona template",
)
async def create_persona(
    request: PersonaTemplateWriteRequest,
    registry: PromptPersonaRegistryDependency,
):
    ensure_ade_api_enabled()
    if _is_label_persona_selector(scenario=request.scenario, key=request.key):
        raise HTTPException(
            status_code=400,
            detail="Label scenario does not support persona templates",
        )
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="content is required")

    try:
        record = registry.create_template(
            "persona",
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
    "/api/v2/prompt-center/personas/{key}",
    response_model=ApiTemplateRecordResponse,
    tags=[TAG_PROMPT_CENTER],
    summary="Update persona template",
)
async def update_persona(
    key: str,
    request: PersonaTemplatePatchRequest,
    registry: PromptPersonaRegistryDependency,
    scenario: str | None = None,
):
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(scenario) if scenario else None
    if _is_label_persona_selector(scenario=resolved_scenario, key=key):
        raise HTTPException(
            status_code=400,
            detail="Label scenario does not support persona templates",
        )
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
            "persona",
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
    "/api/v2/prompt-center/personas/{key}/archive",
    response_model=ApiTemplateRecordResponse,
    tags=[TAG_PROMPT_CENTER],
    summary="Archive persona template",
)
async def archive_persona(
    key: str,
    registry: PromptPersonaRegistryDependency,
    scenario: str | None = None,
):
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(scenario) if scenario else None
    if _is_label_persona_selector(scenario=resolved_scenario, key=key):
        raise HTTPException(
            status_code=400,
            detail="Label scenario does not support persona templates",
        )
    try:
        record = registry.archive_template("persona", key, scenario=resolved_scenario)
    except RegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return as_template_record(record)


@router.post(
    "/api/v2/prompt-center/personas/{key}/restore",
    response_model=ApiTemplateRecordResponse,
    tags=[TAG_PROMPT_CENTER],
    summary="Restore archived persona template",
)
async def restore_persona(
    key: str,
    registry: PromptPersonaRegistryDependency,
    scenario: str | None = None,
):
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(scenario) if scenario else None
    if _is_label_persona_selector(scenario=resolved_scenario, key=key):
        raise HTTPException(
            status_code=400,
            detail="Label scenario does not support persona templates",
        )
    try:
        record = registry.restore_template("persona", key, scenario=resolved_scenario)
    except RegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return as_template_record(record)


@router.delete(
    "/api/v2/prompt-center/personas/{key}/purge",
    tags=[TAG_PROMPT_CENTER],
    summary="Purge archived persona template",
)
async def purge_persona(
    key: str,
    registry: PromptPersonaRegistryDependency,
    scenario: str | None = None,
):
    ensure_ade_api_enabled()
    resolved_scenario = normalize_scenario(scenario) if scenario else None
    if _is_label_persona_selector(scenario=resolved_scenario, key=key):
        raise HTTPException(
            status_code=400,
            detail="Label scenario does not support persona templates",
        )
    try:
        registry.purge_template("persona", key, scenario=resolved_scenario)
    except RegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "key": key, "kind": "persona"}
