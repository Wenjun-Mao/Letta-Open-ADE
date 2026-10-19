"""Conversation-first scheduling, paused input and explicit Retry receipts."""

import hashlib
import json

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from .base import IdempotencyConflictError, OptimisticLockError
from .conversations import ConversationRepository
from .metadata import conversation_leases, conversations, run_retry_requests, runs
from .runs import RunRepository


async def lock_run(connection: AsyncConnection, run_id: str) -> tuple[dict, dict]:
    repository = RunRepository(connection)
    identity = await repository.get(run_id)
    conversation = await ConversationRepository(connection).get_for_update(
        str(identity["conversation_id"])
    )
    return conversation, await repository.get_for_update(run_id)


class RunLifecycleRepository:
    def __init__(self, connection: AsyncConnection):
        self.connection = connection

    async def claim(
        self, *, workspace_id: str, runtime_mode: str, abandoned=False
    ) -> dict | None:
        statement = select(runs.c.id).join(
            conversations, conversations.c.id == runs.c.conversation_id
        )
        conditions = [
            runs.c.workspace_id == workspace_id,
            runs.c.accepted_runtime_mode == runtime_mode,
        ]
        if abandoned:
            statement = statement.join(
                conversation_leases, conversation_leases.c.run_id == runs.c.id
            )
            conditions.extend(
                [
                    runs.c.status == "running",
                    conversation_leases.c.released_at.is_(None),
                    conversation_leases.c.expires_at <= func.now(),
                ]
            )
        else:
            conditions.append(runs.c.status == "pending")
        run_id = await self.connection.scalar(
            statement.where(*conditions)
            .order_by(runs.c.created_at, runs.c.id)
            .with_for_update(of=conversations, skip_locked=True)
            .limit(1)
        )
        if run_id is None:
            return None
        run = await RunRepository(self.connection).get_for_update(str(run_id))
        if (
            run["status"] != ("running" if abandoned else "pending")
            or str(run["workspace_id"]) != workspace_id
            or run["accepted_runtime_mode"] != runtime_mode
        ):
            return None
        if not abandoned:
            await self.connection.execute(
                update(runs)
                .where(runs.c.id == run_id)
                .values(status="running", started_at=func.now())
            )
            run["status"] = "running"
        run["retry_attempt_base"] = await self.attempt_base(str(run_id))
        return run

    async def attempt_base(self, run_id: str) -> int:
        return int(
            await self.connection.scalar(
                select(
                    func.coalesce(
                        func.max(run_retry_requests.c.expected_attempt_count), 0
                    )
                ).where(run_retry_requests.c.run_id == run_id)
            )
            or 0
        )

    async def pause(self, run_id: str, *, detail_code: str) -> None:
        await self.connection.execute(
            update(runs)
            .where(runs.c.id == run_id, runs.c.status == "running")
            .values(
                status="paused",
                paused_at=func.now(),
                finished_at=None,
                error_code="memory_lookup_failed",
                error_message=f"Memory lookup failed ({detail_code}); Retry uses the saved message",
            )
        )

    async def retry(
        self, run: dict, *, idempotency_key: str, expected_attempt_count: int
    ) -> bool:
        payload = {
            "run_id": str(run["id"]),
            "expected_attempt_count": expected_attempt_count,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        receipt = (
            (
                await self.connection.execute(
                    select(run_retry_requests).where(
                        run_retry_requests.c.run_id == run["id"],
                        run_retry_requests.c.idempotency_key == idempotency_key,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if receipt is not None:
            if receipt["request_sha256"] != digest:
                raise IdempotencyConflictError(
                    "Retry key is already bound to another attempt"
                )
            return True
        if (
            run["status"] != "paused"
            or int(run["attempt_count"]) != expected_attempt_count
        ):
            raise OptimisticLockError("Saved reply changed; reload before Retry")
        await self.connection.execute(
            insert(run_retry_requests).values(
                run_id=run["id"],
                idempotency_key=idempotency_key,
                request_sha256=digest,
                expected_attempt_count=expected_attempt_count,
            )
        )
        await self.connection.execute(
            update(runs)
            .where(runs.c.id == run["id"])
            .values(
                status="pending",
                paused_at=None,
                started_at=None,
                finished_at=None,
                error_code=None,
                error_message=None,
            )
        )
        return False
