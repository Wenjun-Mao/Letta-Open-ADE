"""Current product-path tests, not native Memory or Character qualification."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from ade_api.features.agent_runtime.contracts import AcceptTurnRequest, RetryRunRequest
from ade_api.features.agent_runtime.errors import ConversationBusy, RuntimeConflict
from ade_api.features.agent_runtime.persistence.conversations import (
    ConversationRepository,
)
from ade_api.features.agent_runtime.persistence.memory_deliveries import (
    MemoryDeliveryRepository,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    memory_deliveries,
    memory_facts,
    memory_revisions,
)
from ade_api.features.agent_runtime.persistence.runs import RunRepository

from .hindsight_runtime_support import runtime
from .hindsight_support import DATABASE_URL, engine


pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Disposable Hindsight PostgreSQL fixture not configured"
)


@pytest.fixture(autouse=True)
def controlled_build_identity(monkeypatch):
    # Synthetic presence identity, never a release or actual-source attestation.
    monkeypatch.setenv("ADE_SOURCE_REVISION", "f" * 40)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "true")
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "e" * 64)


def test_acceptance_reply_and_delivery_are_independent_atomic_boundaries():
    asyncio.run(_acceptance_reply_and_delivery())


async def _acceptance_reply_and_delivery():
    db = engine()
    try:
        owner, service, worker, native, transport = await runtime(db)
        request = AcceptTurnRequest(
            content="Original accepted input", idempotency_key=uuid4().hex
        )
        accepted = await service.accept_turn(str(owner.conversation["id"]), request)
        assert (await service.accept_turn(str(owner.conversation["id"]), request))[
            "idempotent_replay"
        ]
        async with db.connect() as connection:
            total, deliveries = await MemoryDeliveryRepository(connection).list(
                owner.relationship.bank_id
            )
            assert total == 1 and deliveries[0]["status"] == "queued"
        assert await worker.process_once()
        assert (await service.get_run(accepted["run_id"]))["status"] == "succeeded"
        assert len(native.lookups) == 1 and not native.submissions
        assert len(transport.requests) == 1
        async with db.connect() as connection:
            messages = await ConversationRepository(connection).list_messages(
                str(owner.conversation["id"])
            )
            total, deliveries = await MemoryDeliveryRepository(connection).list(
                owner.relationship.bank_id
            )
            assert [row["role"] for row in messages] == ["user", "assistant"]
            assert total == 2 and all(row["status"] == "queued" for row in deliveries)
            assert not (
                await connection.execute(
                    select(memory_facts).where(
                        memory_facts.c.subject_id == owner.relationship.subject_id
                    )
                )
            ).all()
            assert not (
                await connection.execute(
                    select(memory_revisions).where(
                        memory_revisions.c.subject_id == owner.relationship.subject_id
                    )
                )
            ).all()
    finally:
        await db.dispose()


def test_recall_failure_pauses_then_concurrent_retry_reuses_one_saved_input():
    asyncio.run(_recall_failure_retry())


async def _recall_failure_retry():
    db = engine()
    try:
        owner, service, worker, native, transport = await runtime(db)
        native.fail_recall = True
        accepted = await service.accept_turn(
            str(owner.conversation["id"]),
            AcceptTurnRequest(
                content="Keep the accepted input",
                idempotency_key=uuid4().hex,
                retry_count=3,
            ),
        )
        assert await worker.process_once()
        run = await service.get_run(accepted["run_id"])
        assert (
            run["status"] == "paused" and run["attempt_count"] == 1 and run["paused_at"]
        )
        assert len(native.lookups) == 1 and not transport.requests
        with pytest.raises(ConversationBusy):
            await service.accept_turn(
                str(owner.conversation["id"]),
                AcceptTurnRequest(
                    content="Cannot overtake", idempotency_key=uuid4().hex
                ),
            )
        request = RetryRunRequest(idempotency_key=uuid4().hex, expected_attempt_count=1)
        first, second = await asyncio.gather(
            service.retry_run(run["id"], request), service.retry_run(run["id"], request)
        )
        assert sorted([first["idempotent_replay"], second["idempotent_replay"]]) == [
            False,
            True,
        ]
        with pytest.raises(RuntimeConflict):
            await service.retry_run(
                run["id"],
                RetryRunRequest(idempotency_key=uuid4().hex, expected_attempt_count=1),
            )
        native.fail_recall = False
        assert await worker.process_once()
        run = await service.get_run(run["id"])
        assert run["status"] == "succeeded" and run["attempt_count"] == 2
        assert len(native.lookups) == 2 and len(transport.requests) == 1
        assert (await service.retry_run(run["id"], request))["idempotent_replay"]
        async with db.connect() as connection:
            messages = await ConversationRepository(connection).list_messages(
                str(owner.conversation["id"])
            )
            assert [row["role"] for row in messages] == ["user", "assistant"]
            assert (
                await MemoryDeliveryRepository(connection).list(
                    owner.relationship.bank_id
                )
            )[0] == 2
    finally:
        await db.dispose()


def test_generation_failure_keeps_user_delivery_and_cancelled_pause_keeps_input():
    asyncio.run(_failed_generation_and_cancel())


async def _failed_generation_and_cancel():
    db = engine()
    try:
        owner, service, worker, native, transport = await runtime(db)
        transport.fail = True
        accepted = await service.accept_turn(
            str(owner.conversation["id"]),
            AcceptTurnRequest(
                content="Retain despite failed reply", idempotency_key=uuid4().hex
            ),
        )
        assert await worker.process_once()
        assert (await service.get_run(accepted["run_id"]))["status"] == "failed"
        assert await worker.delivery_worker.process_once()
        assert len(native.submissions) == 1
        async with db.begin() as connection:
            await connection.execute(
                update(memory_deliveries)
                .where(memory_deliveries.c.bank_id == owner.relationship.bank_id)
                .values(next_attempt_at=func.now())
            )
        assert await worker.delivery_worker.process_once()
        async with db.connect() as connection:
            assert (
                await MemoryDeliveryRepository(connection).list(
                    owner.relationship.bank_id
                )
            )[1][0]["status"] == "retained"
            messages = await ConversationRepository(connection).list_messages(
                str(owner.conversation["id"])
            )
            assert len(messages) == 1 and messages[0]["role"] == "user"
        native.fail_recall = True
        accepted = await service.accept_turn(
            str(owner.conversation["id"]),
            AcceptTurnRequest(
                content="Cancel a paused saved input", idempotency_key=uuid4().hex
            ),
        )
        assert await worker.process_once()
        assert (await service.get_run(accepted["run_id"]))["status"] == "paused"
        assert (await service.cancel_run(accepted["run_id"]))["status"] == "cancelled"
        with pytest.raises(RuntimeConflict):
            await service.retry_run(
                accepted["run_id"],
                RetryRunRequest(idempotency_key=uuid4().hex, expected_attempt_count=1),
            )
        async with db.connect() as connection:
            assert (
                len(
                    await ConversationRepository(connection).list_messages(
                        str(owner.conversation["id"])
                    )
                )
                == 2
            )
            assert (
                await MemoryDeliveryRepository(connection).list(
                    owner.relationship.bank_id
                )
            )[0] == 2
    finally:
        await db.dispose()


def test_reply_and_source_intent_roll_back_together_if_final_delivery_fails(
    monkeypatch,
):
    asyncio.run(_atomic_reply(monkeypatch))


async def _atomic_reply(monkeypatch):
    db = engine()
    try:
        owner, service, worker, _, _ = await runtime(db)
        accepted = await service.accept_turn(
            str(owner.conversation["id"]),
            AcceptTurnRequest(
                content="Accepted user remains", idempotency_key=uuid4().hex
            ),
        )

        async def reject(*args, **kwargs):
            raise RuntimeError("Controlled final intent failure")

        monkeypatch.setattr(
            "ade_api.features.agent_runtime.worker_finalization.enqueue_message", reject
        )
        assert await worker.process_once()
        assert (await service.get_run(accepted["run_id"]))["status"] == "failed"
        async with db.connect() as connection:
            assert (
                len(
                    await ConversationRepository(connection).list_messages(
                        str(owner.conversation["id"])
                    )
                )
                == 1
            )
            assert (
                await MemoryDeliveryRepository(connection).list(
                    owner.relationship.bank_id
                )
            )[0] == 1
    finally:
        await db.dispose()


def test_normal_reply_path_preserves_compaction_prefix_and_provenance():
    asyncio.run(_compaction_provenance())


async def _compaction_provenance():
    db = engine()
    try:
        owner, service, worker, native, transport = await runtime(db)
        for index in range(6):
            accepted = await service.accept_turn(
                str(owner.conversation["id"]),
                AcceptTurnRequest(
                    content=f"Original turn {index}: " + "x" * 3000,
                    idempotency_key=uuid4().hex,
                ),
            )
            assert await worker.process_once()
            assert (await service.get_run(accepted["run_id"]))["status"] == "succeeded"
        async with db.connect() as connection:
            repository = ConversationRepository(connection)
            summary = await repository.latest_summary(str(owner.conversation["id"]))
            assert summary and summary["model_key"] == "fake::character"
            assert summary["provider_request_id"] == "controlled-summary"
            sources = await repository.list_summary_source_message_ids(
                str(summary["id"])
            )
            messages = await repository.list_messages(str(owner.conversation["id"]))
            assert sources == [
                str(row["id"])
                for row in messages
                if int(row["sequence"]) <= int(summary["through_sequence"])
            ]
            assert len(messages) == 12
            assert (
                await MemoryDeliveryRepository(connection).list(
                    owner.relationship.bank_id
                )
            )[0] == 12
        assert len(native.lookups) == 6 and any(
            "response_format" in request for request in transport.requests
        )
    finally:
        await db.dispose()


def test_acceptance_rolls_back_when_delivery_intent_cannot_be_committed(monkeypatch):
    asyncio.run(_atomic_acceptance(monkeypatch))


async def _atomic_acceptance(monkeypatch):
    db = engine()
    try:
        owner, service, _, _, _ = await runtime(db)

        async def reject(*args, **kwargs):
            raise RuntimeError("Controlled outbox contract failure")

        monkeypatch.setattr(
            "ade_api.features.agent_runtime.run_service.enqueue_message", reject
        )
        with pytest.raises(RuntimeError, match="Controlled outbox"):
            await service.accept_turn(
                str(owner.conversation["id"]),
                AcceptTurnRequest(
                    content="Must roll back", idempotency_key=uuid4().hex
                ),
            )
        async with db.connect() as connection:
            assert not await ConversationRepository(connection).list_messages(
                str(owner.conversation["id"])
            )
            assert (
                await RunRepository(connection).list_for_conversation(
                    str(owner.conversation["id"]), limit=10, offset=0
                )
            )[0] == 0
    finally:
        await db.dispose()
