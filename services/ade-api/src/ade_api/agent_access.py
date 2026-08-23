from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from ade_api.dependencies import agent_lifecycle_registry, client


def is_not_found_error(exc: Exception) -> bool:
    text = str(exc or "").lower()
    return "not found" in text or "404" in text


def fetch_agent_or_404(agent_id: str) -> Any:
    try:
        return client.agents.retrieve(agent_id=agent_id)
    except Exception as exc:
        if is_not_found_error(exc):
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def ensure_agent_not_archived(agent_id: str) -> None:
    record = agent_lifecycle_registry.get_record(agent_id)
    if record and bool(record.get("archived", False)):
        raise HTTPException(
            status_code=410,
            detail=f"Agent '{agent_id}' is archived. Restore it before using this endpoint.",
        )
