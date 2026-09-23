"""Source, worker, and provider-budget gates before native qualification."""

from __future__ import annotations

import re
from typing import Any

from ade_api.features.agent_runtime.request_budget import budget_identity
from ade_api.features.agent_runtime.worker_health import (
    worker_compatibility_fingerprint,
)
from ade_api.platform.settings import get_settings


def budget_preflight_passed(
    health: dict[str, Any], *, diagnostic: bool, retry_count: int
) -> bool:
    settings = get_settings()
    budget = budget_identity(settings)
    if budget is None:
        return diagnostic
    if not diagnostic and (budget["stage"] != "qualification" or retry_count != 0):
        return False
    return health.get("compatibility_fingerprint") == worker_compatibility_fingerprint(
        runtime_mode=settings.agent_runtime_mode,
        budget=budget,
    )


def worker_preflight_passed(
    health: dict[str, Any],
    *,
    source_revision: str | None,
    source_dirty: bool | None,
    source_fingerprint: str | None,
    diagnostic: bool,
) -> bool:
    return (
        source_revision is not None
        and re.fullmatch(r"[0-9a-f]{40,64}", source_revision) is not None
        and source_dirty is not None
        and (diagnostic or source_dirty is False)
        and source_fingerprint is not None
        and re.fullmatch(r"[0-9a-f]{64}", source_fingerprint) is not None
        and health.get("http_status") == 200
        and health.get("status") == "ready"
        and health.get("database_ready") is True
        and health.get("worker_ready") is True
        and isinstance(health.get("matching_build_worker_count"), int)
        and not isinstance(health.get("matching_build_worker_count"), bool)
        and health["matching_build_worker_count"] >= 1
        and health.get("source_revision") == source_revision
        and health.get("source_dirty") is source_dirty
        and health.get("source_fingerprint") == source_fingerprint
    )
