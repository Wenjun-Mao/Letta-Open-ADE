from __future__ import annotations

from typing import Any


def as_template_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": str(record.get("kind", "") or ""),
        "scenario": str(record.get("scenario", "") or "chat"),
        "key": str(record.get("key", "") or ""),
        "label": str(record.get("label", "") or ""),
        "description": str(record.get("description", "") or ""),
        "content": str(record.get("content", "") or ""),
        "preview": str(record.get("preview", "") or ""),
        "length": int(record.get("length", 0) or 0),
        "archived": bool(record.get("archived", False)),
        "source_path": str(record.get("source_path", "") or ""),
        "updated_at": str(record.get("updated_at", "") or ""),
        "output_schema": str(record.get("output_schema", "") or "") or None,
    }
