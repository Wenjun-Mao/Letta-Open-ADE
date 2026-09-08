from __future__ import annotations

from typing import Any

from ade_api.platform.settings import get_settings


def agent_studio_llm_config_for_model(
    model_key: str,
    *,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
) -> dict[str, Any] | None:
    """Build a router-backed LLM config for a validated canonical model key."""
    resolved_model_key = str(model_key or "").strip()
    source_id, separator, provider_model_id = resolved_model_key.partition("::")
    if not separator or not source_id.strip() or not provider_model_id.strip():
        return None

    router_base_url = get_settings().model_router_v1_base_url()
    if not router_base_url:
        return None

    config: dict[str, Any] = {
        "context_window": 16384,
        "model": resolved_model_key,
        "model_endpoint_type": "openai",
        "model_endpoint": router_base_url,
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
