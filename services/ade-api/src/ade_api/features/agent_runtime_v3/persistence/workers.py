from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import and_, func, insert, select, true, update
from sqlalchemy.ext.asyncio import AsyncConnection

from .base import values
from .metadata import worker_instances


class WorkerInstanceRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def register(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = await self._connection.execute(
            insert(worker_instances)
            .values(**values(payload))
            .returning(*worker_instances.c)
        )
        return dict(result.mappings().one())

    async def heartbeat(self, instance_id: str) -> bool:
        result = await self._connection.execute(
            update(worker_instances)
            .where(
                and_(
                    worker_instances.c.instance_id == instance_id,
                    worker_instances.c.state.in_(("ready", "draining")),
                )
            )
            .values(heartbeat_at=func.clock_timestamp())
        )
        return result.rowcount == 1

    async def mark_draining(self, instance_id: str) -> bool:
        result = await self._connection.execute(
            update(worker_instances)
            .where(
                and_(
                    worker_instances.c.instance_id == instance_id,
                    worker_instances.c.state == "ready",
                )
            )
            .values(state="draining", heartbeat_at=func.clock_timestamp())
        )
        return result.rowcount == 1

    async def mark_stopped(self, instance_id: str) -> bool:
        result = await self._connection.execute(
            update(worker_instances)
            .where(
                and_(
                    worker_instances.c.instance_id == instance_id,
                    worker_instances.c.state.in_(("ready", "draining")),
                )
            )
            .values(
                state="stopped",
                heartbeat_at=func.clock_timestamp(),
                stopped_at=func.clock_timestamp(),
            )
        )
        return result.rowcount == 1

    async def health_snapshot(
        self,
        *,
        compatibility_fingerprint: str,
        source_revision: str,
        source_dirty: bool,
        source_fingerprint: str,
        freshness_seconds: float,
    ) -> dict[str, Any]:
        checked = select(func.clock_timestamp().label("checked_at")).cte(
            "worker_health_clock"
        )
        cutoff = checked.c.checked_at - timedelta(seconds=freshness_seconds)
        compatible = and_(
            worker_instances.c.state == "ready",
            worker_instances.c.compatibility_fingerprint == compatibility_fingerprint,
            worker_instances.c.heartbeat_at > cutoff,
        )
        matching_build = and_(
            compatible,
            worker_instances.c.source_revision == source_revision,
            worker_instances.c.source_dirty.is_(source_dirty),
            worker_instances.c.source_fingerprint == source_fingerprint,
        )
        result = await self._connection.execute(
            select(
                checked.c.checked_at,
                func.count(worker_instances.c.instance_id)
                .filter(compatible)
                .label("compatible_worker_count"),
                func.count(worker_instances.c.instance_id)
                .filter(matching_build)
                .label("matching_build_worker_count"),
                func.max(worker_instances.c.heartbeat_at)
                .filter(compatible)
                .label("latest_heartbeat_at"),
            )
            .select_from(checked.outerjoin(worker_instances, true()))
            .group_by(checked.c.checked_at)
        )
        return dict(result.mappings().one())
