"""A stale scheduling observation cannot mutate a newly owned run/lease."""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from ade_api.features.agent_runtime.contracts import AcceptTurnRequest
from ade_api.features.agent_runtime.persistence.leases import (
    ConversationLeaseRepository,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    conversation_leases,
    run_attempts,
    runs,
)
from ade_api.features.agent_runtime.persistence.run_lifecycle import (
    RunLifecycleRepository,
)
from ade_api.features.agent_runtime.persistence.runs import RunRepository

from .hindsight_runtime_support import runtime
from .hindsight_support import DATABASE_URL, engine


pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Disposable Hindsight PostgreSQL fixture not configured"
)


@pytest.fixture(autouse=True)
def controlled_build_identity(monkeypatch):
    monkeypatch.setenv("ADE_SOURCE_REVISION", "f" * 40)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "true")
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "e" * 64)


@pytest.mark.parametrize("retry_count", [0, 1])
def test_recovery_must_own_lease_before_abandoning_original_attempt(
    monkeypatch, retry_count
):
    asyncio.run(_renewed_lease(monkeypatch, retry_count))


async def _renewed_lease(monkeypatch, retry_count):
    db = engine()
    try:
        owner, service, worker, _, _ = await runtime(db)
        accepted = await service.accept_turn(
            str(owner.conversation["id"]),
            AcceptTurnRequest(
                content="Owned input",
                idempotency_key=uuid4().hex,
                retry_count=retry_count,
            ),
        )
        original, _ = await worker.claimer.claim()
        started = await worker.attempts.start_attempt(original, 1)
        async with db.begin() as connection:
            await connection.execute(
                update(conversation_leases)
                .where(conversation_leases.c.lease_token == original.lease_token)
                .values(expires_at=func.now() - timedelta(seconds=1))
            )
        acquire = ConversationLeaseRepository.acquire

        async def renewed_before_acquire(repository, **kwargs):
            # Reproduce the interleaving where selection observed expiry, but the
            # original lease is valid by the time takeover attempts its CAS.
            async with db.begin() as connection:
                await connection.execute(
                    update(conversation_leases)
                    .where(conversation_leases.c.lease_token == original.lease_token)
                    .values(expires_at=func.now() + timedelta(seconds=60))
                )
            return await acquire(repository, **kwargs)

        monkeypatch.setattr(
            ConversationLeaseRepository, "acquire", renewed_before_acquire
        )
        claim, handled = await worker.claimer.claim()
        assert claim is None and handled
        async with db.connect() as connection:
            assert (
                await connection.scalar(
                    select(run_attempts.c.status).where(
                        run_attempts.c.id == started.attempt_id
                    )
                )
                == "running"
            )
            assert (await RunRepository(connection).get(accepted["run_id"]))[
                "status"
            ] == "running"
            assert await ConversationLeaseRepository(connection).owns(
                original.lease_token, accepted["run_id"]
            )
    finally:
        await db.dispose()


def test_recovered_cancellation_wins_over_exhausted_automatic_attempts():
    asyncio.run(_cancel_recovery())


async def _cancel_recovery():
    db = engine()
    try:
        owner, service, worker, _, _ = await runtime(db)
        accepted = await service.accept_turn(
            str(owner.conversation["id"]),
            AcceptTurnRequest(
                content="Cancellation preserves input", idempotency_key=uuid4().hex
            ),
        )
        original, _ = await worker.claimer.claim()
        await worker.attempts.start_attempt(original, 1)
        await service.cancel_run(accepted["run_id"])
        async with db.begin() as connection:
            await connection.execute(
                update(conversation_leases)
                .where(conversation_leases.c.lease_token == original.lease_token)
                .values(expires_at=func.now() - timedelta(seconds=1))
            )
        claim, handled = await worker.claimer.claim()
        assert claim is None and handled
        current = await service.get_run(accepted["run_id"])
        assert current["status"] == "cancelled" and current["attempt_count"] == 1
    finally:
        await db.dispose()


def test_claim_rechecks_latest_run_status_after_conversation_lock(monkeypatch):
    asyncio.run(_changed_run(monkeypatch))


async def _changed_run(monkeypatch):
    db = engine()
    try:
        owner, service, worker, _, _ = await runtime(db)
        accepted = await service.accept_turn(
            str(owner.conversation["id"]),
            AcceptTurnRequest(content="Pending input", idempotency_key=uuid4().hex),
        )
        get_locked = RunRepository.get_for_update

        async def changed_before_run_lock(repository, run_id):
            await repository._connection.execute(
                update(runs).where(runs.c.id == run_id).values(status="cancelled")
            )
            return await get_locked(repository, run_id)

        monkeypatch.setattr(RunRepository, "get_for_update", changed_before_run_lock)
        async with db.begin() as connection:
            claim = await RunLifecycleRepository(connection).claim(
                workspace_id=worker.database.workspace_id, runtime_mode="development"
            )
            assert claim is None
            assert (await RunRepository(connection).get(accepted["run_id"]))[
                "status"
            ] == "cancelled"
    finally:
        await db.dispose()
