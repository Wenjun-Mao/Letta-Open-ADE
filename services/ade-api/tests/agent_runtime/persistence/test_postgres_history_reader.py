"""Structural history reads against disposable PostgreSQL only."""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import insert, update

import ade_api.features.agent_runtime.turn_memory_snapshot as snapshot_module
import ade_api.features.agent_runtime.persistence.history as history_module
import ade_api.features.agent_runtime.persistence.history_lineage as lineage_module
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    agent_definitions,
    conversations,
    memory_facts,
    memory_revision_predecessors,
    memory_revision_sources,
    memory_revisions,
)
from ade_api.features.agent_runtime.turn_memory_snapshot import load_turn_state
from workflows.evals.character_memory_dev.history_reader_test_support import (
    action,
    assistant,
    conversation,
    fact,
    require_disposable_database_url,
    turn,
    version,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="disposable PostgreSQL history test database required"
)


def test_scope_versions_archive_and_snapshot_membership(
    seed_m2_memory_resources, monkeypatch
) -> None:
    assert DATABASE_URL is not None
    require_disposable_database_url(DATABASE_URL)

    async def scenario():
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                version_two = await version(
                    connection, ids, root_id=ids["definition"], version=2
                )
                await connection.execute(
                    update(conversations)
                    .where(conversations.c.id == ids["conversation_two"])
                    .values(agent_definition_version_id=version_two)
                )
                await connection.execute(
                    update(conversations)
                    .where(conversations.c.id == ids["conversation_one"])
                    .values(archived_at="2026-01-01T00:00:00Z")
                )
                other_root = str(uuid4())
                await connection.execute(
                    insert(agent_definitions).values(
                        id=other_root,
                        workspace_id=ids["workspace"],
                        definition_key=f"other-{other_root[:8]}",
                        name="Other character",
                    )
                )
                other_version = await version(
                    connection, ids, root_id=other_root, version=1
                )
                other_character = await conversation(
                    connection,
                    ids,
                    version_id=other_version,
                    subject_id=ids["subject_one"],
                )
                old = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "Old archived report.",
                )
                await assistant(
                    connection, ids["workspace"], ids["conversation_one"], old
                )
                sibling_conversation = await conversation(
                    connection,
                    ids,
                    version_id=version_two,
                    subject_id=ids["subject_one"],
                )
                sibling = await turn(
                    connection,
                    ids["workspace"],
                    sibling_conversation,
                    "Same local sequence, different chat.",
                )
                await assistant(
                    connection, ids["workspace"], sibling_conversation, sibling
                )
                failed = await turn(
                    connection,
                    ids["workspace"],
                    sibling_conversation,
                    "Rejected candidate.",
                    status="failed",
                    sequence=3,
                )
                await assistant(
                    connection,
                    ids["workspace"],
                    sibling_conversation,
                    failed,
                )
                wrong_purpose = await conversation(
                    connection,
                    ids,
                    version_id=version_two,
                    subject_id=ids["subject_one"],
                    purpose="evaluation",
                )
                purpose_turn = await turn(
                    connection,
                    ids["workspace"],
                    wrong_purpose,
                    "Evaluation-only chat.",
                )
                await assistant(
                    connection, ids["workspace"], wrong_purpose, purpose_turn
                )
                other = await turn(
                    connection,
                    ids["workspace"],
                    other_character,
                    "Private other character.",
                )
                await assistant(connection, ids["workspace"], other_character, other)
                other_workspace = await seed_m2_memory_resources(connection)
                foreign = await turn(
                    connection,
                    other_workspace["workspace"],
                    other_workspace["conversation_one"],
                    "Other workspace.",
                )
                await assistant(
                    connection,
                    other_workspace["workspace"],
                    other_workspace["conversation_one"],
                    foreign,
                )
                isolated = await turn(
                    connection,
                    ids["workspace"],
                    ids["other_conversation"],
                    "Other subject.",
                )
                await assistant(
                    connection, ids["workspace"], ids["other_conversation"], isolated
                )
                incomplete = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "No assistant yet.",
                    sequence=3,
                )
                current = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_two"],
                    "What did we discuss?",
                    status="pending",
                )
                # Shared subject facts remain visible even when sourced under a
                # different character root. History scope does not filter facts.
                await fact(
                    connection,
                    ids,
                    source_id=other["user_id"],
                    source_run_id=other["run_id"],
                    content="Private other character.",
                )

            # The writer starts before capture but commits only after the reader
            # has read mandatory state. No fact changes or generation fencing
            # can hide an incoherent transcript snapshot.
            late_connection = await engine.connect()
            late_transaction = await late_connection.begin()
            late = await turn(
                late_connection,
                ids["workspace"],
                ids["conversation_one"],
                "Late committed exchange.",
                sequence=5,
            )
            await assistant(
                late_connection, ids["workspace"], ids["conversation_one"], late
            )

            arrived = asyncio.Event()
            resume = asyncio.Event()
            original = snapshot_module.read_history_corpus

            async def pause_before_history(*args, **kwargs):
                arrived.set()
                await resume.wait()
                return await original(*args, **kwargs)

            monkeypatch.setattr(
                snapshot_module, "read_history_corpus", pause_before_history
            )
            task = asyncio.create_task(
                load_turn_state(
                    engine,
                    {
                        "id": current["run_id"],
                        "conversation_id": ids["conversation_two"],
                        "accepted_memory_generation": 1,
                    },
                    include_history=True,
                )
            )
            await asyncio.wait_for(arrived.wait(), 5)
            await late_transaction.commit()
            await late_connection.close()
            resume.set()
            state = await asyncio.wait_for(task, 5)
            assert {item["run_id"] for item in state["history"]["exchanges"]} == {
                old["run_id"],
                sibling["run_id"],
            }
            assert any(item["archived"] for item in state["history"]["exchanges"])
            assert any(
                fact["fact_type"] == "person.preference" for fact in state["facts"]
            )
            assert state["history"]["omitted"]["annotation"] == 0
            assert incomplete["run_id"] not in {
                item["run_id"] for item in state["history"]["exchanges"]
            }
            assert failed["run_id"] not in {
                item["run_id"] for item in state["history"]["exchanges"]
            }
            monkeypatch.setattr(history_module, "MAX_EXCHANGES", 1)
            bounded = await load_turn_state(
                engine,
                {
                    "id": current["run_id"],
                    "conversation_id": ids["conversation_two"],
                    "accepted_memory_generation": 1,
                },
                include_history=True,
            )
            assert len(bounded["history"]["exchanges"]) == 1
            assert bounded["history"]["omitted"]["capacity_at_least"] == 1
            monkeypatch.setattr(history_module, "MAX_MESSAGE_CHARS", 5)
            overlong = await load_turn_state(
                engine,
                {
                    "id": current["run_id"],
                    "conversation_id": ids["conversation_two"],
                    "accepted_memory_generation": 1,
                },
                include_history=True,
            )
            assert overlong["history"]["exchanges"] == []
            assert overlong["history"]["omitted"]["content"] == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_source_relative_branch_and_source_less_removal(
    seed_m2_memory_resources, monkeypatch
) -> None:
    assert DATABASE_URL is not None
    require_disposable_database_url(DATABASE_URL)

    async def scenario():
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                old = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "早上咖啡。晚上茶。",
                )
                await assistant(
                    connection, ids["workspace"], ids["conversation_one"], old
                )
                current = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_two"],
                    "What did I say?",
                    status="pending",
                )
                fact_id, origin = await fact(
                    connection,
                    ids,
                    source_id=old["user_id"],
                    source_run_id=old["run_id"],
                    content="早上咖啡。晚上茶。",
                    quote="早上咖啡。",
                )
                unaffected_id, _ = await fact(
                    connection,
                    ids,
                    source_id=old["user_id"],
                    source_run_id=old["run_id"],
                    content="早上咖啡。晚上茶。",
                    quote="晚上茶。",
                )
                # Two recorded branches from the origin converge on a source-less
                # operator removal. No revision value is surfaced in the envelope.
                branch_ids = [str(uuid4()) for _ in range(3)]
                for index, revision_id in enumerate(branch_ids, start=2):
                    await connection.execute(
                        insert(memory_revisions).values(
                            id=revision_id,
                            fact_id=fact_id,
                            workspace_id=ids["workspace"],
                            subject_id=ids["subject_one"],
                            operation="forget" if index == 4 else "revise",
                            fact_version=index,
                            value={"private": f"old-value-{index}"},
                            action_id=await action(connection, ids),
                            reason="forgotten" if index == 4 else "correct",
                        )
                    )
                await connection.execute(
                    insert(memory_revision_predecessors),
                    [
                        {
                            "revision_id": branch_ids[0],
                            "predecessor_revision_id": origin,
                        },
                        {
                            "revision_id": branch_ids[1],
                            "predecessor_revision_id": origin,
                        },
                        {
                            "revision_id": branch_ids[2],
                            "predecessor_revision_id": branch_ids[0],
                        },
                        {
                            "revision_id": branch_ids[2],
                            "predecessor_revision_id": branch_ids[1],
                        },
                    ],
                )
                await connection.execute(
                    update(memory_facts)
                    .where(memory_facts.c.id == fact_id)
                    .values(
                        status="forgotten",
                        value=None,
                        version=4,
                        current_revision_id=branch_ids[2],
                    )
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
            annotations = state["history"]["exchanges"][0]["annotations"]
            assert len(annotations["links"]) == 2
            assert len(annotations["revisions"]) == 5
            assert len(annotations["predecessor_edges"]) == 4
            assert {revision["reason"] for revision in annotations["revisions"]} == {
                None,
                "correct",
                "forgotten",
            }
            by_id = {fact["id"]: fact for fact in annotations["facts"]}
            assert by_id[fact_id]["status"] == "forgotten"
            assert by_id[fact_id]["value"] is None
            assert by_id[unaffected_id]["status"] == "active"
            assert "old-value" not in str(annotations)
            monkeypatch.setattr(lineage_module, "MAX_LINKS_PER_EXCHANGE", 1)
            too_many_links = await load_turn_state(
                engine,
                {
                    "id": current["run_id"],
                    "conversation_id": ids["conversation_two"],
                    "accepted_memory_generation": 1,
                },
                include_history=True,
            )
            assert too_many_links["history"]["exchanges"] == []
            assert too_many_links["history"]["omitted"]["annotation"] == 1
            monkeypatch.setattr(lineage_module, "MAX_LINKS_PER_EXCHANGE", 8)
            monkeypatch.setattr(lineage_module, "MAX_REVISIONS_PER_FACT", 3)
            bounded = await load_turn_state(
                engine,
                {
                    "id": current["run_id"],
                    "conversation_id": ids["conversation_two"],
                    "accepted_memory_generation": 1,
                },
                include_history=True,
            )
            assert bounded["history"]["exchanges"] == []
            assert bounded["history"]["omitted"]["annotation"] == 1

            async with engine.begin() as connection:
                await connection.execute(
                    update(memory_revision_sources)
                    .where(memory_revision_sources.c.revision_id == origin)
                    .values(message_sha256="f" * 64)
                )
            with pytest.raises(RuntimeValidationError, match="integrity"):
                await load_turn_state(
                    engine,
                    {
                        "id": current["run_id"],
                        "conversation_id": ids["conversation_two"],
                        "accepted_memory_generation": 1,
                    },
                    include_history=True,
                )
        finally:
            await engine.dispose()

    asyncio.run(scenario())
