from __future__ import annotations

from typing import Any


def definition_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "definition_key": row["definition_key"],
        "version": row["version"],
        "name": row["name"],
        "prompt_key": row["prompt_key"],
        "prompt_sha256": row["prompt_sha256"],
        "persona_key": row["persona_key"],
        "persona_sha256": row["persona_sha256"],
        "tool_names": list(row["tool_names"]),
        "memory_policy_version": row["memory_policy_version"],
        "qualification_state": row["qualification_state"],
        "deployments": list(row["deployment_snapshot"]),
        "created_at": row["created_at"],
    }


def subject_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "external_key": row["external_key"],
        "display_name": row["display_name"],
        "created_at": row["created_at"],
    }


def conversation_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "agent_definition_id": str(row["agent_definition_version_id"]),
        "memory_subject_id": str(row["memory_subject_id"]),
        "version": row["version"],
        "created_at": row["created_at"],
    }


def message_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "sequence": row["sequence"],
        "role": row["role"],
        "content": row["content"],
        "run_id": str(row["run_id"]) if row.get("run_id") else None,
        "created_at": row["created_at"],
    }


def run_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "conversation_id": str(row["conversation_id"]),
        "status": row["status"],
        "qualification_state": row["qualification_state"],
        "attempt_count": row["attempt_count"],
        "cancellation_requested_at": row["cancellation_requested_at"],
        "error_code": row["error_code"],
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
    }


def turn_accepted_response(row: dict[str, Any], *, replayed: bool) -> dict[str, Any]:
    run_id = str(row["id"])
    return {
        "run_id": run_id,
        "status": row["status"],
        "events_url": f"/api/v3/runs/{run_id}/events",
        "idempotent_replay": replayed,
    }
