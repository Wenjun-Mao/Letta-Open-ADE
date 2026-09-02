from __future__ import annotations

from typing import Any


def definition_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "agent_definition_id": (
            str(row["agent_definition_id"]) if row.get("agent_definition_id") else None
        ),
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
        "archived_at": row.get("definition_archived_at"),
        "created_at": row["created_at"],
    }


def subject_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "external_key": row["external_key"],
        "display_name": row["display_name"],
        "version": int(row.get("version", 1)),
        "archived_at": row.get("archived_at"),
        "created_at": row["created_at"],
        "updated_at": row.get("updated_at", row["created_at"]),
    }


def conversation_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "agent_definition_id": str(row["agent_definition_version_id"]),
        "memory_subject_id": str(row["memory_subject_id"]),
        "title": row.get("title", "Conversation"),
        "purpose": row.get("purpose", "development"),
        "version": row["version"],
        "archived_at": row.get("archived_at"),
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
        "timeout_seconds": float(row["timeout_seconds"]),
        "retry_count": int(row["retry_count"]),
        "cancellation_requested_at": row["cancellation_requested_at"],
        "error_code": row["error_code"],
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
    }


def conversation_summary_response(
    row: dict[str, Any], *, source_message_ids: list[str]
) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "version": int(row["version"]),
        "previous_summary_id": (
            str(row["previous_summary_id"])
            if row["previous_summary_id"] is not None
            else None
        ),
        "content": row["content"],
        "source_boundary": {
            "through_sequence": int(row["through_sequence"]),
            "message_ids": source_message_ids,
        },
        "provenance": {
            "run_id": str(row["run_id"]),
            "model_key": row["model_key"],
            "model_fingerprint": row["model_fingerprint"],
            "provider_request_id": row["provider_request_id"],
            "content_sha256": row["content_sha256"],
            "prompt_sha256": row["prompt_sha256"],
            "input_sha256": row["input_sha256"],
            "policy_sha256": row["policy_sha256"],
        },
        "created_at": row["created_at"],
    }


def memory_revision_response(
    row: dict[str, Any],
    *,
    predecessor_revision_ids: list[str],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "operation": row["operation"],
        "fact_version": int(row["fact_version"]),
        "value": row["value"],
        "run_id": str(row["run_id"]),
        "predecessor_revision_ids": predecessor_revision_ids,
        "evidence": evidence,
        "created_at": row["created_at"],
    }


def memory_fact_response(
    row: dict[str, Any], *, revisions: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "key": row["normalized_key"],
        "fact_type": row["fact_type"],
        "entity_id": str(row["entity_id"]),
        "entity_kind": row["entity_kind"],
        "entity_label": row["entity_label"],
        "qualifier": row["qualifier"],
        "value": row["value"],
        "status": row["status"],
        "version": int(row["version"]),
        "revisions": revisions,
        "updated_at": row["updated_at"],
    }


def turn_accepted_response(row: dict[str, Any], *, replayed: bool) -> dict[str, Any]:
    run_id = str(row["id"])
    return {
        "run_id": run_id,
        "status": row["status"],
        "events_url": f"/api/v3/runs/{run_id}/events",
        "idempotent_replay": replayed,
    }
