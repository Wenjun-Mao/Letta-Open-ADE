"""Provider payload normalization and sampling defaults."""

from __future__ import annotations

from typing import Any

from model_router.catalog import RoutedModel
from model_router.settings import RouterSourceConfig


def _normalize_openai_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize ADE convenience values before they reach upstream providers."""
    next_payload = dict(payload)
    max_tokens = next_payload.get("max_tokens")
    if (
        isinstance(max_tokens, int | float)
        and not isinstance(max_tokens, bool)
        and max_tokens <= 0
    ):
        next_payload.pop("max_tokens", None)
    return next_payload


def _normalize_adapter_payload(
    source: RouterSourceConfig, payload: dict[str, Any]
) -> dict[str, Any]:
    """Preserve tool-choice meaning across provider wire-protocol variants."""

    next_payload = dict(payload)
    if source.adapter == "deepseek_openai":
        return _normalize_deepseek_payload(next_payload)
    if source.adapter != "llama_cpp_server":
        return next_payload

    tool_choice = next_payload.get("tool_choice")
    if not isinstance(tool_choice, dict):
        return next_payload
    function = tool_choice.get("function")
    selected_name = (
        str(function.get("name") or "").strip()
        if tool_choice.get("type") == "function" and isinstance(function, dict)
        else ""
    )
    if not selected_name:
        raise ValueError("llama.cpp named tool choice requires one function name")

    tools = next_payload.get("tools")
    if not isinstance(tools, list):
        raise ValueError("llama.cpp named tool choice requires a tools list")
    selected_tools = [
        tool
        for tool in tools
        if isinstance(tool, dict)
        and tool.get("type") == "function"
        and isinstance(tool.get("function"), dict)
        and str(tool["function"].get("name") or "").strip() == selected_name
    ]
    if len(selected_tools) != 1:
        raise ValueError(
            "llama.cpp named tool choice must match exactly one declared function"
        )

    # llama.cpp's OpenAI route supports `required`, but not OpenAI's named object.
    # Reducing the list preserves the exact ADE-selected function semantics.
    next_payload["tools"] = selected_tools
    next_payload["tool_choice"] = "required"
    return next_payload


def _normalize_deepseek_payload(payload: dict[str, Any]) -> dict[str, Any]:
    thinking = payload.get("thinking")
    if thinking is not None and (
        not isinstance(thinking, dict)
        or thinking.get("type") not in {"enabled", "disabled"}
    ):
        raise ValueError("DeepSeek thinking must have type enabled or disabled")
    reasoning_effort = payload.get("reasoning_effort")
    if reasoning_effort is not None and reasoning_effort not in {
        "none",
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
        "ultra",
    }:
        raise ValueError("DeepSeek reasoning_effort is unsupported")
    thinking_enabled = not (
        (isinstance(thinking, dict) and thinking["type"] == "disabled")
        or reasoning_effort == "none"
    )
    if (
        thinking is not None
        and reasoning_effort is not None
        and ((thinking["type"] == "disabled") != (reasoning_effort == "none"))
    ):
        raise ValueError("DeepSeek thinking and reasoning_effort conflict")
    response_format = payload.get("response_format")
    if response_format is not None and (
        not isinstance(response_format, dict)
        or response_format.get("type") not in {"text", "json_object"}
    ):
        raise ValueError(
            "DeepSeek supports text or json_object response_format, not json_schema"
        )
    if "chat_template_kwargs" in payload:
        raise ValueError("DeepSeek does not support chat_template_kwargs")
    if "top_k" in payload:
        raise ValueError("DeepSeek does not support top_k")
    if thinking_enabled:
        if (
            isinstance(payload.get("tool_choice"), dict)
            or payload.get("tool_choice") == "required"
        ):
            raise ValueError(
                "DeepSeek thinking mode does not support forced tool_choice"
            )
        for field in ("temperature", "presence_penalty", "frequency_penalty"):
            if field in payload:
                raise ValueError(f"DeepSeek thinking mode ignores {field}")
    if "top_p" in payload:
        try:
            top_p = float(payload["top_p"])
        except (TypeError, ValueError) as exc:
            raise ValueError("DeepSeek top_p must be numeric") from exc
        if not 0 < top_p <= 1:
            raise ValueError("DeepSeek top_p must be between 0 and 1")
    return payload


def _apply_sampling_defaults(
    routed_model: RoutedModel,
    source: RouterSourceConfig,
    payload: dict[str, Any],
) -> dict[str, Any]:
    defaults = routed_model.sampling_defaults or {}
    next_payload = dict(payload)
    if source.adapter == "deepseek_openai":
        if _payload_missing(next_payload, "thinking"):
            next_payload["thinking"] = {
                "type": (
                    "disabled"
                    if next_payload.get("reasoning_effort") == "none"
                    else "enabled"
                    if routed_model.thinking_default_enabled
                    else "disabled"
                )
            }
        if (
            next_payload["thinking"].get("type") == "enabled"
            and _payload_missing(next_payload, "reasoning_effort")
            and routed_model.reasoning_effort_default is not None
        ):
            next_payload["reasoning_effort"] = routed_model.reasoning_effort_default
        next_payload.setdefault("stream", False)
        return next_payload
    for field in ("temperature", "top_p"):
        if _payload_missing(next_payload, field) and defaults.get(field) is not None:
            next_payload[field] = defaults[field]
    if (
        _supports_top_k(routed_model, source)
        and _payload_missing(next_payload, "top_k")
        and defaults.get("top_k") is not None
    ):
        next_payload["top_k"] = defaults["top_k"]
    if _is_vllm_source(source):
        for field in ("min_p", "presence_penalty", "repetition_penalty"):
            if (
                _payload_missing(next_payload, field)
                and defaults.get(field) is not None
            ):
                next_payload[field] = defaults[field]
        if routed_model.supports_thinking and _chat_template_kwargs_missing(
            next_payload, "enable_thinking"
        ):
            next_payload["chat_template_kwargs"] = {
                **_existing_chat_template_kwargs(next_payload),
                "enable_thinking": _thinking_default_for_payload(
                    routed_model, next_payload
                ),
            }
    return next_payload


def _payload_missing(payload: dict[str, Any], field: str) -> bool:
    return field not in payload or payload.get(field) is None


def _existing_chat_template_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("chat_template_kwargs")
    return dict(value) if isinstance(value, dict) else {}


def _chat_template_kwargs_missing(payload: dict[str, Any], field: str) -> bool:
    value = payload.get("chat_template_kwargs")
    if not isinstance(value, dict):
        return True
    return field not in value or value.get(field) is None


def _thinking_default_for_payload(
    routed_model: RoutedModel, payload: dict[str, Any]
) -> bool:
    tools = payload.get("tools")
    if (
        isinstance(tools, list)
        and bool(tools)
        and routed_model.tool_call_thinking_default_enabled is not None
    ):
        return routed_model.tool_call_thinking_default_enabled
    return routed_model.thinking_default_enabled


def _supports_top_k(routed_model: RoutedModel, source: RouterSourceConfig) -> bool:
    return routed_model.supports_top_k or source.adapter in {
        "llama_cpp_server",
        "vllm_openai",
    }


def _is_vllm_source(source: RouterSourceConfig) -> bool:
    return source.adapter == "vllm_openai"
