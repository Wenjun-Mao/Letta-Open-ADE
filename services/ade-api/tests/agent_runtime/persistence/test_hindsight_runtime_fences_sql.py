"""Actual worker orchestration races with controlled network/lease failures."""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, update

from ade_api.features.agent_runtime.contracts import AcceptTurnRequest, RetryRunRequest
from ade_api.features.agent_runtime.errors import RuntimeConflict
from ade_api.features.agent_runtime.persistence.conversations import (
    ConversationRepository,
)
from ade_api.features.agent_runtime.persistence.leases import (
    ConversationLeaseRepository,
)
from ade_api.features.agent_runtime.persistence.memory_deliveries import (
    MemoryDeliveryRepository,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    conversation_leases,
    conversations,
)

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


def test_cancellation_during_lookup_preserves_input_and_delivery():
    asyncio.run(_cancel_lookup())


async def _cancel_lookup():
    db = engine()
    try:
        owner, service, worker, native, transport = await runtime(db)
        native.recall_started, native.release_recall = asyncio.Event(), asyncio.Event()
        accepted = await service.accept_turn(
            str(owner.conversation["id"]),
            AcceptTurnRequest(content="Saved input", idempotency_key=uuid4().hex),
        )
        task = asyncio.create_task(worker.process_once())
        await asyncio.wait_for(native.recall_started.wait(), timeout=2)
        await service.cancel_run(accepted["run_id"])
        await asyncio.wait_for(task, timeout=2)
        assert (await service.get_run(accepted["run_id"]))["status"] == "cancelled"
        assert not transport.requests
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
            assert not await ConversationLeaseRepository(connection).get_active(
                str(owner.conversation["id"])
            )
    finally:
        await db.dispose()


def test_stale_worker_cannot_commit_its_candidate_or_delivery():
    asyncio.run(_stale_worker())


async def _stale_worker():
    db = engine()
    try:
        owner, service, worker, _, transport = await runtime(db)
        transport.started, transport.release = asyncio.Event(), asyncio.Event()
        accepted = await service.accept_turn(
            str(owner.conversation["id"]),
            AcceptTurnRequest(content="Saved input", idempotency_key=uuid4().hex),
        )
        task = asyncio.create_task(worker.process_once())
        await asyncio.wait_for(transport.started.wait(), timeout=2)
        async with db.begin() as connection:
            await connection.execute(
                update(conversation_leases)
                .where(conversation_leases.c.run_id == accepted["run_id"])
                .values(expires_at=func.now() - timedelta(seconds=1))
            )
        claim, handled = await worker.claimer.claim()
        assert claim is None and handled
        transport.release.set()
        await asyncio.wait_for(task, timeout=2)
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


def test_tool_lookup_failure_pauses_and_changed_conversation_rejects_retry():
    asyncio.run(_tool_failure_and_changed_conversation())


async def _tool_failure_and_changed_conversation():
    db = engine()
    try:
        owner, service, worker, native, transport = await runtime(db)
        original = native.recall

        async def fail_tool(bank, payload):
            if native.lookups:
                native.fail_recall = True
            return await original(bank, payload)

        native.recall = fail_tool
        transport.responses = [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {
                                        "name": "search_memory",
                                        "arguments": '{"query":"earlier"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ]
            }
        ]
        accepted = await service.accept_turn(
            str(owner.conversation["id"]),
            AcceptTurnRequest(content="Saved input", idempotency_key=uuid4().hex),
        )
        assert await worker.process_once()
        run = await service.get_run(accepted["run_id"])
        assert run["status"] == "paused" and len(transport.requests) == 1
        async with db.begin() as connection:
            await connection.execute(
                update(conversations)
                .where(conversations.c.id == owner.conversation["id"])
                .values(version=2)
            )
        with pytest.raises(RuntimeConflict, match="compatible"):
            await service.retry_run(
                run["id"],
                RetryRunRequest(idempotency_key=uuid4().hex, expected_attempt_count=1),
            )
        assert (await service.get_run(run["id"]))["status"] == "paused"
        async with db.connect() as connection:
            assert (
                len(
                    await ConversationRepository(connection).list_messages(
                        str(owner.conversation["id"])
                    )
                )
                == 1
            )
            assert not await ConversationLeaseRepository(connection).get_active(
                str(owner.conversation["id"])
            )
    finally:
        await db.dispose()
