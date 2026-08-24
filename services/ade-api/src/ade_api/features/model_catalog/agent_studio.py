from __future__ import annotations

from typing import Any

from ade_api.platform.settings import get_settings


def agent_studio_llm_config_for_model(
    model_handle: str,
    *,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
) -> dict[str, Any] | None:
    """Build Letta's router-backed LLM config for a validated chat-model handle."""
    handle = str(model_handle or "").strip()
    if not handle.startswith("openai-proxy/") or "::" not in handle:
        return None

    router_base_url = get_settings().model_router_v1_base_url()
    if not router_base_url:
        return None

    provider_model_id = handle.split("/", 1)[1].strip()
    if not provider_model_id:
        return None

    config: dict[str, Any] = {
        "context_window": 16384,
        "model": provider_model_id,
        "model_endpoint_type": "openai",
        "model_endpoint": router_base_url,
        "handle": handle,
        "max_tokens": 16384,
        "parallel_tool_calls": False,
    }
    if temperature is not None:
        config["temperature"] = float(temperature)
    if top_p is not None:
        config["top_p"] = float(top_p)
    if top_k is not None:
        config["top_k"] = int(top_k)
    return config
