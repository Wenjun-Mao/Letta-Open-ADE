from __future__ import annotations

from typing import Any


def agent_lifecycle_payload(
    record: dict[str, Any],
    *,
    fallback_name: str = "",
    fallback_model: str = "",
) -> dict[str, Any]:
    return {
        "id": str(record.get("id", "") or ""),
        "name": str(record.get("name", "") or fallback_name),
        "model": str(record.get("model", "") or fallback_model),
        "archived": bool(record.get("archived", False)),
        "archived_at": record.get("archived_at"),
        "updated_at": str(record.get("updated_at", "") or ""),
    }
