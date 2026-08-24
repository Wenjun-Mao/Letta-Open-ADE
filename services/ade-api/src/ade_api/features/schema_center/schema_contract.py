from __future__ import annotations

import json
from typing import Any

_DEFAULT_LABEL_GROUPS = ("people", "organizations", "locations", "dates", "events")


def build_label_output_schema(
    group_names: list[str] | tuple[str, ...],
    *,
    max_items: int = 64,
) -> dict[str, Any]:
    keys = _normalize_group_names(group_names)
    if not keys:
        raise ValueError(
            "Label output schema must define at least one extraction group."
        )
    return {
        "type": "object",
        "properties": {
            key: {
                "type": "array",
                "maxItems": max_items,
                "items": {
                    "type": "string",
                    "minLength": 1,
                },
            }
            for key in keys
        },
        "required": list(keys),
        "additionalProperties": False,
    }


def default_label_output_schema() -> dict[str, Any]:
    return build_label_output_schema(_DEFAULT_LABEL_GROUPS)


def validate_label_output_schema_contract(schema: dict[str, Any]) -> list[str]:
    if not isinstance(schema, dict):
        return ["schema must be a JSON object"]
    if schema.get("type") != "object":
        return ["label schema must be a top-level object schema"]

    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        return ["label schema must define at least one extraction group"]

    required = schema.get("required")
    if not isinstance(required, list) or not required:
        return ["label schema must require every extraction group"]
    required_names = [
        str(item or "").strip() for item in required if str(item or "").strip()
    ]
    if set(required_names) != set(str(name) for name in properties):
        return ["label schema must require exactly the defined extraction groups"]

    if schema.get("additionalProperties") is not False:
        return ["label schema must set additionalProperties to false"]

    errors: list[str] = []
    for group_name, group_schema in properties.items():
        if not isinstance(group_schema, dict):
            errors.append(f"group '{group_name}' must be a schema object")
            continue
        if group_schema.get("type") != "array":
            errors.append(f"group '{group_name}' must be an array schema")
            continue
        items = group_schema.get("items")
        if not isinstance(items, dict) or items.get("type") != "string":
            errors.append(f"group '{group_name}' items must be string schemas")
            continue
    return errors


def label_schema_group_names(schema: dict[str, Any]) -> list[str]:
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return []
    return [str(key) for key in properties]


def schema_preview_text(schema: dict[str, Any]) -> str:
    return json.dumps(schema, ensure_ascii=False, indent=2)


def _normalize_group_names(group_names: list[str] | tuple[str, ...]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in group_names:
        key = str(item or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized
