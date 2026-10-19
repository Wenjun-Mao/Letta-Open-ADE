"""Real-SQL delivery through a recording native substitute; no provider traffic."""

import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import func, update

from ade_api.features.agent_runtime.memory_delivery_worker import MemoryDeliveryWorker
from ade_api.features.agent_runtime.memory_banks import (
    MemoryBankAccess,
    MemoryBankError,
)
from ade_api.features.agent_runtime.persistence.memory_deliveries import (
    MemoryDeliveryRepository,
)
from ade_api.features.agent_runtime.persistence.memory_relationships import (
    MemoryRelationshipRepository,
)
from ade_api.features.agent_runtime.persistence.metadata import memory_deliveries

from .hindsight_native_fake import NativeDeliveryFake
from .hindsight_support import DATABASE_URL, engine, message, scope


pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Disposable ADE_TEST_DATABASE_URL is required"
)


async def prepare(db):
    async with db.begin() as connection:
        owner = await scope(connection)
        source, _ = await message(connection, owner)
        delivery = await MemoryDeliveryRepository(connection).enqueue(source)
    return owner, source, delivery


async def mature(db, operation):
    async with db.begin() as connection:
        await connection.execute(
            update(memory_deliveries)
            .where(
                memory_deliveries.c.operation_id == operation,
            )
            .values(next_attempt_at=func.now())
        )


async def current(db, owner, operation):
    async with db.connect() as connection:
        return await MemoryDeliveryRepository(connection).get(
            str(operation), bank_id=owner.relationship.bank_id
        )


@pytest.mark.parametrize("lost_ack", [False, True])
def test_dispatch_and_reconciliation_never_hold_sql_locks_or_resubmit_accepted_work(
    lost_ack,
):
    async def scenario():
        db = engine()
        try:
            owner, source, delivery = await prepare(db)
            native = NativeDeliveryFake(db)
            native.lose_ack = lost_ack
            worker = MemoryDeliveryWorker(
                engine=db, client=native, workspace_id=owner.relationship.workspace_id
            )
            assert await worker.process_once()
            first = await current(db, owner, delivery["operation_id"])
            assert first["status"] == ("uncertain" if lost_ack else "processing")
            await mature(db, delivery["operation_id"])
            assert await worker.process_once()
            final = await current(db, owner, delivery["operation_id"])
            assert final["status"] == "retained"
            assert final["accepted_via"] == (
                "reconciliation" if lost_ack else "response"
            )
            assert final["attempt_count"] == 1 and final["check_count"] == 2
            assert native.submissions == [
                (str(delivery["operation_id"]), bytes(delivery["payload"]))
            ]
            assert native.network_checks >= 7
            assert native.creations == [owner.relationship.bank_id]
        finally:
            await db.dispose()

    asyncio.run(scenario())


def test_native_failure_waits_for_delivery_retry_and_keeps_the_original_operation():
    async def scenario():
        db = engine()
        try:
            owner, source, delivery = await prepare(db)
            native = NativeDeliveryFake(db)
            native.initial_status = "failed"
            worker = MemoryDeliveryWorker(
                engine=db, client=native, workspace_id=owner.relationship.workspace_id
            )
            await worker.process_once()
            await mature(db, delivery["operation_id"])
            await worker.process_once()
            failed = await current(db, owner, delivery["operation_id"])
            assert failed["status"] == "failed"
            assert await worker.process_once() is False
            assert native.retries == []
            async with db.begin() as connection:
                await MemoryDeliveryRepository(connection).request_retry(
                    str(delivery["operation_id"]),
                    bank_id=owner.relationship.bank_id,
                    expected_check_count=int(failed["check_count"]),
                )
            await worker.process_once()
            await mature(db, delivery["operation_id"])
            await worker.process_once()
            final = await current(db, owner, delivery["operation_id"])
            assert final["status"] == "retained"
            assert native.retries == [str(delivery["operation_id"])]
            assert (
                len(native.submissions) == 1 and final["payload"] == delivery["payload"]
            )
        finally:
            await db.dispose()

    asyncio.run(scenario())


@pytest.mark.parametrize("fault", ["missing_bank", "changed_source"])
def test_remote_loss_or_source_rewrite_is_not_successful_empty_memory(fault):
    async def scenario():
        db = engine()
        try:
            owner, _, delivery = await prepare(db)
            native = NativeDeliveryFake(db)
            worker = MemoryDeliveryWorker(
                engine=db, client=native, workspace_id=owner.relationship.workspace_id
            )
            await worker.process_once()
            if fault == "missing_bank":
                native.configurations.clear()
            else:
                native.corrupt_document = True
            await mature(db, delivery["operation_id"])
            await worker.process_once()
            failed = await current(db, owner, delivery["operation_id"])
            assert failed["status"] == "failed"
            assert failed["retained_at"] is None
            assert len(native.creations) == 1
            if fault == "missing_bank":
                async with db.connect() as connection:
                    bank = await MemoryRelationshipRepository(connection).get(
                        owner.relationship.bank_id,
                        workspace_id=owner.relationship.workspace_id,
                    )
                    assert bank["state"] == "missing"
        finally:
            await db.dispose()

    asyncio.run(scenario())


def test_stale_worker_cannot_overwrite_reconciled_completion():
    async def scenario():
        db = engine()
        try:
            owner, _, delivery = await prepare(db)
            native = NativeDeliveryFake(db)
            native.submission_started, native.release_submission = (
                asyncio.Event(),
                asyncio.Event(),
            )
            worker = MemoryDeliveryWorker(
                engine=db, client=native, workspace_id=owner.relationship.workspace_id
            )
            old = asyncio.create_task(worker.process_once())
            async with asyncio.timeout(5):
                await native.submission_started.wait()
                async with db.begin() as connection:
                    await connection.execute(
                        update(memory_deliveries)
                        .where(
                            memory_deliveries.c.operation_id
                            == delivery["operation_id"],
                        )
                        .values(lease_expires_at=func.now() - timedelta(seconds=1))
                    )
                assert await worker.process_once()
                assert (await current(db, owner, delivery["operation_id"]))[
                    "status"
                ] == "retained"
                native.release_submission.set()
                await old
            final = await current(db, owner, delivery["operation_id"])
            assert final["status"] == "retained" and final["check_count"] == 2
            assert len(native.submissions) == 1
        finally:
            await db.dispose()

    asyncio.run(scenario())


@pytest.mark.parametrize("populated", [False, True])
def test_interrupted_bank_creation_reconciles_only_a_verified_empty_bank(populated):
    async def scenario():
        import time

        db = engine()
        try:
            owner, _, delivery = await prepare(db)
            native = NativeDeliveryFake(db)
            native.configurations[owner.relationship.bank_id] = {}
            if populated:
                original = native.statistics

                async def nonempty(bank):
                    return {**await original(bank), "total_documents": 1}

                native.statistics = nonempty
            access = MemoryBankAccess(
                engine=db, client=native, workspace_id=owner.relationship.workspace_id
            )
            if populated:
                with pytest.raises(MemoryBankError, match="not_empty"):
                    await access.ensure_ready(
                        owner.relationship.bank_id, deadline=time.monotonic() + 5
                    )
            else:
                assert (
                    await access.ensure_ready(
                        owner.relationship.bank_id, deadline=time.monotonic() + 5
                    )
                )["state"] == "ready"
            assert native.creations == []
            assert native.submissions == []
        finally:
            await db.dispose()

    asyncio.run(scenario())
