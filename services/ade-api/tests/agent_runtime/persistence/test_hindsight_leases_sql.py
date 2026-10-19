"""PostgreSQL ordering, unrelated progress, restart recovery and stale-worker fencing."""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, update

from ade_api.features.agent_runtime.persistence.base import (
    LeaseUnavailableError,
    OptimisticLockError,
)
from ade_api.features.agent_runtime.persistence.memory_deliveries import (
    MemoryDeliveryRepository,
    MAX_RECONCILIATION_ERRORS,
)
from ade_api.features.agent_runtime.persistence.memory_relationships import (
    MemoryRelationshipRepository,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    memory_deliveries,
    memory_relationships,
)

from .hindsight_support import DATABASE_URL, engine, message, scope


pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Disposable ADE_TEST_DATABASE_URL is required"
)


async def queue(connection, owner):
    repository = MemoryDeliveryRepository(connection)
    user, run_id = await message(connection, owner)
    first = await repository.enqueue(user)
    assistant, _ = await message(
        connection,
        owner,
        role="assistant",
        run_id=run_id,
        content="Committed controlled reply",
    )
    second = await repository.enqueue(assistant, earlier_messages=(user,))
    return first, second


async def claim(db, owner, token):
    async with db.begin() as connection:
        return await MemoryDeliveryRepository(connection).claim(
            workspace_id=owner.relationship.workspace_id,
            token=token,
            lease_seconds=30,
        )


def test_failed_relationship_blocks_its_successor_not_another_character():
    async def scenario():
        db = engine()
        try:
            async with db.begin() as connection:
                owner = await scope(connection)
                first, second = await queue(connection, owner)
            token = str(uuid4())
            current = await claim(db, owner, token)
            assert current["operation_id"] == first["operation_id"]
            async with db.begin() as connection:
                await MemoryDeliveryRepository(connection).record_error(
                    str(first["operation_id"]),
                    token,
                    error_code="native_failed",
                    permanent=True,
                )
                # Cross-relationship timestamps may tie; no global FIFO is promised.
                other = await scope(
                    connection,
                    workspace_id=owner.relationship.workspace_id,
                    subject_id=owner.relationship.subject_id,
                )
                unrelated, _ = await queue(connection, other)
            next_claim = await claim(db, owner, str(uuid4()))
            assert next_claim["operation_id"] == unrelated["operation_id"]
            assert next_claim["operation_id"] != second["operation_id"]
        finally:
            await db.dispose()

    asyncio.run(scenario())


def test_concurrent_workers_cannot_claim_two_items_from_one_relationship():
    async def scenario():
        db = engine()
        try:
            async with db.begin() as connection:
                owner = await scope(connection)
                first, _ = await queue(connection, owner)
            results = await asyncio.gather(
                claim(db, owner, str(uuid4())), claim(db, owner, str(uuid4()))
            )
            claimed = [row for row in results if row]
            assert len(claimed) == 1
            assert claimed[0]["operation_id"] == first["operation_id"]
        finally:
            await db.dispose()

    asyncio.run(scenario())


def test_expired_owner_cannot_heartbeat_or_finish_after_recovery():
    async def scenario():
        db = engine()
        try:
            async with db.begin() as connection:
                owner = await scope(connection)
                first, second = await queue(connection, owner)
            old, new = str(uuid4()), str(uuid4())
            original = await claim(db, owner, old)
            async with db.begin() as connection:
                await connection.execute(
                    update(memory_deliveries)
                    .where(
                        memory_deliveries.c.operation_id == first["operation_id"],
                    )
                    .values(lease_expires_at=func.now() - timedelta(seconds=1))
                )
            recovered = await claim(db, owner, new)
            assert recovered["operation_id"] == original["operation_id"]
            assert recovered["payload"] == original["payload"]
            async with db.begin() as connection:
                assert not await MemoryDeliveryRepository(connection).heartbeat(
                    str(first["operation_id"]), old, lease_seconds=30
                )
            with pytest.raises(LeaseUnavailableError):
                async with db.begin() as connection:
                    await MemoryDeliveryRepository(connection).record_native(
                        str(first["operation_id"]),
                        old,
                        status="retained",
                        native_status="completed",
                        progress={},
                        acknowledgement="reconciliation",
                    )
            async with db.begin() as connection:
                await MemoryDeliveryRepository(connection).record_native(
                    str(first["operation_id"]),
                    new,
                    status="retained",
                    native_status="completed",
                    progress={"reported_progress": {"processed": 1, "total": 15}},
                    acknowledgement="reconciliation",
                )
            assert (await claim(db, owner, str(uuid4())))["operation_id"] == second[
                "operation_id"
            ]
        finally:
            await db.dispose()

    asyncio.run(scenario())


def test_uncertain_exhaustion_requires_explicit_retry_without_new_identity():
    async def scenario():
        db = engine()
        try:
            async with db.begin() as connection:
                owner = await scope(connection)
                first, _ = await queue(connection, owner)
            for _ in range(MAX_RECONCILIATION_ERRORS):
                token = str(uuid4())
                current = await claim(db, owner, token)
                assert current["operation_id"] == first["operation_id"]
                async with db.begin() as connection:
                    await MemoryDeliveryRepository(connection).record_error(
                        str(first["operation_id"]),
                        token,
                        error_code="transport_unavailable",
                    )
                    # Mature the scheduled backoff deterministically, without changing lease identity.
                    await connection.execute(
                        update(memory_deliveries)
                        .where(
                            memory_deliveries.c.operation_id == first["operation_id"],
                        )
                        .values(next_attempt_at=func.now())
                    )
            assert await claim(db, owner, str(uuid4())) is None
            with pytest.raises(OptimisticLockError):
                async with db.begin() as connection:
                    await MemoryDeliveryRepository(connection).request_retry(
                        str(first["operation_id"]),
                        bank_id=owner.relationship.bank_id,
                        expected_check_count=0,
                    )
            async with db.begin() as connection:
                repository = MemoryDeliveryRepository(connection)
                retried = await repository.request_retry(
                    str(first["operation_id"]),
                    bank_id=owner.relationship.bank_id,
                    expected_check_count=MAX_RECONCILIATION_ERRORS,
                )
                duplicate = await repository.request_retry(
                    str(first["operation_id"]),
                    bank_id=owner.relationship.bank_id,
                    expected_check_count=MAX_RECONCILIATION_ERRORS,
                )
                assert (
                    retried["operation_id"]
                    == duplicate["operation_id"]
                    == first["operation_id"]
                )
                assert retried["payload"] == first["payload"]
            assert (await claim(db, owner, str(uuid4())))["operation_id"] == first[
                "operation_id"
            ]
        finally:
            await db.dispose()

    asyncio.run(scenario())


def test_bank_initialization_is_fenced_and_missing_established_bank_is_not_new():
    async def scenario():
        db = engine()
        try:
            async with db.begin() as connection:
                owner = await scope(connection)
                await MemoryRelationshipRepository(connection).ensure(
                    owner.relationship
                )
            old, new = str(uuid4()), str(uuid4())
            kwargs = {
                "workspace_id": owner.relationship.workspace_id,
                "lease_seconds": 30,
            }
            async with db.begin() as connection:
                repository = MemoryRelationshipRepository(connection)
                assert await repository.claim_initialization(
                    owner.relationship.bank_id, token=old, **kwargs
                )
                assert (
                    await repository.claim_initialization(
                        owner.relationship.bank_id, token=new, **kwargs
                    )
                    is None
                )
                await connection.execute(
                    update(memory_relationships)
                    .where(
                        memory_relationships.c.bank_id == owner.relationship.bank_id,
                    )
                    .values(initialization_expires_at=func.now() - timedelta(seconds=1))
                )
            async with db.begin() as connection:
                assert await MemoryRelationshipRepository(
                    connection
                ).claim_initialization(owner.relationship.bank_id, token=new, **kwargs)
            with pytest.raises(LeaseUnavailableError):
                async with db.begin() as connection:
                    await MemoryRelationshipRepository(
                        connection
                    ).finish_initialization(
                        owner.relationship.bank_id,
                        workspace_id=owner.relationship.workspace_id,
                        token=old,
                        state="ready",
                    )
            async with db.begin() as connection:
                repository = MemoryRelationshipRepository(connection)
                await repository.finish_initialization(
                    owner.relationship.bank_id,
                    workspace_id=owner.relationship.workspace_id,
                    token=new,
                    state="ready",
                )
                await repository.mark_missing(
                    owner.relationship.bank_id,
                    workspace_id=owner.relationship.workspace_id,
                )
                assert (
                    await repository.claim_initialization(
                        owner.relationship.bank_id, token=str(uuid4()), **kwargs
                    )
                    is None
                )
                row = await repository.get(
                    owner.relationship.bank_id,
                    workspace_id=owner.relationship.workspace_id,
                )
                assert row["state"] == "missing" and row["initialized_at"] is not None
        finally:
            await db.dispose()

    asyncio.run(scenario())
