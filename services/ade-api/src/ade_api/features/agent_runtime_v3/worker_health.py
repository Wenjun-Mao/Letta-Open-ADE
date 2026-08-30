from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.exc import SQLAlchemyError

from ade_api.platform.settings import AdeApiSettings, get_settings

from .database_boundary import RuntimeDatabase
from .errors import AgentRuntimeV3Error, RuntimeNotReady
from .persistence.database import create_persistence_engine
from .persistence.validation import migration_heads
from .persistence.workers import WorkerInstanceRepository


WORKER_CONTRACT_VERSION = "agent-runtime-v3-worker-v1"
RUNTIME_VERSION = os.getenv("ADE_API_VERSION", "0.3.0")
LOGGER = logging.getLogger(__name__)


def worker_compatibility_fingerprint(
    *,
    runtime_mode: str,
    contract_version: str = WORKER_CONTRACT_VERSION,
    migration_heads: tuple[str, ...] | None = None,
) -> str:
    payload = {
        "contract_version": contract_version,
        "migration_heads": list(
            migration_heads if migration_heads is not None else _migration_heads()
        ),
        "runtime_mode": str(runtime_mode),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def project_runtime_health(
    workers: list[dict[str, Any]],
    *,
    checked_at: datetime,
    freshness_seconds: float,
    compatibility_fingerprint: str,
    source_revision: str | None = None,
    source_dirty: bool | None = None,
    source_fingerprint: str | None = None,
) -> dict[str, Any]:
    compatible: list[dict[str, Any]] = []
    matching_build: list[dict[str, Any]] = []
    for worker in workers:
        age = max(
            0.0,
            (checked_at - worker["heartbeat_at"]).total_seconds(),
        )
        if (
            worker.get("state") == "ready"
            and worker.get("compatibility_fingerprint") == compatibility_fingerprint
            and age < freshness_seconds
        ):
            compatible.append(worker)
            if source_revision is None or (
                worker.get("source_revision") == source_revision
                and worker.get("source_dirty") is source_dirty
                and worker.get("source_fingerprint") == source_fingerprint
            ):
                matching_build.append(worker)
    worker_ready = bool(matching_build)
    return {
        "status": "ready" if worker_ready else "not_ready",
        "database_ready": True,
        "worker_ready": worker_ready,
        "checked_at": checked_at,
        "freshness_seconds": float(freshness_seconds),
        "compatible_worker_count": len(compatible),
        "matching_build_worker_count": len(matching_build),
        "compatibility_fingerprint": compatibility_fingerprint,
        "source_revision": source_revision or "",
        "source_dirty": source_dirty,
        "source_fingerprint": source_fingerprint or "",
        "latest_heartbeat_at": max(
            (worker["heartbeat_at"] for worker in compatible),
            default=None,
        ),
    }


class RuntimeWorkerHealthServiceProtocol(Protocol):
    async def get_health(self) -> dict[str, Any]: ...

    async def aclose(self) -> None: ...


class RuntimeWorkerHealthService:
    def __init__(self, *, engine: AsyncEngine, settings: AdeApiSettings) -> None:
        self.engine = engine
        self.settings = settings
        self.database = RuntimeDatabase(engine)

    async def aclose(self) -> None:
        await self.engine.dispose()

    async def get_health(self) -> dict[str, Any]:
        compatibility = _settings_fingerprint(self.settings)
        source_revision, source_dirty, source_fingerprint = _source_identity()
        source_valid = _source_identity_is_valid(source_revision, source_fingerprint)
        try:
            await self.database.ensure_ready()
            async with self.database.translated_errors():
                async with self.engine.connect() as connection:
                    snapshot = await WorkerInstanceRepository(
                        connection
                    ).health_snapshot(
                        compatibility_fingerprint=compatibility,
                        source_revision=source_revision,
                        source_dirty=source_dirty,
                        source_fingerprint=source_fingerprint,
                        freshness_seconds=(
                            self.settings.agent_runtime_v3_worker_stale_seconds
                        ),
                    )
        except (AgentRuntimeV3Error, SQLAlchemyError) as exc:
            LOGGER.warning(
                "Agent Runtime v3 worker health database check failed (%s)",
                type(exc).__name__,
            )
            return _not_ready_health(
                settings=self.settings,
                failure_code="database_unavailable",
                database_ready=False,
            )
        matching_count = (
            int(snapshot["matching_build_worker_count"]) if source_valid else 0
        )
        return {
            "status": "ready" if matching_count > 0 else "not_ready",
            "database_ready": True,
            "worker_ready": matching_count > 0,
            "checked_at": snapshot["checked_at"],
            "freshness_seconds": float(
                self.settings.agent_runtime_v3_worker_stale_seconds
            ),
            "compatible_worker_count": int(snapshot["compatible_worker_count"]),
            "matching_build_worker_count": matching_count,
            "compatibility_fingerprint": compatibility,
            "source_revision": source_revision,
            "source_dirty": source_dirty,
            "source_fingerprint": source_fingerprint,
            "latest_heartbeat_at": snapshot["latest_heartbeat_at"],
            "failure_code": (
                None
                if matching_count > 0
                else (
                    "compatible_worker_unavailable"
                    if source_valid
                    else "source_identity_unknown"
                )
            ),
        }


class UnavailableRuntimeWorkerHealthService:
    def __init__(self, *, settings: AdeApiSettings, failure_code: str) -> None:
        self.settings = settings
        self.failure_code = failure_code

    async def get_health(self) -> dict[str, Any]:
        return _not_ready_health(
            settings=self.settings,
            failure_code=self.failure_code,
            database_ready=False,
        )

    async def aclose(self) -> None:
        return None


class WorkerPresence:
    """Own one worker process's boot-scoped health session."""

    def __init__(
        self,
        *,
        engine: AsyncEngine,
        settings: AdeApiSettings,
        instance_id: str | None = None,
    ) -> None:
        self.engine = engine
        self.settings = settings
        self.instance_id = instance_id or str(uuid4())
        self.compatibility_fingerprint = _settings_fingerprint(settings)
        (
            self.source_revision,
            self.source_dirty,
            self.source_fingerprint,
        ) = _source_identity()
        if not _source_identity_is_valid(self.source_revision, self.source_fingerprint):
            raise RuntimeNotReady(
                "ADE-native worker requires exact source revision and fingerprint"
            )
        self._registered = False

    async def register(self) -> None:
        async with self.engine.begin() as connection:
            await WorkerInstanceRepository(connection).register(
                {
                    "instance_id": self.instance_id,
                    "worker_id": self.settings.agent_runtime_v3_worker_id,
                    "state": "ready",
                    "contract_version": WORKER_CONTRACT_VERSION,
                    "compatibility_fingerprint": self.compatibility_fingerprint,
                    "runtime_version": RUNTIME_VERSION,
                    "source_revision": self.source_revision,
                    "source_dirty": self.source_dirty,
                    "source_fingerprint": self.source_fingerprint,
                }
            )
        self._registered = True

    async def heartbeat(self) -> None:
        async with self.engine.begin() as connection:
            updated = await WorkerInstanceRepository(connection).heartbeat(
                self.instance_id
            )
        if not updated:
            raise RuntimeNotReady("ADE-native worker health session was lost")

    async def mark_draining(self) -> None:
        if not self._registered:
            return
        async with self.engine.begin() as connection:
            await WorkerInstanceRepository(connection).mark_draining(self.instance_id)

    async def mark_stopped(self) -> None:
        if not self._registered:
            return
        async with self.engine.begin() as connection:
            await WorkerInstanceRepository(connection).mark_stopped(self.instance_id)
        self._registered = False

    async def heartbeat_forever(self, stop: asyncio.Event) -> None:
        interval = self.settings.agent_runtime_v3_worker_heartbeat_seconds
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
            except TimeoutError:
                await self.heartbeat()


def build_runtime_worker_health_service(
    settings: AdeApiSettings | None = None,
) -> RuntimeWorkerHealthServiceProtocol:
    settings = settings or get_settings()
    if not settings.agent_runtime_v3_enabled:
        return UnavailableRuntimeWorkerHealthService(
            settings=settings,
            failure_code="runtime_disabled",
        )
    if not settings.database_url:
        return UnavailableRuntimeWorkerHealthService(
            settings=settings,
            failure_code="database_not_configured",
        )
    return RuntimeWorkerHealthService(
        engine=create_persistence_engine(settings.database_url),
        settings=settings,
    )


def _settings_fingerprint(settings: AdeApiSettings) -> str:
    return worker_compatibility_fingerprint(
        runtime_mode=settings.agent_runtime_v3_mode,
    )


def _migration_heads() -> tuple[str, ...]:
    return migration_heads()


def _source_identity() -> tuple[str, bool, str]:
    revision = (
        str(os.getenv("ADE_SOURCE_REVISION") or "unknown").strip().casefold()
        or "unknown"
    )
    dirty_value = str(os.getenv("ADE_SOURCE_DIRTY") or "true").strip().casefold()
    fingerprint = (
        str(os.getenv("ADE_SOURCE_FINGERPRINT") or "unknown").strip().casefold()
        or "unknown"
    )
    return (
        revision[:128],
        dirty_value not in {"0", "false", "no", "off"},
        fingerprint[:128],
    )


def _source_identity_is_valid(revision: str, fingerprint: str) -> bool:
    return bool(
        re.fullmatch(r"[0-9a-f]{40,64}", revision)
        and re.fullmatch(r"[0-9a-f]{64}", fingerprint)
    )


def _not_ready_health(
    *,
    settings: AdeApiSettings,
    failure_code: str,
    database_ready: bool,
) -> dict[str, Any]:
    source_revision, source_dirty, source_fingerprint = _source_identity()
    return {
        "status": "not_ready",
        "database_ready": database_ready,
        "worker_ready": False,
        "checked_at": datetime.now(UTC),
        "freshness_seconds": float(settings.agent_runtime_v3_worker_stale_seconds),
        "compatible_worker_count": 0,
        "matching_build_worker_count": 0,
        "compatibility_fingerprint": _settings_fingerprint(settings),
        "source_revision": source_revision,
        "source_dirty": source_dirty,
        "source_fingerprint": source_fingerprint,
        "latest_heartbeat_at": None,
        "failure_code": failure_code,
    }
