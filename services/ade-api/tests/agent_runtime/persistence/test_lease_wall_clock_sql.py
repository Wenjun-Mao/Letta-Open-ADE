"""Expiry fences use current database time even inside an older transaction."""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from ade_api.features.agent_runtime.contracts import AcceptTurnRequest
from ade_api.features.agent_runtime.persistence.base import LeaseUnavailableError
from ade_api.features.agent_runtime.persistence.conversations import (
    ConversationRepository,
)
from ade_api.features.agent_runtime.persistence.leases import (
    ConversationLeaseRepository,
)
from ade_api.features.agent_runtime.persistence.memory_deliveries import (
    MemoryDeliveryRepository,
)
from ade_api.features.agent_runtime.persistence.memory import MemoryRepository
from ade_api.features.agent_runtime.persistence.memory_relationships import (
    MemoryRelationshipRepository,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    conversation_leases,
    memory_deliveries,
    memory_relationships,
)

from .hindsight_runtime_support import runtime
from .hindsight_support import DATABASE_URL, engine, message, scope


pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Disposable SQL not configured"
)


@pytest.mark.parametrize("kind", ["conversation", "delivery", "initialization"])
def test_expiry_during_an_open_transaction_invalidates_ownership(monkeypatch, kind):
    monkeypatch.setenv("ADE_SOURCE_REVISION", "f" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "e" * 64)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "true")
    asyncio.run(_expiry(kind))


async def _expiry(kind):
    db = engine()
    try:
        token = str(uuid4())
        if kind == "conversation":
            owner, service, worker, _, _ = await runtime(db)
            accepted = await service.accept_turn(
                str(owner.conversation["id"]),
                AcceptTurnRequest(content="Clock fence", idempotency_key=uuid4().hex),
            )
            claim, _ = await worker.claimer.claim()
            token, identity = claim.lease_token, accepted["run_id"]
            table, column, condition = (
                conversation_leases,
                "expires_at",
                conversation_leases.c.run_id == identity,
            )
        else:
            async with db.begin() as connection:
                owner = await scope(connection)
                await MemoryRelationshipRepository(connection).ensure(
                    owner.relationship
                )
                if kind == "delivery":
                    user, _ = await message(connection, owner)
                    row = await MemoryDeliveryRepository(connection).enqueue(user)
                    identity = str(row["operation_id"])
                    await MemoryDeliveryRepository(connection).claim(
                        workspace_id=owner.relationship.workspace_id,
                        token=token,
                        lease_seconds=30,
                    )
                    table, column, condition = (
                        memory_deliveries,
                        "lease_expires_at",
                        memory_deliveries.c.operation_id == identity,
                    )
                else:
                    identity = owner.relationship.bank_id
                    await MemoryRelationshipRepository(connection).claim_initialization(
                        identity,
                        workspace_id=owner.relationship.workspace_id,
                        token=token,
                        lease_seconds=30,
                    )
                    table, column, condition = (
                        memory_relationships,
                        "initialization_expires_at",
                        memory_relationships.c.bank_id == identity,
                    )
        async with db.begin() as connection:
            await connection.execute(
                update(table)
                .where(condition)
                .values({column: func.clock_timestamp() + timedelta(milliseconds=100)})
            )
            await connection.execute(select(func.pg_sleep(0.15)))
            assert await connection.scalar(
                select(func.clock_timestamp() >= table.c[column]).where(condition)
            )
            if kind == "conversation":
                repository = ConversationLeaseRepository(connection)
                assert not await repository.owns(token, identity)
                assert not await repository.heartbeat(token, lease_seconds=30)
            elif kind == "delivery":
                repository = MemoryDeliveryRepository(connection)
                assert not await repository.heartbeat(identity, token, lease_seconds=30)
                with pytest.raises(LeaseUnavailableError):
                    await repository.record_native(
                        identity,
                        token,
                        status="retained",
                        native_status="completed",
                        progress={},
                        acknowledgement="reconciliation",
                    )
            else:
                with pytest.raises(LeaseUnavailableError):
                    await MemoryRelationshipRepository(
                        connection
                    ).finish_initialization(
                        identity,
                        workspace_id=owner.relationship.workspace_id,
                        token=token,
                        state="ready",
                    )
    finally:
        await db.dispose()


def test_finalization_cannot_commit_after_waiting_past_its_lease(monkeypatch):
    monkeypatch.setenv("ADE_SOURCE_REVISION", "f" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "e" * 64)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "true")
    asyncio.run(_late_finalization(monkeypatch))


async def _late_finalization(monkeypatch):
    db = engine()
    task = None
    try:
        owner, service, worker, _, transport = await runtime(db)
        transport.started, transport.release = asyncio.Event(), asyncio.Event()
        accepted = await service.accept_turn(
            str(owner.conversation["id"]),
            AcceptTurnRequest(content="Late final commit", idempotency_key=uuid4().hex),
        )
        reached_subject = asyncio.Event()
        original = MemoryRepository.lock_subject

        async def lock_subject(repository, subject_id):
            reached_subject.set()
            return await original(repository, subject_id)

        monkeypatch.setattr(MemoryRepository, "lock_subject", lock_subject)
        task = asyncio.create_task(worker.process_once())
        await asyncio.wait_for(transport.started.wait(), timeout=2)
        async with db.begin() as blocker:
            await original(MemoryRepository(blocker), owner.relationship.subject_id)
            transport.release.set()
            await asyncio.wait_for(reached_subject.wait(), timeout=2)
            async with db.begin() as connection:
                await connection.execute(
                    update(conversation_leases)
                    .where(conversation_leases.c.run_id == accepted["run_id"])
                    .values(
                        expires_at=func.clock_timestamp() + timedelta(milliseconds=50)
                    )
                )
            await blocker.execute(select(func.pg_sleep(0.1)))
        await asyncio.wait_for(task, timeout=2)
        async with db.connect() as connection:
            messages = await ConversationRepository(connection).list_messages(
                str(owner.conversation["id"])
            )
            assert [row["role"] for row in messages] == ["user"]
            assert (
                await MemoryDeliveryRepository(connection).list(
                    owner.relationship.bank_id
                )
            )[0] == 1
        _, handled = await worker.claimer.claim()
        assert handled
        assert (await service.get_run(accepted["run_id"]))["status"] == "failed"
    finally:
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await db.dispose()
