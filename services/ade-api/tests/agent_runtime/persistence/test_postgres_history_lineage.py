"""Source-relative lifecycle contrasts in isolated PostgreSQL."""

from __future__ import annotations

import asyncio
import hashlib
import os
from uuid import uuid4

import pytest
from sqlalchemy import insert, update

import ade_api.features.agent_runtime.persistence.history_lineage as lineage_module
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    memory_revision_sources,
)
from ade_api.features.agent_runtime.turn_memory_snapshot import load_turn_state
from workflows.evals.character_memory_dev.history_reader_test_support import (
    append_revision,
    assistant,
    conversation,
    fact,
    require_disposable_database_url,
    turn,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="disposable PostgreSQL history test database required"
)


def _run(ids, current):
    return {
        "id": current["run_id"],
        "conversation_id": ids["conversation_two"],
        "accepted_memory_generation": 1,
    }


def test_linear_correction_then_return_preserves_intervening_revision(
    seed_m2_memory_resources, monkeypatch
) -> None:
    assert DATABASE_URL is not None
    require_disposable_database_url(DATABASE_URL)

    async def scenario():
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                contents = [
                    "我早上更喜欢咖啡。",
                    "前面说咖啡是记错了，早上其实更喜欢茶。",
                    "最近早上又更喜欢咖啡。",
                ]
                turns = []
                for index, content in enumerate(contents):
                    exchange = await turn(
                        connection,
                        ids["workspace"],
                        ids["conversation_one"],
                        content,
                        sequence=index * 2 + 1,
                    )
                    await assistant(
                        connection, ids["workspace"], ids["conversation_one"], exchange
                    )
                    turns.append(exchange)
                current = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_two"],
                    "我是不是一直都更喜欢咖啡？",
                    status="pending",
                )
                fact_id, revision = await fact(
                    connection,
                    ids,
                    source_id=turns[0]["user_id"],
                    source_run_id=turns[0]["run_id"],
                    content=contents[0],
                    value="早上更喜欢咖啡",
                )
                revision = await append_revision(
                    connection,
                    ids,
                    fact_id=fact_id,
                    predecessor_id=revision,
                    fact_version=2,
                    operation="revise",
                    reason="correct",
                    value="早上更喜欢茶",
                    status="active",
                    run_id=turns[1]["run_id"],
                    source_id=turns[1]["user_id"],
                    content=contents[1],
                )
                await append_revision(
                    connection,
                    ids,
                    fact_id=fact_id,
                    predecessor_id=revision,
                    fact_version=3,
                    operation="revise",
                    reason="supersede",
                    value="早上又更喜欢咖啡",
                    status="active",
                    run_id=turns[2]["run_id"],
                    source_id=turns[2]["user_id"],
                    content=contents[2],
                )
            state = await load_turn_state(
                engine, _run(ids, current), include_history=True
            )
            original = next(
                item
                for item in state["history"]["exchanges"]
                if item["run_id"] == turns[0]["run_id"]
            )
            annotations = original["annotations"]
            assert [item["reason"] for item in annotations["revisions"]] == [
                None,
                "correct",
                "supersede",
            ]
            assert len(annotations["predecessor_edges"]) == 2
            assert annotations["facts"][0]["status"] == "active"
            assert annotations["facts"][0]["value"] == "早上又更喜欢咖啡"
            monkeypatch.setattr(lineage_module, "MAX_EDGES_PER_FACT", 1)
            bounded = await load_turn_state(
                engine, _run(ids, current), include_history=True
            )
            assert turns[0]["run_id"] not in {
                item["run_id"] for item in bounded["history"]["exchanges"]
            }
            assert bounded["history"]["omitted"]["annotation"] >= 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_fact_repair_and_user_retraction_have_distinct_source_metadata(
    seed_m2_memory_resources,
) -> None:
    assert DATABASE_URL is not None
    require_disposable_database_url(DATABASE_URL)

    async def scenario():
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                repair_text = "我早上更喜欢咖啡。"
                repair = await turn(
                    connection, ids["workspace"], ids["conversation_one"], repair_text
                )
                assistant_text = "你说的是早上喜欢咖啡。"
                assistant_id = await assistant(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    repair,
                    assistant_text,
                )
                repair_followup_text = "我刚才说的是早上，不是整天。"
                repair_followup = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    repair_followup_text,
                    sequence=3,
                )
                await assistant(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    repair_followup,
                )
                separate = await conversation(
                    connection,
                    ids,
                    version_id=ids["definition_version"],
                    subject_id=ids["subject_one"],
                )
                residence_text = "我住在北京。"
                residence = await turn(
                    connection, ids["workspace"], separate, residence_text
                )
                await assistant(connection, ids["workspace"], separate, residence)
                retraction_text = "我之前说住北京是记错了，只是出差。"
                retraction = await turn(
                    connection, ids["workspace"], separate, retraction_text, sequence=3
                )
                await assistant(connection, ids["workspace"], separate, retraction)
                current = await turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_two"],
                    "先前的话后来怎样了？",
                    status="pending",
                )
                repair_fact, repair_origin = await fact(
                    connection,
                    ids,
                    source_id=repair["user_id"],
                    source_run_id=repair["run_id"],
                    content=repair_text,
                    value="整天更喜欢咖啡",
                )
                await connection.execute(
                    insert(memory_revision_sources).values(
                        id=str(uuid4()),
                        revision_id=repair_origin,
                        message_id=assistant_id,
                        start_char=0,
                        end_char=len(assistant_text),
                        quote=assistant_text,
                        message_sha256=hashlib.sha256(
                            assistant_text.encode()
                        ).hexdigest(),
                        authority_role="assistant_referent",
                    )
                )
                repair_next = await append_revision(
                    connection,
                    ids,
                    fact_id=repair_fact,
                    predecessor_id=repair_origin,
                    fact_version=2,
                    operation="revise",
                    reason="correct",
                    value="早上更喜欢咖啡",
                    status="active",
                    run_id=repair_followup["run_id"],
                    source_id=repair_followup["user_id"],
                    content=repair_followup_text,
                )
                await connection.execute(
                    insert(memory_revision_sources).values(
                        id=str(uuid4()),
                        revision_id=repair_next,
                        message_id=repair["user_id"],
                        start_char=0,
                        end_char=len("我早上"),
                        quote="我早上",
                        message_sha256=hashlib.sha256(repair_text.encode()).hexdigest(),
                        authority_role="user_antecedent",
                    )
                )
                residence_fact, residence_origin = await fact(
                    connection,
                    ids,
                    source_id=residence["user_id"],
                    source_run_id=residence["run_id"],
                    content=residence_text,
                    fact_type="person.current_location",
                    qualifier=None,
                    value="北京",
                )
                await append_revision(
                    connection,
                    ids,
                    fact_id=residence_fact,
                    predecessor_id=residence_origin,
                    fact_version=2,
                    operation="end",
                    reason="invalidated",
                    value="北京",
                    status="inactive",
                    run_id=retraction["run_id"],
                    source_id=retraction["user_id"],
                    content=retraction_text,
                )

            state = await load_turn_state(
                engine, _run(ids, current), include_history=True
            )
            by_run = {item["run_id"]: item for item in state["history"]["exchanges"]}
            repaired = by_run[repair["run_id"]]["annotations"]
            retracted = by_run[residence["run_id"]]["annotations"]
            assert {link["authority_role"] for link in repaired["links"]} == {
                "user_assertion",
                "user_antecedent",
                "assistant_referent",
            }
            assert [revision["reason"] for revision in repaired["revisions"]] == [
                None,
                "correct",
            ]
            assert [revision["reason"] for revision in retracted["revisions"]] == [
                None,
                "invalidated",
            ]
            assert repaired["facts"][0]["status"] == "active"
            assert retracted["facts"][0]["status"] == "inactive"
            assert repair_text == by_run[repair["run_id"]]["messages"][0]["content"]
            assert (
                retraction_text
                == by_run[retraction["run_id"]]["messages"][0]["content"]
            )

            async with engine.begin() as connection:
                await connection.execute(
                    update(memory_revision_sources)
                    .where(
                        memory_revision_sources.c.revision_id == repair_origin,
                        memory_revision_sources.c.message_id == assistant_id,
                    )
                    .values(authority_role="user_assertion")
                )
            with pytest.raises(RuntimeValidationError, match="integrity"):
                await load_turn_state(engine, _run(ids, current), include_history=True)
            async with engine.begin() as connection:
                await connection.execute(
                    update(memory_revision_sources)
                    .where(
                        memory_revision_sources.c.revision_id == repair_origin,
                        memory_revision_sources.c.message_id == assistant_id,
                    )
                    .values(authority_role="assistant_referent")
                )
                await fact(
                    connection,
                    ids,
                    source_id=repair["user_id"],
                    source_run_id=repair["run_id"],
                    content=repair_text,
                    subject_key="subject_two",
                )
            with pytest.raises(RuntimeValidationError, match="boundary"):
                await load_turn_state(engine, _run(ids, current), include_history=True)
        finally:
            await engine.dispose()

    asyncio.run(scenario())
