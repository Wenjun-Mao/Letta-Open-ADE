from __future__ import annotations

from typing import Any

from ade_api.services.labeling_helpers import (
    build_best_effort_label_system_prompt,
    build_label_user_payload,
    build_repair_prompt,
    label_response_format,
)


def build_label_request_payload(
    *,
    model: str,
    system_prompt: str,
    article_input: str,
    output_schema: dict[str, Any],
    output_schema_name: str,
    output_mode: str,
    max_tokens: int,
    temperature: float,
    top_p: float,
    top_k: int | None,
) -> dict[str, Any]:
    """Build the provider request for one Label Lab extraction attempt."""
    if output_mode in {"strict_json_schema", "json_schema"}:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": str(system_prompt or "").strip()},
                {"role": "user", "content": build_label_user_payload(article_input)},
            ],
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "response_format": label_response_format(
                output_schema, name=output_schema_name
            ),
        }
    else:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": build_best_effort_label_system_prompt(
                        system_prompt=system_prompt,
                        schema=output_schema,
                    ),
                },
                {"role": "user", "content": build_label_user_payload(article_input)},
            ],
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }

    if max_tokens == 0:
        payload.pop("max_tokens", None)
    if top_k is not None:
        payload["top_k"] = top_k
    return payload


def build_label_repair_request_payload(
    *,
    model: str,
    system_prompt: str,
    article_input: str,
    output_schema: dict[str, Any],
    output_schema_name: str,
    output_mode: str,
    max_tokens: int,
    temperature: float,
    top_p: float,
    top_k: int | None,
    invalid_output: str,
    validation_errors: list[str],
) -> dict[str, Any]:
    """Build a label-repair request that retains the primary request's provider settings."""
    payload = build_label_request_payload(
        model=model,
        system_prompt=system_prompt,
        article_input=article_input,
        output_schema=output_schema,
        output_schema_name=output_schema_name,
        output_mode=output_mode,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
    )
    payload["messages"] = [
        payload["messages"][0],
        {
            "role": "user",
            "content": build_repair_prompt(
                article_input=article_input,
                invalid_output=invalid_output,
                validation_errors=validation_errors,
            ),
        },
    ]
    return payload
