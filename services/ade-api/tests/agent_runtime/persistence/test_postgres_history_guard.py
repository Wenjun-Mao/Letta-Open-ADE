"""Fresh H authorization checks against committed disposable PostgreSQL rows."""

from __future__ import annotations

import asyncio
import os
import time

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import SQLAlchemyError

import ade_api.features.agent_runtime.turn_memory_snapshot as snapshot_module
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.history_native_rank import (
    HISTORY_EMBEDDING_ROUTE,
    rank_native_history,
)
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.history_guard import (
    validate_admitted_history,
    validate_history_before_dispatch,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    conversations,
    memory_subjects,
    messages,
)
from ade_api.features.agent_runtime.turn_memory_snapshot import load_turn_state
from workflows.evals.character_memory_dev.history_reader_test_support import (
    assistant,
    require_disposable_database_url,
    turn,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="disposable PostgreSQL history test database required"
)


def test_native_embedding_rechecks_frozen_postgres_source_before_query(
    seed_m2_memory_resources,
) -> None:
    assert DATABASE_URL is not None
    require_disposable_database_url(DATABASE_URL)

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                old = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "早上喝咖啡。",
                )
                old_assistant_id = await assistant(
                    connection, ids["workspace"], ids["conversation_one"], old
                )
                current = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_two"],
                    "你记得吗？",
                    status="pending",
                )
            snapshot = await load_turn_state(
                engine,
                {
                    "id": current["run_id"],
                    "conversation_id": ids["conversation_two"],
                    "accepted_memory_generation": 1,
                },
                include_history=True,
            )
            held = snapshot["history"]["exchanges"]
            assert len(held) == 1
            guard_calls = 0
            embedding_calls = 0

            async def authorize(exchanges):
                nonlocal guard_calls
                guard_calls += 1
                async with engine.connect() as connection:
                    return await validate_history_before_dispatch(
                        connection,
                        exchanges=exchanges,
                        workspace_id=ids["workspace"],
                        subject_id=ids["subject_one"],
                        purpose="development",
                        definition_root_id=ids["definition"],
                        current_run_id=current["run_id"],
                        accepted_memory_generation=1,
                    )

            class Embeddings:
                async def embed(self, *, model_key, inputs, timeout_seconds):
                    nonlocal embedding_calls
                    embedding_calls += 1
                    assert model_key == HISTORY_EMBEDDING_ROUTE
                    assert len(inputs) == 1
                    async with engine.begin() as connection:
                        await connection.execute(
                            delete(messages).where(messages.c.id == old_assistant_id)
                        )
                    return [[1.0] * 1024]

            with pytest.raises(RuntimeValidationError) as loss:
                await rank_native_history(
                    exchanges=held,
                    current_user="你记得吗？",
                    local_suffix=[],
                    recipe="probe_local_qwen_cosine",
                    embeddings=Embeddings(),
                    model_key=HISTORY_EMBEDDING_ROUTE,
                    deadline=time.monotonic() + 30,
                    authorize_sources=authorize,
                    mark_exposed=lambda: None,
                )
            assert loss.value.detail_code == "natural_history_missing"
            assert (guard_calls, embedding_calls) == (2, 1)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_native_embedding_rejects_stale_generation_before_any_dispatch(
    seed_m2_memory_resources,
) -> None:
    assert DATABASE_URL is not None
    require_disposable_database_url(DATABASE_URL)

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                old = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "早上喝咖啡。",
                )
                await assistant(
                    connection, ids["workspace"], ids["conversation_one"], old
                )
                current = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_two"],
                    "你记得吗？",
                    status="pending",
                )
            state = await load_turn_state(
                engine,
                {
                    "id": current["run_id"],
                    "conversation_id": ids["conversation_two"],
                    "accepted_memory_generation": 1,
                },
                include_history=True,
            )
            async with engine.begin() as connection:
                await connection.execute(
                    update(memory_subjects)
                    .where(memory_subjects.c.id == ids["subject_one"])
                    .values(memory_generation=2)
                )
            dispatches = 0

            async def authorize(exchanges):
                async with engine.connect() as connection:
                    return await validate_history_before_dispatch(
                        connection,
                        exchanges=exchanges,
                        workspace_id=ids["workspace"],
                        subject_id=ids["subject_one"],
                        purpose="development",
                        definition_root_id=ids["definition"],
                        current_run_id=current["run_id"],
                        accepted_memory_generation=1,
                    )

            class Embeddings:
                async def embed(self, *, model_key, inputs, timeout_seconds):
                    nonlocal dispatches
                    dispatches += 1
                    return [[1.0] * 1024]

            with pytest.raises(RuntimeValidationError) as stale:
                await rank_native_history(
                    exchanges=state["history"]["exchanges"],
                    current_user="你记得吗？",
                    local_suffix=[],
                    recipe="probe_local_qwen_cosine",
                    embeddings=Embeddings(),
                    model_key=HISTORY_EMBEDDING_ROUTE,
                    deadline=time.monotonic() + 30,
                    authorize_sources=authorize,
                    mark_exposed=lambda: None,
                )
            assert stale.value.detail_code == "natural_history_stale_generation"
            assert dispatches == 0
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_fresh_guard_allows_archive_but_rejects_hash_scope_and_purge(
    seed_m2_memory_resources,
) -> None:
    assert DATABASE_URL is not None
    require_disposable_database_url(DATABASE_URL)

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                old = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "早上喝咖啡。",
                )
                old_assistant_id = await assistant(
                    connection, ids["workspace"], ids["conversation_one"], old
                )
                current = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_two"],
                    "你记得吗？",
                    status="pending",
                )
            state = await load_turn_state(
                engine,
                {
                    "id": current["run_id"],
                    "conversation_id": ids["conversation_two"],
                    "accepted_memory_generation": 1,
                },
                include_history=True,
            )
            held = state["history"]["exchanges"]
            assert len(held) == 1

            async def check() -> set[str]:
                async with engine.connect() as connection:
                    return await validate_admitted_history(
                        connection,
                        exchanges=held,
                        workspace_id=ids["workspace"],
                        subject_id=ids["subject_one"],
                        purpose="development",
                        definition_root_id=ids["definition"],
                        current_run_id=current["run_id"],
                    )

            assert await check() == set()
            async with engine.begin() as connection:
                await connection.execute(
                    update(conversations)
                    .where(conversations.c.id == ids["conversation_one"])
                    .values(archived_at="2026-01-01T00:00:00Z")
                )
            assert await check() == set()
            async with engine.begin() as connection:
                await connection.execute(
                    update(messages)
                    .where(messages.c.id == old["user_id"])
                    .values(content="篡改")
                )
            with pytest.raises(RuntimeValidationError) as altered:
                await check()
            assert altered.value.detail_code == "natural_history_integrity"
            async with engine.begin() as connection:
                await connection.execute(
                    update(messages)
                    .where(messages.c.id == old["user_id"])
                    .values(content="早上喝咖啡。")
                )
                await connection.execute(
                    update(conversations)
                    .where(conversations.c.id == ids["conversation_one"])
                    .values(memory_subject_id=ids["subject_two"])
                )
            with pytest.raises(RuntimeValidationError) as cross_subject:
                await check()
            assert cross_subject.value.detail_code == "natural_history_integrity"
            async with engine.begin() as connection:
                await connection.execute(
                    update(conversations)
                    .where(conversations.c.id == ids["conversation_one"])
                    .values(memory_subject_id=ids["subject_one"])
                )
                await connection.execute(
                    delete(messages).where(messages.c.id == old_assistant_id)
                )
            assert await check() == {old["run_id"]}
            async with engine.begin() as connection:
                await connection.execute(
                    update(messages)
                    .where(messages.c.id == old["user_id"])
                    .values(content="altered while sibling is purged")
                )
            with pytest.raises(RuntimeValidationError) as partial:
                await check()
            assert partial.value.detail_code == "natural_history_integrity"
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_optional_history_reader_error_preserves_mandatory_rr_state(
    seed_m2_memory_resources, monkeypatch
) -> None:
    assert DATABASE_URL is not None
    require_disposable_database_url(DATABASE_URL)

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                current = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_two"],
                    "What did I say?",
                    status="pending",
                )

            async def unavailable(*args, **kwargs):
                raise SQLAlchemyError("optional reader unavailable")

            monkeypatch.setattr(snapshot_module, "read_history_corpus", unavailable)
            state = await load_turn_state(
                engine,
                {
                    "id": current["run_id"],
                    "conversation_id": ids["conversation_two"],
                    "accepted_memory_generation": 1,
                },
                include_history=True,
            )
            assert state["history"] == {"exchanges": [], "unavailable": True}
            assert state["conversation"]["id"] == ids["conversation_two"]
            assert state["subject"]["id"] == ids["subject_one"]
        finally:
            await engine.dispose()

    asyncio.run(scenario())
