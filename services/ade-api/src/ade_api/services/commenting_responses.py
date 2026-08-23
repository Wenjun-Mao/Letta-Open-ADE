from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ade_api.services.commenting_helpers import (
    extract_comment_from_reasoning,
    extract_structured_comment,
    is_publishable_comment,
    normalize_content,
    sanitize_comment,
)


def build_comment_generation_result(
    *,
    content: str,
    content_source: str,
    selected_attempt: str,
    finish_reason: str,
    data: dict[str, Any],
    payload: dict[str, Any],
    runtime: dict[str, Any],
) -> dict[str, Any]:
    """Map a usable provider answer into the Comment Lab result and diagnostics contract."""
    return {
        "content": content,
        "content_source": content_source,
        "selected_attempt": selected_attempt,
        "finish_reason": finish_reason,
        "usage": data.get("usage", {})
        if isinstance(data.get("usage", {}), dict)
        else {},
        "received_at": datetime.now(timezone.utc).isoformat(),
        "raw_request": payload,
        "raw_reply": data,
        **runtime,
    }


def map_comment_provider_response(
    *,
    data: dict[str, Any],
    payload: dict[str, Any],
    runtime: dict[str, Any],
    task_shape: str,
    max_tokens: int,
) -> dict[str, Any]:
    """Select a publishable comment or raise the established provider-response error."""
    choices = data.get("choices", [])
    if not isinstance(choices, list) or not choices:
        raise ValueError(
            f"Comment provider returned no choices; task_shape={task_shape}; max_tokens={max_tokens}"
        )

    choice = choices[0]
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    finish_reason = (
        str(choice.get("finish_reason", "") or "").strip().lower()
        if isinstance(choice, dict)
        else ""
    )
    content = normalize_content(message.get("content", ""))
    reasoning = normalize_content(
        message.get("reasoning_content", "") or message.get("reasoning", "")
    )

    if task_shape == "structured_output":
        content = extract_structured_comment(content)
        if not content:
            reasoning_structured = extract_structured_comment(reasoning)
            if reasoning_structured:
                cleaned_reasoning_structured = sanitize_comment(reasoning_structured)
                if is_publishable_comment(cleaned_reasoning_structured):
                    return build_comment_generation_result(
                        content=cleaned_reasoning_structured,
                        content_source="structured_json_reasoning_content",
                        selected_attempt=task_shape,
                        finish_reason=finish_reason,
                        data=data,
                        payload=payload,
                        runtime=runtime,
                    )

    if content:
        cleaned_content = sanitize_comment(content)
        if is_publishable_comment(cleaned_content):
            return build_comment_generation_result(
                content=cleaned_content,
                content_source="assistant_content",
                selected_attempt=task_shape,
                finish_reason=finish_reason,
                data=data,
                payload=payload,
                runtime=runtime,
            )

    recovered = extract_comment_from_reasoning(reasoning)
    if recovered:
        cleaned_recovered = sanitize_comment(recovered)
        if is_publishable_comment(cleaned_recovered):
            return build_comment_generation_result(
                content=cleaned_recovered,
                content_source="reasoning_tail_extraction",
                selected_attempt=task_shape,
                finish_reason=finish_reason,
                data=data,
                payload=payload,
                runtime=runtime,
            )

    if finish_reason and finish_reason != "stop":
        raise ValueError(
            "Comment provider finished without final content "
            f"(finish_reason={finish_reason}); task_shape={task_shape}; max_tokens={max_tokens}"
        )
    raise ValueError(
        f"Comment provider returned empty content; task_shape={task_shape}; max_tokens={max_tokens}"
    )
