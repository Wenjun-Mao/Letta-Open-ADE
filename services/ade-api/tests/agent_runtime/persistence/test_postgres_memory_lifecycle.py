from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import text

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
from ade_api.features.agent_runtime.contracts import MemoryOperation


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
TEST_DATABASE_PREFIX = "ade_m2_memory_test_"
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="ADE_TEST_DATABASE_URL must point at a disposable M2 test database",
)


def test_postgres_memory_lifecycle_lineage_and_subject_isolation(
    m2_memory_lifecycle_support,
) -> None:
    assert DATABASE_URL is not None
    engine = create_persistence_engine(DATABASE_URL)

    async def scenario() -> None:
        async with engine.begin() as connection:
            database_name = await connection.scalar(text("SELECT current_database()"))
            if not str(database_name).startswith(TEST_DATABASE_PREFIX):
                raise AssertionError(
                    "PostgreSQL memory lifecycle test requires a uniquely named "
                    f"{TEST_DATABASE_PREFIX}<id> database"
                )

            ids = await m2_memory_lifecycle_support.seed_resources(connection)
            repository = MemoryRepository(connection)
            subject_entity = {
                "id": ids["subject_one"],
                "subject_id": ids["subject_one"],
                "kind": "subject",
                "label": "Subject One",
            }

            add_turn = await m2_memory_lifecycle_support.record_turn(
                connection,
                ids["workspace"],
                ids["conversation_one"],
                "我喜欢红茶。",
            )
            add_review = m2_memory_lifecycle_support.prepare_review(
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

            correction_turn = await m2_memory_lifecycle_support.record_turn(
                connection,
                ids["workspace"],
                ids["conversation_two"],
                "我现在更喜欢绿茶，之前的偏好需要更正。",
            )
            active_fact = (await repository.list_active_facts(ids["subject_one"]))[0]
            correction_review = m2_memory_lifecycle_support.prepare_review(
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

            other_subject_turn = await m2_memory_lifecycle_support.record_turn(
                connection,
                ids["workspace"],
                ids["other_conversation"],
                "我喜欢咖啡。",
            )
            other_subject_entity = {
                **subject_entity,
                "id": ids["subject_two"],
                "subject_id": ids["subject_two"],
                "label": "Subject Two",
            }
            other_subject_review = m2_memory_lifecycle_support.prepare_review(
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
                message=other_subject_turn,
                entities=[other_subject_entity],
            )
            other_result = await commit_memory_review(
                connection,
                workspace_id=ids["workspace"],
                subject_id=ids["subject_two"],
                run_id=other_subject_turn["run_id"],
                review=other_subject_review,
                operation_embeddings=([0.0, 1.0, 0.0],),
                embedding_fingerprint="synthetic-vector-v1",
                embedding_dimensions=3,
                retrieval_policy_version="storage-test-v1",
            )
            other_fact_id = other_result[0]["fact_id"]

            async def retrieved_facts(
                subject_id: str, query_embedding: list[float]
            ) -> list[dict]:
                return await repository.search_active_facts(
                    subject_id=subject_id,
                    query_embedding=query_embedding,
                    model_fingerprint="synthetic-vector-v1",
                    retrieval_policy_version="storage-test-v1",
                    limit=10,
                )

            first_subject_hits = await retrieved_facts(
                ids["subject_one"], [0.0, 1.0, 0.0]
            )
            assert {hit["id"] for hit in first_subject_hits} == {fact_id}
            old_vector_hits = await retrieved_facts(ids["subject_one"], [1.0, 0.0, 0.0])
            assert {hit["id"] for hit in old_vector_hits} == {fact_id}
            assert old_vector_hits[0]["current_revision_id"] == second_revision_id
            assert old_vector_hits[0]["distance"] == pytest.approx(1.0)
            assert {
                hit["id"]
                for hit in await retrieved_facts(ids["subject_two"], [0.0, 1.0, 0.0])
            } == {other_fact_id}

            forget_turn = await m2_memory_lifecycle_support.record_turn(
                connection,
                ids["workspace"],
                ids["conversation_two"],
                "请把这个偏好忘掉。",
                sequence=2,
            )
            active_fact = (await repository.list_active_facts(ids["subject_one"]))[0]
            forget_review = m2_memory_lifecycle_support.prepare_review(
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
                active_facts=[active_fact],
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

            assert await repository.list_active_facts(ids["subject_one"]) == []
            assert await retrieved_facts(ids["subject_one"], [0.0, 1.0, 0.0]) == []
            assert {
                hit["id"]
                for hit in await retrieved_facts(ids["subject_two"], [0.0, 1.0, 0.0])
            } == {other_fact_id}

            revisions = await repository.list_revisions(fact_id)
            assert [(row["operation"], row["fact_version"]) for row in revisions] == [
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
            sources = {
                row["id"]: await repository.list_revision_sources(row["id"])
                for row in revisions
            }
            assert [sources[row["id"]][0]["message_id"] for row in revisions] == [
                add_turn["id"],
                correction_turn["id"],
                forget_turn["id"],
            ]
            assert [sources[row["id"]][0]["quote"] for row in revisions] == [
                "红茶",
                "绿茶",
                "请把这个偏好忘掉",
            ]
            forgotten = (await repository.list_facts(ids["subject_one"]))[0]
            assert forgotten["id"] == fact_id
            assert forgotten["status"] == "forgotten"
            assert forgotten["current_revision_id"] == third_revision_id

    try:
        asyncio.run(scenario())
    finally:
        asyncio.run(engine.dispose())
