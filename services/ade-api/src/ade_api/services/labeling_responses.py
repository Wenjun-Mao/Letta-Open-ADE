from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ade_api.services.labeling_helpers import (
    normalize_label_content,
    parse_json_object,
    validate_label_result,
)


def extract_validated_label_response(
    *,
    data: dict[str, Any],
    article_input: str,
    output_schema: dict[str, Any],
) -> tuple[dict[str, list[str]] | None, str, list[str], str | None]:
    """Map the first provider choice into a validated label result or repair diagnostics."""
    choices = data.get("choices", [])
    if not isinstance(choices, list) or not choices:
        return None, "", ["Response payload did not include any choices."], None

    choice = choices[0] if isinstance(choices[0], dict) else {}
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    finish_reason = (
        str(choice.get("finish_reason", "") or "").strip().lower()
        if isinstance(choice, dict)
        else ""
    )
    content_candidate = normalize_label_content(message.get("content", ""))
    reasoning_candidate = normalize_label_content(message.get("reasoning_content", ""))
    candidates = [content_candidate] if content_candidate else [reasoning_candidate]
    validation_errors: list[str] = []
    invalid_output = ""
    for candidate in candidates:
        if not candidate:
            continue
        invalid_output = invalid_output or candidate
        try:
            parsed = parse_json_object(candidate)
        except ValueError as exc:
            validation_errors.append(str(exc))
            continue

        normalized, errors = validate_label_result(parsed, article_input, output_schema)
        if normalized is not None:
            return normalized, candidate, [], finish_reason or None
        validation_errors.extend(errors)

    if finish_reason and finish_reason != "stop":
        validation_errors.append(
            f"Provider finished with finish_reason={finish_reason}."
        )
    return (
        None,
        invalid_output,
        validation_errors or ["Provider returned empty content."],
        finish_reason or None,
    )


def build_label_generation_result(
    *,
    result: dict[str, list[str]],
    output_mode: str,
    selected_attempt: str,
    finish_reason: str | None,
    data: dict[str, Any],
    payload: dict[str, Any],
    runtime: dict[str, Any],
) -> dict[str, Any]:
    """Map a validated provider result into the Label Lab result and diagnostics contract."""
    return {
        "result": result,
        "output_mode": output_mode,
        "selected_attempt": selected_attempt,
        "finish_reason": finish_reason,
        "usage": data.get("usage", {})
        if isinstance(data.get("usage", {}), dict)
        else {},
        "received_at": datetime.now(timezone.utc).isoformat(),
        "raw_request": payload,
        "raw_reply": data,
        "validation_errors": [],
        **runtime,
    }


def append_finish_reason_diagnostic(
    validation_errors: list[str], finish_reason: str | None
) -> None:
    """Keep one non-stop finish reason in the final Label Lab validation diagnostics."""
    if (
        finish_reason
        and finish_reason != "stop"
        and not any(
            error.startswith("Provider finished with finish_reason=")
            for error in validation_errors
        )
    ):
        validation_errors.append(
            f"Provider finished with finish_reason={finish_reason}."
        )
