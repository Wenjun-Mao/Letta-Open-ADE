from __future__ import annotations

from typing import Any

from .content_identity import template_content_sha256


def as_template_record(record: dict[str, Any]) -> dict[str, Any]:
    content = str(record.get("content", "") or "")
    return {
        "kind": str(record.get("kind", "") or ""),
        "scenario": str(record.get("scenario", "") or "chat"),
        "key": str(record.get("key", "") or ""),
        "label": str(record.get("label", "") or ""),
        "description": str(record.get("description", "") or ""),
        "content": content,
        "content_sha256": template_content_sha256(content),
        "preview": str(record.get("preview", "") or ""),
        "length": int(record.get("length", 0) or 0),
        "archived": bool(record.get("archived", False)),
        "source_path": str(record.get("source_path", "") or ""),
        "updated_at": str(record.get("updated_at", "") or ""),
        "output_schema": str(record.get("output_schema", "") or "") or None,
    }
