from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ade_api.agent_access import fetch_agent_or_404, is_not_found_error
from ade_api.dependencies import agent_lifecycle_registry, agent_platform
from ade_api.feature_flags import ensure_platform_api_enabled
from ade_api.mappers import agent_lifecycle_payload
from ade_api.models.agents import ApiAgentLifecycleResponse, ApiAgentPurgeResponse
from ade_api.openapi_metadata import TAG_AGENT_STUDIO
from ade_api.registries.agent_lifecycle import AgentLifecycleRegistryError

router = APIRouter()


@router.post(
    "/api/v2/agent-studio/agents/{agent_id}/archive",
    response_model=ApiAgentLifecycleResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Archive agent (soft delete)",
)
async def api_platform_archive_agent(agent_id: str):
    ensure_platform_api_enabled()
    resolved_agent_id = agent_id.strip()
    if not resolved_agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    agent = fetch_agent_or_404(resolved_agent_id)
    try:
        archived = agent_lifecycle_registry.archive_agent(
            agent_id=resolved_agent_id,
            name=str(getattr(agent, "name", "")),
            model=str(getattr(agent, "model", "")),
        )
    except AgentLifecycleRegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return agent_lifecycle_payload(
        archived,
        fallback_name=str(getattr(agent, "name", "")),
        fallback_model=str(getattr(agent, "model", "")),
    )


@router.post(
    "/api/v2/agent-studio/agents/{agent_id}/restore",
    response_model=ApiAgentLifecycleResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Restore archived agent",
)
async def api_platform_restore_agent(agent_id: str):
    ensure_platform_api_enabled()
    resolved_agent_id = agent_id.strip()
    if not resolved_agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    archived_record = agent_lifecycle_registry.get_record(resolved_agent_id)
    if not archived_record or not bool(archived_record.get("archived", False)):
        raise HTTPException(status_code=400, detail=f"Agent '{resolved_agent_id}' is not archived")

    agent = fetch_agent_or_404(resolved_agent_id)
    try:
        restored = agent_lifecycle_registry.restore_agent(resolved_agent_id)
    except AgentLifecycleRegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return agent_lifecycle_payload(
        restored,
        fallback_name=str(getattr(agent, "name", "")),
        fallback_model=str(getattr(agent, "model", "")),
    )


def purge_archived_agent(agent_id: str) -> dict[str, Any]:
    resolved_agent_id = agent_id.strip()
    if not resolved_agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    archived_record = agent_lifecycle_registry.get_record(resolved_agent_id)
    if not archived_record or not bool(archived_record.get("archived", False)):
        raise HTTPException(status_code=400, detail=f"Agent '{resolved_agent_id}' must be archived before purge")

    try:
        agent_platform.delete_agent(agent_id=resolved_agent_id)
    except Exception as exc:
        if not is_not_found_error(exc):
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        agent_lifecycle_registry.purge_agent(resolved_agent_id)
    except AgentLifecycleRegistryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"ok": True, "id": resolved_agent_id, "kind": "agent"}


@router.delete(
    "/api/v2/agent-studio/agents/{agent_id}/purge",
    response_model=ApiAgentPurgeResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Purge archived agent (hard delete)",
)
async def api_platform_purge_agent(agent_id: str):
    ensure_platform_api_enabled()
    return purge_archived_agent(agent_id)


@router.delete(
    "/api/v2/agent-studio/agents/{agent_id}",
    response_model=ApiAgentPurgeResponse,
    tags=[TAG_AGENT_STUDIO],
    summary="Delete archived agent (hard delete)",
)
async def api_delete_agent(agent_id: str):
    ensure_platform_api_enabled()
    return purge_archived_agent(agent_id)
