from __future__ import annotations

from typing import Any


def as_label_schema_record(record: dict[str, Any]) -> dict[str, Any]:
    """Map registry data to Schema Center's public response shape."""
    schema = record.get("schema")
    return {
        "key": str(record.get("key", "") or ""),
        "label": str(record.get("label", "") or ""),
        "description": str(record.get("description", "") or ""),
        "schema": schema if isinstance(schema, dict) else {},
        "preview": str(record.get("preview", "") or ""),
        "archived": bool(record.get("archived", False)),
        "source_path": str(record.get("source_path", "") or ""),
        "updated_at": str(record.get("updated_at", "") or ""),
    }
