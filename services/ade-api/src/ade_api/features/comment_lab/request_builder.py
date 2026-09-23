from __future__ import annotations

from typing import Any

from ade_api.features.comment_lab.helpers import (
    build_all_in_system_prompt,
    build_classic_user_payload,
    build_structured_system_prompt,
    structured_response_format,
)


def build_comment_request_payload(
    *,
    model: str,
    system_prompt: str,
    persona_prompt: str,
    news_input: str,
    task_shape: str,
    max_tokens: int,
    cache_prompt: bool,
    source_adapter: str | None,
    enable_thinking: bool,
    enable_thinking_is_explicit: bool,
    temperature: float,
    top_p: float,
    top_k: int | None,
) -> dict[str, Any]:
    """Build the provider request for one Comment Lab generation attempt."""
    classic_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": str(system_prompt or "")},
            {
                "role": "user",
                "content": build_classic_user_payload(
                    persona_prompt=persona_prompt,
                    news_input=news_input,
                ),
            },
        ],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }
    all_in_system_payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": build_all_in_system_prompt(
                    system_prompt=system_prompt,
                    persona_prompt=persona_prompt,
                ),
            },
            {"role": "user", "content": str(news_input or "").strip()},
        ],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }
    structured_output_payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": build_structured_system_prompt(
                    system_prompt=system_prompt,
                    persona_prompt=persona_prompt,
                ),
            },
            {"role": "user", "content": str(news_input or "").strip()},
        ],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "response_format": structured_response_format(),
    }
    payload = {
        "classic": classic_payload,
        "all_in_system": all_in_system_payload,
        "structured_output": structured_output_payload,
    }.get(task_shape, classic_payload)

    adapter = str(source_adapter or "").strip().lower()
    if adapter == "deepseek_openai":
        payload.pop("temperature", None)
        if task_shape == "structured_output":
            payload["response_format"] = {"type": "json_object"}
            payload["messages"][0]["content"] += (
                '\n示例 JSON: {"comment":"这是一条可发布的中文评论。"}'
            )
        if enable_thinking_is_explicit:
            payload["thinking"] = {"type": "enabled" if enable_thinking else "disabled"}
            if not enable_thinking:
                payload["temperature"] = temperature

    if max_tokens == 0:
        payload.pop("max_tokens", None)
    if top_k is not None and adapter != "deepseek_openai":
        payload["top_k"] = top_k

    if adapter == "llama_cpp_server":
        payload["cache_prompt"] = cache_prompt
    if adapter == "vllm_openai" and enable_thinking_is_explicit:
        chat_template_kwargs = payload.get("chat_template_kwargs", {})
        if not isinstance(chat_template_kwargs, dict):
            chat_template_kwargs = {}
        payload["chat_template_kwargs"] = {
            **chat_template_kwargs,
            "enable_thinking": enable_thinking,
        }
    return payload


def build_structured_output_compatibility_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Remove unsupported provider-side schema enforcement while retaining prompt JSON rules."""
    fallback_payload = dict(payload)
    fallback_payload.pop("response_format", None)
    return fallback_payload
