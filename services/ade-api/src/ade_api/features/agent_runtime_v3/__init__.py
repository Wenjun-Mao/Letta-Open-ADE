"""ADE-owned conversational runtime.

The v3 package is intentionally independent from the retained Letta-backed v2
surface. Agent Studio uses this package without fallback or dual-write behavior.
"""

from .api import router


async def shutdown_agent_runtime_v3() -> None:
    """Release cached runtime resources during ADE API shutdown."""

    from .dependencies import shutdown_agent_runtime_v3_service

    await shutdown_agent_runtime_v3_service()


__all__ = ["router", "shutdown_agent_runtime_v3"]
