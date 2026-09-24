"""A real two-connection regression for admission/finalization row order."""

from __future__ import annotations

import asyncio
import os
import re
from uuid import uuid4

import pytest
from sqlalchemy import insert, text
from sqlalchemy.engine import make_url

from ade_api.features.agent_runtime.persistence.conversations import (
    ConversationRepository,
)
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.memory import MemoryRepository
from ade_api.features.agent_runtime.persistence.metadata import (
    conversations,
    memory_subjects,
)
from ade_api.features.agent_runtime.worker_finalization import (
    _lock_conversation_and_subject,
)

DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="ADE_TEST_DATABASE_URL must point at a disposable PostgreSQL test database",
)


def test_admission_and_finalization_do_not_deadlock_when_subject_id_sorts_first(
    seed_m2_memory_resources,
) -> None:
    assert DATABASE_URL is not None
    url = make_url(DATABASE_URL)
    assert url.drivername == "postgresql+psycopg"
    assert url.host in {"localhost", "127.0.0.1", "::1"}
    assert url.username == "ade_owner" and url.password is None
    assert url.database is not None
    assert re.fullmatch(r"ade_m2_memory_test_[0-9a-f]{8,}", url.database)

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        subject_id = f"00000000-0000-0000-0000-{uuid4().hex[-12:]}"
        conversation_id = f"ffffffff-ffff-ffff-ffff-{uuid4().hex[-12:]}"
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                await connection.execute(
                    insert(memory_subjects).values(
                        id=subject_id,
                        workspace_id=ids["workspace"],
                        external_key=f"lock-order-{subject_id}",
                        display_name="Lock order subject",
                    )
                )
                await connection.execute(
                    insert(conversations).values(
                        id=conversation_id,
                        workspace_id=ids["workspace"],
                        agent_definition_version_id=ids["definition_version"],
                        memory_subject_id=subject_id,
                    )
                )

            blocked_pid: int | None = None
            holder_locked = asyncio.Event()

            async def holder() -> None:
                async with engine.begin() as connection:
                    await connection.execute(text("SET LOCAL lock_timeout = '1500ms'"))
                    await ConversationRepository(connection).get_for_update(
                        conversation_id
                    )
                    holder_locked.set()
                    await waiter_started.wait()
                    await waiter_blocked.wait()
                    await MemoryRepository(connection).lock_subject(subject_id)

            waiter_started = asyncio.Event()
            waiter_blocked = asyncio.Event()

            async def waiter() -> None:
                nonlocal blocked_pid
                await holder_locked.wait()
                async with engine.begin() as connection:
                    blocked_pid = int(
                        await connection.scalar(text("SELECT pg_backend_pid()"))
                    )
                    waiter_started.set()
                    await _lock_conversation_and_subject(
                        ConversationRepository(connection),
                        MemoryRepository(connection),
                        conversation_id,
                        subject_id,
                    )

            async def observe_waiter_lock() -> None:
                await waiter_started.wait()
                async with engine.connect() as connection:
                    for _ in range(40):
                        waiting = await connection.scalar(
                            text(
                                "SELECT wait_event_type = 'Lock' FROM pg_stat_activity "
                                "WHERE pid = :pid"
                            ),
                            {"pid": blocked_pid},
                        )
                        if waiting:
                            waiter_blocked.set()
                            return
                        await asyncio.sleep(0.05)
                raise AssertionError(
                    "finalization never reached a PostgreSQL lock wait"
                )

            async with asyncio.timeout(5):
                await asyncio.gather(holder(), waiter(), observe_waiter_lock())
        finally:
            await engine.dispose()

    asyncio.run(scenario())
