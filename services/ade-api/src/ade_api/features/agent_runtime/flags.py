from __future__ import annotations

from ade_api.platform.settings import get_settings

from .errors import RuntimeFeatureDisabled


def ensure_agent_runtime_enabled() -> None:
    if not get_settings().agent_runtime_enabled:
        raise RuntimeFeatureDisabled(
            "ADE-native agent runtime is disabled. Set "
            "ADE_API_AGENT_RUNTIME_ENABLED=true only after applying its migrations."
        )
