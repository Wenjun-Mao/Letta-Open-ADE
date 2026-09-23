from __future__ import annotations

import asyncio
import os
import re

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import AsyncConnection

from ade_api.features.agent_runtime.contracts import MemoryOperation
from ade_api.features.agent_runtime.memory_commit import commit_memory_review
from ade_api.features.agent_runtime.memory_review import (
    AddProposal,
    CorrectProposal,
    ForgetProposal,
    ReviewDecision,
)
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.memory import MemoryRepository


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
TEST_DATABASE = re.compile(r"^ade_m2_memory_test_[0-9a-f]{8,}$")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="ADE_TEST_DATABASE_URL must point at a disposable M2 test database",
)


def _require_disposable_database_url(database_url: str) -> None:
    try:
        url = make_url(database_url)
    except (ArgumentError, ValueError) as exc:
        raise AssertionError(
            "PostgreSQL memory test requires a passwordless loopback test URL"
        ) from exc
    if (
        url.drivername != "postgresql+psycopg"
        or url.host not in {"localhost", "127.0.0.1", "::1"}
        or url.username != "ade_owner"
        or url.password is not None
        or not url.database
        or not TEST_DATABASE.fullmatch(url.database)
    ):
        raise AssertionError(
            "PostgreSQL memory test requires a passwordless loopback ade_owner URL for a "
            "uniquely named ade_m2_memory_test_<hex-id> database"
        )


async def _search_active_facts(
    connection: AsyncConnection, subject_id: str, query_embedding: list[float]
) -> list[dict]:
    return await MemoryRepository(connection).search_active_facts(
        subject_id=subject_id,
        query_embedding=query_embedding,
        model_fingerprint="synthetic-vector-v1",
        retrieval_policy_version="storage-test-v1",
        limit=10,
    )


def test_postgres_memory_lifecycle_lineage_and_subject_isolation(
    seed_m2_memory_resources,
    record_m2_memory_turn,
    prepare_m2_memory_review,
) -> None:
    assert DATABASE_URL is not None
    _require_disposable_database_url(DATABASE_URL)

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        read_engine = create_persistence_engine(DATABASE_URL)
        try:
            async with read_engine.connect() as connection:
                database_name = await connection.scalar(
                    text("SELECT current_database()")
                )
                assert isinstance(database_name, str) and TEST_DATABASE.fullmatch(
                    database_name
                )

            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                subject_entity = {
                    "id": ids["subject_one"],
                    "subject_id": ids["subject_one"],
                    "kind": "subject",
                    "label": "Subject One",
                }
                add_turn = await record_m2_memory_turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "我喜欢红茶。",
                )
                add_review = prepare_m2_memory_review(
                    ReviewDecision(
                        proposals=[
                            AddProposal(
                                operation=MemoryOperation.ADD,
                                fact_type="person.preference",
                                qualifier="drink",
                                value="红茶",
                                evidence_quote="红茶",
                            )
                        ]
                    ),
                    subject_id=ids["subject_one"],
                    message=add_turn,
                    entities=[subject_entity],
                )
                add_result = await commit_memory_review(
                    connection,
                    workspace_id=ids["workspace"],
                    subject_id=ids["subject_one"],
                    run_id=add_turn["run_id"],
                    review=add_review,
                    operation_embeddings=([1.0, 0.0, 0.0],),
                    embedding_fingerprint="synthetic-vector-v1",
                    embedding_dimensions=3,
                    retrieval_policy_version="storage-test-v1",
                )
                fact_id = add_result[0]["fact_id"]
                first_revision_id = add_result[0]["revision_id"]

            async with read_engine.connect() as connection:
                repository = MemoryRepository(connection)
                active_facts = await repository.list_active_facts(ids["subject_one"])
                assert len(active_facts) == 1
                active_fact = active_facts[0]
                assert active_fact["id"] == fact_id
                assert active_fact["value"] == "红茶"
                first_revision = await repository.list_revisions(fact_id)
                assert [row["id"] for row in first_revision] == [first_revision_id]
                first_source = (
                    await repository.list_revision_sources(
                        first_revision_id,
                        workspace_id=ids["workspace"],
                        subject_id=ids["subject_one"],
                    )
                )[0]
                assert first_source["message_id"] == add_turn["id"]
                assert first_source["conversation_id"] == ids["conversation_one"]
                assert first_source["message_sequence"] == 1

            async with engine.begin() as connection:
                correction_turn = await record_m2_memory_turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_two"],
                    "我现在更喜欢绿茶，之前的偏好需要更正。",
                )
                correction_review = prepare_m2_memory_review(
                    ReviewDecision(
                        proposals=[
                            CorrectProposal(
                                operation=MemoryOperation.CORRECT,
                                fact_id=fact_id,
                                expected_version=1,
                                value="绿茶",
                                evidence_quote="绿茶",
                            )
                        ]
                    ),
                    subject_id=ids["subject_one"],
                    message=correction_turn,
                    active_facts=[active_fact],
                    entities=[subject_entity],
                )
                correction_result = await commit_memory_review(
                    connection,
                    workspace_id=ids["workspace"],
                    subject_id=ids["subject_one"],
                    run_id=correction_turn["run_id"],
                    review=correction_review,
                    operation_embeddings=([0.0, 1.0, 0.0],),
                    embedding_fingerprint="synthetic-vector-v1",
                    embedding_dimensions=3,
                    retrieval_policy_version="storage-test-v1",
                )
                second_revision_id = correction_result[0]["revision_id"]

            async with read_engine.connect() as connection:
                repository = MemoryRepository(connection)
                corrected_facts = await repository.list_active_facts(ids["subject_one"])
                assert len(corrected_facts) == 1
                corrected_fact = corrected_facts[0]
                assert corrected_fact["value"] == "绿茶"
                assert corrected_fact["version"] == 2
                assert corrected_fact["current_revision_id"] == second_revision_id
                revisions = await repository.list_revisions(fact_id)
                assert [
                    (row["operation"], row["fact_version"]) for row in revisions
                ] == [
                    ("add", 1),
                    ("correct", 2),
                ]
                assert await repository.list_revision_predecessor_ids(
                    second_revision_id
                ) == [first_revision_id]
                correction_sources = await repository.list_revision_sources(
                    second_revision_id
                )
                assert correction_sources[0]["message_id"] == correction_turn["id"]
                assert (
                    correction_sources[0]["conversation_id"] == ids["conversation_two"]
                )
                assert correction_sources[0]["message_sequence"] == 1
                assert correction_sources[0]["quote"] == "绿茶"
                current_hits = await _search_active_facts(
                    connection, ids["subject_one"], [0.0, 1.0, 0.0]
                )
                old_vector_hits = await _search_active_facts(
                    connection, ids["subject_one"], [1.0, 0.0, 0.0]
                )
                assert {hit["id"] for hit in current_hits} == {fact_id}
                assert {hit["id"] for hit in old_vector_hits} == {fact_id}
                assert old_vector_hits[0]["current_revision_id"] == second_revision_id
                assert old_vector_hits[0]["distance"] == pytest.approx(1.0)

            async with engine.begin() as connection:
                other_turn = await record_m2_memory_turn(
                    connection,
                    ids["workspace"],
                    ids["other_conversation"],
                    "我喜欢咖啡。",
                )
                other_entity = {
                    "id": ids["subject_two"],
                    "subject_id": ids["subject_two"],
                    "kind": "subject",
                    "label": "Subject Two",
                }
                other_review = prepare_m2_memory_review(
                    ReviewDecision(
                        proposals=[
                            AddProposal(
                                operation=MemoryOperation.ADD,
                                fact_type="person.preference",
                                qualifier="drink",
                                value="咖啡",
                                evidence_quote="咖啡",
                            )
                        ]
                    ),
                    subject_id=ids["subject_two"],
                    message=other_turn,
                    entities=[other_entity],
                )
                other_result = await commit_memory_review(
                    connection,
                    workspace_id=ids["workspace"],
                    subject_id=ids["subject_two"],
                    run_id=other_turn["run_id"],
                    review=other_review,
                    operation_embeddings=([0.0, 1.0, 0.0],),
                    embedding_fingerprint="synthetic-vector-v1",
                    embedding_dimensions=3,
                    retrieval_policy_version="storage-test-v1",
                )
                other_fact_id = other_result[0]["fact_id"]

            async with read_engine.connect() as connection:
                first_hits = await _search_active_facts(
                    connection, ids["subject_one"], [0.0, 1.0, 0.0]
                )
                second_hits = await _search_active_facts(
                    connection, ids["subject_two"], [0.0, 1.0, 0.0]
                )
                assert {hit["id"] for hit in first_hits} == {fact_id}
                assert {hit["id"] for hit in second_hits} == {other_fact_id}

            async with engine.begin() as connection:
                forget_turn = await record_m2_memory_turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_two"],
                    "请把这个偏好忘掉。",
                    sequence=2,
                )
                forget_review = prepare_m2_memory_review(
                    ReviewDecision(
                        proposals=[
                            ForgetProposal(
                                operation=MemoryOperation.FORGET,
                                fact_id=fact_id,
                                expected_version=2,
                                value=None,
                                evidence_quote="请把这个偏好忘掉",
                            )
                        ]
                    ),
                    subject_id=ids["subject_one"],
                    message=forget_turn,
                    active_facts=[corrected_fact],
                    entities=[subject_entity],
                )
                forget_result = await commit_memory_review(
                    connection,
                    workspace_id=ids["workspace"],
                    subject_id=ids["subject_one"],
                    run_id=forget_turn["run_id"],
                    review=forget_review,
                    operation_embeddings=(None,),
                    embedding_fingerprint="synthetic-vector-v1",
                    embedding_dimensions=3,
                    retrieval_policy_version="storage-test-v1",
                )
                third_revision_id = forget_result[0]["revision_id"]

            async with read_engine.connect() as connection:
                repository = MemoryRepository(connection)
                assert await repository.list_active_facts(ids["subject_one"]) == []
                assert (
                    await _search_active_facts(
                        connection, ids["subject_one"], [0.0, 1.0, 0.0]
                    )
                    == []
                )
                other_hits = await _search_active_facts(
                    connection, ids["subject_two"], [0.0, 1.0, 0.0]
                )
                assert {hit["id"] for hit in other_hits} == {other_fact_id}

                revisions = await repository.list_revisions(fact_id)
                assert [
                    (row["operation"], row["fact_version"]) for row in revisions
                ] == [
                    ("add", 1),
                    ("correct", 2),
                    ("forget", 3),
                ]
                assert [row["id"] for row in revisions] == [
                    first_revision_id,
                    second_revision_id,
                    third_revision_id,
                ]
                assert await repository.list_revision_predecessor_ids(
                    second_revision_id
                ) == [first_revision_id]
                assert await repository.list_revision_predecessor_ids(
                    third_revision_id
                ) == [second_revision_id]
                sources = [
                    (await repository.list_revision_sources(row["id"]))[0]
                    for row in revisions
                ]
                assert [source["message_id"] for source in sources] == [
                    add_turn["id"],
                    correction_turn["id"],
                    forget_turn["id"],
                ]
                assert [source["quote"] for source in sources] == [
                    "红茶",
                    "绿茶",
                    "请把这个偏好忘掉",
                ]
                forgotten = (await repository.list_facts(ids["subject_one"]))[0]
                assert forgotten["id"] == fact_id
                assert forgotten["status"] == "forgotten"
                assert forgotten["current_revision_id"] == third_revision_id
        finally:
            await read_engine.dispose()
            await engine.dispose()

    asyncio.run(scenario())
