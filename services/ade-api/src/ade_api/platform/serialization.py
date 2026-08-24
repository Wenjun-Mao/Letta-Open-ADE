from __future__ import annotations

import json
from typing import Any


def safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except Exception:
        return str(value)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return safe_json(json.loads(stripped))
            except Exception:
                return value
        return value
    if isinstance(value, list):
        text_parts = [getattr(item, "text", None) for item in value]
        valid_parts = [part for part in text_parts if isinstance(part, str) and part]
        if valid_parts:
            return " ".join(valid_parts)
        return safe_json(value)
    if isinstance(value, (dict, tuple)):
        return safe_json(value)
    return str(value)


def to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return to_jsonable(model_dump(mode="json"))
        except TypeError:
            return to_jsonable(model_dump())
        except Exception:
            pass

    to_dict = getattr(value, "dict", None)
    if callable(to_dict):
        try:
            return to_jsonable(to_dict())
        except Exception:
            pass

    return normalize_text(value)


def serialize_message(message: Any) -> dict[str, Any]:
    message_type = getattr(message, "message_type", "unknown")
    role = getattr(message, "role", message_type)

    content: Any = getattr(message, "content", None)
    if message_type == "reasoning_message":
        content = getattr(message, "reasoning", content)
    if message_type == "tool_return_message":
        content = getattr(message, "tool_return", content)

    tool_name = None
    tool_arguments = None
    tool_call = getattr(message, "tool_call", None)
    if tool_call is not None:
        tool_name = getattr(tool_call, "name", None)
        tool_arguments = normalize_text(getattr(tool_call, "arguments", None))

    timestamp = getattr(message, "created_at", None) or getattr(message, "date", None)
    return {
        "id": str(getattr(message, "id", "")),
        "created_at": str(timestamp or ""),
        "message_type": message_type,
        "role": role,
        "status": str(getattr(message, "status", "")),
        "name": tool_name,
        "tool_arguments": tool_arguments,
        "content": normalize_text(content),
    }
