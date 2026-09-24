"""Provider-facing current-memory and embedding documents for a turn."""

from __future__ import annotations

from typing import Any

from .natural_memory_policy import PreparedNaturalOperation


def context_fact(fact: dict[str, Any]) -> dict[str, Any]:
    result = {
        "id": str(fact["id"]),
        "key": str(fact["normalized_key"]),
        "value": fact["value"],
        "version": int(fact["version"]),
    }
    if fact.get("status") == "inactive":
        result["status"] = "inactive"
    return result


def tool_fact(fact: dict[str, Any]) -> dict[str, Any]:
    return {
        **context_fact(fact),
        "fact_type": fact["fact_type"],
        "qualifier": fact["qualifier"],
        "distance": float(fact["distance"]),
    }


def fact_document(operation: Any) -> str:
    base = (
        f"fact_type: {operation.fact_type}\n"
        f"qualifier: {operation.qualifier or ''}\n"
        f"value: {operation.value or ''}"
    )
    if isinstance(operation, PreparedNaturalOperation):
        return (
            f"lifecycle_status: {operation.next_status}\n"
            f"lifecycle_reason: {operation.revision_reason or ''}\n{base}"
        )
    return base
