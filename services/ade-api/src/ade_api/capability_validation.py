from __future__ import annotations

import os
from typing import Any

from ade_api.dependencies import agent_platform
from ade_api.feature_flags import is_truthy, platform_api_enabled


def missing_platform_capabilities(capabilities: dict[str, Any]) -> list[str]:
    missing: list[str] = []

    runtime = capabilities.get("runtime", {})
    if not runtime.get("per_request_model_override") and not runtime.get("per_request_model_override_via_extra_body"):
        missing.append("runtime.per_request_model_override")
    if not runtime.get("per_request_system_override") and not runtime.get("per_request_system_override_via_extra_body"):
        missing.append("runtime.per_request_system_override")

    control = capabilities.get("control", {})
    for capability in (
        "update_system_prompt",
        "update_agent_model",
        "update_core_memory_block",
        "attach_tool",
        "detach_tool",
    ):
        if not control.get(capability):
            missing.append(f"control.{capability}")
    return missing


def validate_platform_capabilities_startup() -> None:
    if not platform_api_enabled():
        return

    capabilities = agent_platform.capabilities()
    missing = missing_platform_capabilities(capabilities)
    if is_truthy(os.getenv("ADE_API_STRICT_CAPABILITIES")) and missing:
        raise RuntimeError(f"Missing required Agent Platform capabilities: {', '.join(missing)}")
