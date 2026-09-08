"""ADE-owned conversational runtime for the `/api/v3` Agent Studio contract.

Agent Studio uses this runtime directly; there is no sidecar, fallback backend,
or dual-write path.
"""

from .api import router


async def shutdown_agent_runtime() -> None:
    """Release cached runtime resources during ADE API shutdown."""

    from .dependencies import shutdown_agent_runtime_service

    await shutdown_agent_runtime_service()


__all__ = ["router", "shutdown_agent_runtime"]
