"""Full scoped rows, coherent snapshots and honest bounded reader inventories."""

import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import event, insert, select, text, update

import ade_api.features.agent_runtime.persistence.evaluation_observations as observations
import ade_api.features.agent_runtime.persistence.history as history
import ade_api.features.agent_runtime.persistence.history_lineage as lineage
import ade_api.features.agent_runtime.turn_memory_snapshot as snapshots
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    agent_definitions,
    agent_definition_versions,
    conversations,
    memory_entities,
    memory_facts,
    memory_revision_predecessors,
    memory_revisions,
    memory_subjects,
    runs,
)
from workflows.evals.character_memory_dev.history_reader_test_support import (
    action,
    assistant,
    fact,
    turn,
)
from .story_continuity_support import full_state, require_owned_database

DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="fresh disposable PostgreSQL required"
)


async def seed(connection, seed_resources):
    ids = await seed_resources(connection)
    for table in (
        agent_definitions,
        agent_definition_versions,
        conversations,
        memory_subjects,
    ):
        await connection.execute(
            update(table)
            .where(table.c.workspace_id == ids["workspace"])
            .values(purpose="evaluation")
        )
    await connection.execute(
        update(agent_definition_versions)
        .where(agent_definition_versions.c.id == ids["definition_version"])
        .values(memory_policy_version="natural-user-assertions-v4-b-history-probe")
    )
    origins = []
    for sequence in (1, 3):
        origin = await turn(
            connection,
            ids["workspace"],
            ids["conversation_one"],
            "A visible source.",
            sequence=sequence,
        )
        await assistant(connection, ids["workspace"], ids["conversation_one"], origin)
        origins.append(origin)
    fact_id, revision_id = await fact(
        connection,
        ids,
        source_id=origins[0]["user_id"],
        source_run_id=origins[0]["run_id"],
        content="A visible source.",
    )
    successor = str(uuid4())
    await connection.execute(
        insert(memory_revisions).values(
            id=successor,
            fact_id=fact_id,
            workspace_id=ids["workspace"],
            subject_id=ids["subject_one"],
            operation="revise",
            fact_version=2,
            value={"recorded": "past value"},
            action_id=await action(connection, ids),
            reason="ended",
        )
    )
    await connection.execute(
        insert(memory_revision_predecessors).values(
            revision_id=successor, predecessor_revision_id=revision_id
        )
    )
    await connection.execute(
        update(memory_facts)
        .where(memory_facts.c.id == fact_id)
        .values(status="inactive", version=2, current_revision_id=successor)
    )
    orphan = str(uuid4())
    await connection.execute(
        insert(memory_entities).values(
            id=orphan,
            workspace_id=ids["workspace"],
            subject_id=ids["subject_one"],
            kind="pet",
            label="unassociated",
        )
    )
    foreign = await turn(
        connection, ids["workspace"], ids["other_conversation"], "FOREIGN_SECRET"
    )
    await assistant(
        connection,
        ids["workspace"],
        ids["other_conversation"],
        foreign,
        text="FOREIGN_ASSISTANT",
    )
    await fact(
        connection,
        {**ids, "subject_one": ids["subject_two"]},
        source_id=foreign["user_id"],
        source_run_id=foreign["run_id"],
        content="FOREIGN_SECRET",
    )
    current = await turn(
        connection,
        ids["workspace"],
        ids["conversation_two"],
        "Recall?",
        status="running",
    )
    await connection.execute(
        update(runs).where(runs.c.id == current["run_id"]).values(attempt_count=1)
    )
    run = dict(
        (await connection.execute(select(runs).where(runs.c.id == current["run_id"])))
        .mappings()
        .one()
    )
    return ids, origins, orphan, run


async def load(engine, run):
    return await snapshots.load_turn_state(
        engine,
        run,
        include_history=True,
        capture_database_url=DATABASE_URL,
        runtime_mode="development",
    )


def test_full_readback_includes_inactive_orphan_lineage_without_foreign_sources(
    seed_m2_memory_resources, monkeypatch
):
    assert DATABASE_URL
    require_owned_database(DATABASE_URL)
    monkeypatch.setenv("ADE_NATURAL_MEMORY_CAPTURE", "1")

    async def scenario():
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids, origins, orphan, run = await seed(
                    connection, seed_m2_memory_resources
                )
            state = await load(engine, run)
            observed = state["persistence_before"]
            assert observed["state"] == await full_state(engine, ids["subject_one"])
            assert observed["state"]["facts"][0]["status"] == "inactive"
            assert orphan in {row["id"] for row in observed["state"]["entities"]}
            assert len(observed["state"]["revisions"]) == 2
            assert len(observed["state"]["predecessors"]) == 1
            assert observed["state"]["sources"][0]["authority_role"] == "user_assertion"
            assert "FOREIGN" not in str(state)
            assert state["history"]["inventory"]["status"] == "complete"
            assert {
                row["run_id"] for row in state["history"]["inventory"]["candidates"]
            } == {row["run_id"] for row in origins}
            # Disabled capture executes precisely the same SQL as the old reader.
            monkeypatch.setenv("ADE_NATURAL_MEMORY_CAPTURE", "0")
            statements = []

            def record(_conn, _cursor, statement, _parameters, _context, _many):
                statements.append(statement)

            event.listen(engine.sync_engine, "before_cursor_execute", record)
            await snapshots.load_turn_state(engine, run, include_history=True)
            baseline = list(statements)
            statements.clear()
            disabled = await load(engine, run)
            assert statements == baseline
            assert "persistence_before" not in disabled
            assert "inventory" not in disabled["history"]
            event.remove(engine.sync_engine, "before_cursor_execute", record)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["capacity", "content", "annotation", "unavailable"])
def test_reader_omissions_remain_bounded_and_identified(
    seed_m2_memory_resources, monkeypatch, mode
):
    assert DATABASE_URL
    require_owned_database(DATABASE_URL)
    monkeypatch.setenv("ADE_NATURAL_MEMORY_CAPTURE", "1")
    if mode == "content":
        monkeypatch.setattr(history, "MAX_MESSAGE_CHARS", 5)
    if mode == "annotation":
        monkeypatch.setattr(lineage, "MAX_LINKS_PER_EXCHANGE", 0)
    if mode == "unavailable":

        async def fail(connection, **_kwargs):
            await connection.execute(text("SELECT nonexistent_pc11_history_column"))

        monkeypatch.setattr(snapshots, "read_history_corpus", fail)

    async def scenario():
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids, origins, _orphan, run = await seed(
                    connection, seed_m2_memory_resources
                )
                if mode == "capacity":
                    # Cross the real 128-exchange bound, not a reduced test limit.
                    for sequence in range(5, 259, 2):
                        extra = await turn(
                            connection,
                            ids["workspace"],
                            ids["conversation_one"],
                            "Another source.",
                            sequence=sequence,
                        )
                        await assistant(
                            connection, ids["workspace"], ids["conversation_one"], extra
                        )
                        origins.append(extra)
            state = await load(engine, run)
            assert state["persistence_before"]["status"] == "complete"
            reader = state["history"]
            if mode == "unavailable":
                assert reader == {"exchanges": [], "unavailable": True}
                return
            inventory = reader["inventory"]
            assert inventory["status"] == (
                "truncated" if mode == "capacity" else "complete"
            )
            reasons = {row["run_id"]: row["reason"] for row in inventory["candidates"]}
            assert set(reasons) == {row["run_id"] for row in origins}
            if mode == "capacity":
                assert len(reasons) == 129
                assert list(reasons.values()).count("eligible") == 128
                assert list(reasons.values()).count("reader_capacity") == 1
                assert inventory["limit"] == 128
                assert reader["omitted"]["capacity_at_least"] == 1
            elif mode == "content":
                assert list(reasons.values()) == ["content", "content"]
                assert reader["omitted"]["content"] == 2
            else:
                assert reasons[origins[0]["run_id"]] == "annotation"
                assert reader["omitted"]["annotation"] == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_before_snapshot_is_coherent_and_later_concurrent_changes_are_not_isolated(
    seed_m2_memory_resources, monkeypatch
):
    assert DATABASE_URL
    require_owned_database(DATABASE_URL)
    monkeypatch.setenv("ADE_NATURAL_MEMORY_CAPTURE", "1")

    async def scenario():
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids, origins, _orphan, run = await seed(
                    connection, seed_m2_memory_resources
                )
            original = observations.read_snapshot
            late_orphan, late_run = str(uuid4()), None

            async def late_commit(connection, *, binding):
                nonlocal late_run
                # Mandatory state has already established the RR snapshot.
                async with engine.begin() as writer:
                    await writer.execute(
                        insert(memory_entities).values(
                            id=late_orphan,
                            workspace_id=ids["workspace"],
                            subject_id=ids["subject_one"],
                            kind="pet",
                            label="late orphan",
                        )
                    )
                    late = await turn(
                        writer,
                        ids["workspace"],
                        ids["conversation_one"],
                        "Late dialogue.",
                        sequence=5,
                    )
                    await assistant(
                        writer, ids["workspace"], ids["conversation_one"], late
                    )
                    late_run = late["run_id"]
                return await original(connection, binding=binding)

            monkeypatch.setattr(observations, "read_snapshot", late_commit)
            state = await load(engine, run)
            before = state["persistence_before"]
            assert late_orphan not in {row["id"] for row in before["state"]["entities"]}
            assert {
                row["run_id"] for row in state["history"]["inventory"]["candidates"]
            } == {row["run_id"] for row in origins}
            monkeypatch.setattr(observations, "read_snapshot", original)
            async with engine.connect() as connection:
                await connection.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                )
                after = await observations.observe_snapshot(
                    connection, binding=state["observation_binding"]
                )
            assert late_orphan in {row["id"] for row in after["state"]["entities"]}
            assert late_run in {row["id"] for row in after["subject_run_activity"]}
            assert (
                observations.isolation_status(
                    before, after, run_id=str(run["id"]), attempt=1
                )
                == "overlapping_activity"
            )
            assert before["state"] != after["state"]
        finally:
            await engine.dispose()

    asyncio.run(scenario())
