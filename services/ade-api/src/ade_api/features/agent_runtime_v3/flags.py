from __future__ import annotations

from ade_api.platform.settings import get_settings

from .errors import RuntimeFeatureDisabled


def ensure_agent_runtime_v3_enabled() -> None:
    if not get_settings().agent_runtime_v3_enabled:
        raise RuntimeFeatureDisabled(
            "ADE-native agent runtime v3 is disabled. Set "
            "ADE_API_AGENT_RUNTIME_V3_ENABLED=true only after applying its migrations."
        )
