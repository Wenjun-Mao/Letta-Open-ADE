from __future__ import annotations

import json
import re
from typing import Any


LABEL_PROBE_ARTICLE = "Messi scored for Inter Miami against Orlando City."
LABEL_PROBE_RESULT = {
    "players": ["Messi"],
    "teams": ["Inter Miami", "Orlando City"],
}
_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)


def label_probe_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            key: {
                "type": "array",
                "maxItems": 64,
                "items": {"type": "string", "minLength": 1},
            }
            for key in LABEL_PROBE_RESULT
        },
        "required": list(LABEL_PROBE_RESULT),
        "additionalProperties": False,
    }


def label_response_format(
    schema: dict[str, Any], *, name: str = "label_output"
) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {"name": name, "strict": True, "schema": schema},
    }


def build_label_probe_system_prompt() -> str:
    return (
        "Extract football entities from the article.\n"
        "Return JSON only with these keys:\n"
        '- "players": football player names\n'
        '- "teams": football clubs or team names\n\n'
        "Each value must be an array of exact substrings from the article."
    )


def build_label_user_payload(article_input: str) -> str:
    return str(article_input or "").strip()


def normalize_label_content(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = [
            str(item.get("text", "") or "").strip()
            for item in value
            if isinstance(item, dict)
        ]
        return "\n".join(part for part in parts if part).strip()
    return str(value or "").strip()


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = _THINK_TAG_RE.sub("", str(text or "")).strip()
    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("No JSON object could be extracted from provider output")


def label_probe_success(result: dict[str, Any]) -> bool:
    if set(result) != set(LABEL_PROBE_RESULT):
        return False
    for group, expected_values in LABEL_PROBE_RESULT.items():
        values = result.get(group)
        if not isinstance(values, list) or values != expected_values:
            return False
        if any(
            not isinstance(value, str) or value not in LABEL_PROBE_ARTICLE
            for value in values
        ):
            return False
    return True
