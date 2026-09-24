from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.natural_memory_commit import (
    commit_natural_memory_review,
)
from ade_api.features.agent_runtime.natural_memory_policy import (
    prepare_natural_memory_review,
)
from ade_api.features.agent_runtime.natural_memory_review import NaturalReviewDecision
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.memory import MemoryRepository


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="isolated PostgreSQL pgvector test database required"
)


def test_postgres_natural_lifecycle_and_source_roles(
    seed_m2_memory_resources, record_m2_memory_turn
) -> None:
    assert DATABASE_URL is not None

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                subject = ids["subject_one"]
                entity = {"id": subject, "subject_id": subject, "kind": "subject"}
                memory = MemoryRepository(connection)
                fact_id = ""
                for sequence, content, operation, value, reason, status in (
                    (1, "I now live in Toronto.", "add", "Toronto", None, "active"),
                    (
                        2,
                        "I no longer live in Toronto.",
                        "end",
                        None,
                        "ended",
                        "inactive",
                    ),
                    (
                        3,
                        "I live in Toronto again.",
                        "reassert",
                        "Toronto",
                        "reasserted",
                        "active",
                    ),
                    (
                        4,
                        "Forget my Toronto residence.",
                        "forget",
                        None,
                        "forgotten",
                        "forgotten",
                    ),
                ):
                    message = await record_m2_memory_turn(
                        connection,
                        ids["workspace"],
                        ids["conversation_one"],
                        content,
                        sequence=sequence,
                    )
                    message["role"] = "user"
                    quote = content.rstrip(".")
                    proposal = {
                        "kind": "subject_add" if operation == "add" else operation,
                        "evidence": {"mode": "direct", "current_quote": quote},
                    }
                    if operation == "add":
                        proposal.update(
                            fact_type="person.current_location", value=value
                        )
                    else:
                        proposal["target"] = "F1"
                        if operation == "reassert":
                            proposal["value"] = value
                        if operation == "end":
                            proposal["reason"] = reason
                    decision = NaturalReviewDecision.model_validate(
                        {"decisions": [proposal]}
                    )
                    prepared = prepare_natural_memory_review(
                        decision=decision,
                        subject_id=subject,
                        current_user_message=message,
                        available_messages=[message],
                        facts=await memory.list_facts(subject),
                        entities=[entity],
                        candidate_reply="Okay.",
                    )
                    result = await commit_natural_memory_review(
                        connection,
                        workspace_id=ids["workspace"],
                        subject_id=subject,
                        run_id=message["run_id"],
                        review=prepared,
                        operation_embeddings=(
                            None if operation == "forget" else [1.0, 0.0, 0.0],
                        ),
                        embedding_fingerprint="natural-storage-test-v1",
                        embedding_dimensions=3,
                        retrieval_policy_version="natural-storage-test-v2",
                        expected_memory_generation=sequence,
                    )
                    fact_id = result[0]["fact_id"]
                    fact = await memory.get_fact(fact_id)
                    assert fact["status"] == status
                    assert fact["assertion_schema_version"] == 2
                    assert (await memory.get_subject(subject))["memory_generation"] == (
                        sequence + 1
                    )
                    revision = (await memory.list_revisions(fact_id))[-1]
                    assert revision["operation"] == operation
                    assert revision["reason"] == reason
                    sources = await memory.list_revision_sources(
                        result[0]["revision_id"]
                    )
                    assert sources[0]["authority_role"] == "user_assertion"
                    assert sources[0]["message_id"] == message["id"]
                    hits = await memory.search_current_lifecycle_facts(
                        subject_id=subject,
                        query_embedding=[1.0, 0.0, 0.0],
                        model_fingerprint="natural-storage-test-v1",
                        legacy_policy_version="storage-test-v1",
                        lifecycle_policy_version="natural-storage-test-v2",
                        limit=8,
                    )
                    assert [hit["id"] for hit in hits] == (
                        [] if status == "forgotten" else [fact_id]
                    )
                assert len(await memory.list_revisions(fact_id)) == 4
                assert await memory.list_active_facts(subject) == []
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_active_reassert_with_valid_evening_add_rejects_every_sibling(
    seed_m2_memory_resources, record_m2_memory_turn
) -> None:
    assert DATABASE_URL is not None

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                subject = ids["subject_one"]
                entity = {"id": subject, "subject_id": subject, "kind": "subject"}
                memory = MemoryRepository(connection)
                first = await record_m2_memory_turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "I prefer coffee in the morning.",
                    sequence=1,
                )
                first["role"] = "user"
                baseline = prepare_natural_memory_review(
                    decision=NaturalReviewDecision.model_validate(
                        {
                            "decisions": [
                                {
                                    "kind": "subject_add",
                                    "fact_type": "person.preference",
                                    "qualifier": "drink",
                                    "value": "coffee in the morning",
                                    "evidence": {
                                        "mode": "direct",
                                        "current_quote": "I prefer coffee in the morning",
                                    },
                                }
                            ]
                        }
                    ),
                    subject_id=subject,
                    current_user_message=first,
                    available_messages=[first],
                    facts=[],
                    entities=[entity],
                    candidate_reply="Okay.",
                )
                await commit_natural_memory_review(
                    connection,
                    workspace_id=ids["workspace"],
                    subject_id=subject,
                    run_id=first["run_id"],
                    review=baseline,
                    operation_embeddings=(None,),
                    embedding_fingerprint="none",
                    embedding_dimensions=0,
                    retrieval_policy_version="natural-test-v1",
                    expected_memory_generation=1,
                )
                before = await memory.list_facts(subject)
                current = await record_m2_memory_turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "I prefer tea in the evening; still coffee in the morning.",
                    sequence=2,
                )
                current["role"] = "user"
                evidence = {
                    "mode": "direct",
                    "current_quote": current["content"],
                }
                evening = {
                    "kind": "subject_add",
                    "fact_type": "person.preference",
                    "qualifier": "drink",
                    "value": "tea in the evening",
                    "evidence": evidence,
                }
                invalid = {
                    "kind": "reassert",
                    "target": "F1",
                    "value": "coffee in the morning",
                    "evidence": evidence,
                }
                for decisions in ([evening, invalid], [invalid, evening]):
                    with pytest.raises(
                        RuntimeValidationError,
                        match="Reassert requires an inactive target",
                    ):
                        prepare_natural_memory_review(
                            decision=NaturalReviewDecision.model_validate(
                                {"decisions": decisions}
                            ),
                            subject_id=subject,
                            current_user_message=current,
                            available_messages=[current],
                            facts=before,
                            entities=[entity],
                            candidate_reply="Morning coffee and evening tea.",
                        )
                    assert await memory.list_facts(subject) == before
                    assert (await memory.get_subject(subject))["memory_generation"] == 2
                    assert len(await memory.list_revisions(before[0]["id"])) == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_lifecycle_search_deduplicates_indexes_before_fact_limit(
    seed_m2_memory_resources, record_m2_memory_turn
) -> None:
    assert DATABASE_URL is not None

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                subject = ids["subject_one"]
                message = await record_m2_memory_turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "I prefer coffee in the morning and tea in the evening.",
                )
                message["role"] = "user"
                proposals = [
                    {
                        "kind": "subject_add",
                        "fact_type": "person.preference",
                        "qualifier": "drink",
                        "value": value,
                        "evidence": {"mode": "direct", "current_quote": value},
                    }
                    for value in ("coffee in the morning", "tea in the evening")
                ]
                decision = NaturalReviewDecision.model_validate(
                    {"decisions": proposals}
                )
                review = prepare_natural_memory_review(
                    decision=decision,
                    subject_id=subject,
                    current_user_message=message,
                    available_messages=[message],
                    facts=[],
                    entities=[
                        {"id": subject, "subject_id": subject, "kind": "subject"}
                    ],
                    candidate_reply="Okay.",
                )
                committed = await commit_natural_memory_review(
                    connection,
                    workspace_id=ids["workspace"],
                    subject_id=subject,
                    run_id=message["run_id"],
                    review=review,
                    operation_embeddings=([1.0, 0.0, 0.0], [0.9, 0.1, 0.0]),
                    embedding_fingerprint="overlap-test-space",
                    embedding_dimensions=3,
                    retrieval_policy_version="lifecycle-v2",
                    expected_memory_generation=1,
                )
                memory = MemoryRepository(connection)
                await memory.create_embedding(
                    {
                        "id": str(uuid4()),
                        "workspace_id": ids["workspace"],
                        "subject_id": subject,
                        "fact_id": committed[0]["fact_id"],
                        "revision_id": committed[0]["revision_id"],
                        "model_fingerprint": "overlap-test-space",
                        "dimensions": 3,
                        "normalized": True,
                        "retrieval_policy_version": "legacy-v1",
                        "embedding": [1.0, 0.0, 0.0],
                    }
                )
                hits = await memory.search_current_lifecycle_facts(
                    subject_id=subject,
                    query_embedding=[1.0, 0.0, 0.0],
                    model_fingerprint="overlap-test-space",
                    legacy_policy_version="legacy-v1",
                    lifecycle_policy_version="lifecycle-v2",
                    limit=2,
                )
                assert [hit["id"] for hit in hits] == [
                    committed[0]["fact_id"],
                    committed[1]["fact_id"],
                ]
        finally:
            await engine.dispose()

    asyncio.run(scenario())
