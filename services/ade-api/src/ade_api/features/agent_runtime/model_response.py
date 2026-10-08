"""Shared response-envelope and numeric usage mechanics for model protocols."""

from __future__ import annotations

from typing import Any

from .errors import RuntimeValidationError


def first_choice(response: dict[str, Any]) -> tuple[dict[str, Any], str]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise RuntimeValidationError(
            "Model response did not contain a choice",
            detail_code="model_response_choice_missing",
        )
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        raise RuntimeValidationError(
            "Model response choice did not contain a message",
            detail_code="model_response_message_missing",
        )
    return dict(message), str(choice.get("finish_reason", "") or "")


def merge_usage(total: dict[str, int], raw_usage: object) -> None:
    if not isinstance(raw_usage, dict):
        return
    for key, value in raw_usage.items():
        if isinstance(value, int) and not isinstance(value, bool):
            total[str(key)] = total.get(str(key), 0) + value
