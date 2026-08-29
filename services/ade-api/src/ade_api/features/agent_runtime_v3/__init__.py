"""ADE-owned conversational runtime preview.

The v3 package is intentionally independent from Agent Studio's Letta-backed
implementation. It remains disabled unless explicitly enabled by configuration.
"""

from .api import router


async def shutdown_agent_runtime_v3() -> None:
    """Release cached runtime resources during ADE API shutdown."""

    from .dependencies import shutdown_agent_runtime_v3_service

    await shutdown_agent_runtime_v3_service()


__all__ = ["router", "shutdown_agent_runtime_v3"]
