"""Two-connection regression for the current conversation-before-run lock contract."""

import asyncio

import pytest
from sqlalchemy import text

from ade_api.features.agent_runtime.persistence.conversations import (
    ConversationRepository,
)
from ade_api.features.agent_runtime.persistence.run_lifecycle import lock_run
from ade_api.features.agent_runtime.persistence.runs import RunRepository

from .hindsight_support import DATABASE_URL, engine, message, scope


pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Disposable Hindsight PostgreSQL fixture not configured"
)


def test_lifecycle_waits_for_conversation_without_holding_the_run_lock():
    asyncio.run(_lock_order())


async def _lock_order():
    db = engine()
    try:
        async with db.begin() as connection:
            owner = await scope(connection)
            _, run_id = await message(connection, owner)
        holder_locked, waiter_started, waiter_blocked = (
            asyncio.Event(),
            asyncio.Event(),
            asyncio.Event(),
        )
        pid = None

        async def holder():
            async with db.begin() as connection:
                await connection.execute(text("SET LOCAL lock_timeout = '1500ms'"))
                await ConversationRepository(connection).get_for_update(
                    str(owner.conversation["id"])
                )
                holder_locked.set()
                await waiter_blocked.wait()
                # If finalization/Retry had locked run first, this would deadlock.
                await RunRepository(connection).get_for_update(run_id)

        async def waiter():
            nonlocal pid
            await holder_locked.wait()
            async with db.begin() as connection:
                pid = int(await connection.scalar(text("SELECT pg_backend_pid()")))
                waiter_started.set()
                await lock_run(connection, run_id)

        async def observe():
            await waiter_started.wait()
            async with db.connect() as connection:
                for _ in range(40):
                    if await connection.scalar(
                        text(
                            "SELECT wait_event_type = 'Lock' FROM pg_stat_activity WHERE pid = :pid"
                        ),
                        {"pid": pid},
                    ):
                        waiter_blocked.set()
                        return
                    await asyncio.sleep(0.05)
            raise AssertionError("Lifecycle did not reach a PostgreSQL row-lock wait")

        async with asyncio.timeout(5):
            await asyncio.gather(holder(), waiter(), observe())
    finally:
        await db.dispose()
