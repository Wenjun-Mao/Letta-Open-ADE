"""PostgreSQL proof for current authority, support chronology, and stale binding."""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import update

from ade_api.features.agent_runtime.natural_memory_commit import (
    commit_natural_memory_review,
    revalidate_bound_natural_review,
)
from ade_api.features.agent_runtime.natural_memory_policy import (
    prepare_natural_memory_review,
)
from ade_api.features.agent_runtime.natural_memory_review import NaturalReviewDecision
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.persistence.base import OptimisticLockError
from ade_api.features.agent_runtime.persistence.conversations import (
    ConversationRepository,
)
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.memory import MemoryRepository
from ade_api.features.agent_runtime.persistence.metadata import memory_facts


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="isolated PostgreSQL required")


def test_resolution_roles_and_stale_target(
    seed_m2_memory_resources, record_m2_memory_turn
) -> None:
    assert DATABASE_URL is not None

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                subject = ids["subject_one"]
                earlier = await record_m2_memory_turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "One of my dogs is a Husky.",
                    sequence=1,
                )
                current = await record_m2_memory_turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "Roxy",
                    sequence=2,
                )
                conversations = ConversationRepository(connection)
                messages = await conversations.list_messages(ids["conversation_one"])
                subject_entity = {
                    "id": subject,
                    "subject_id": subject,
                    "kind": "subject",
                }
                decision = NaturalReviewDecision.model_validate(
                    {
                        "decisions": [
                            {
                                "kind": "related_add",
                                "fact_type": "pet.breed",
                                "value": "Husky",
                                "entity_ref": "new:roxy",
                                "evidence": {
                                    "mode": "resolve_user",
                                    "current_quote": "Roxy",
                                    "support_handle": "U1",
                                    "support_quote": "One of my dogs is a Husky",
                                },
                            },
                            {
                                "kind": "related_add",
                                "fact_type": "pet.name",
                                "value": "Roxy",
                                "entity_ref": "new:roxy",
                                "evidence": {
                                    "mode": "direct",
                                    "current_quote": "Roxy",
                                },
                            },
                        ]
                    }
                )
                review = prepare_natural_memory_review(
                    decision=decision,
                    subject_id=subject,
                    current_user_message=messages[-1],
                    available_messages=messages,
                    facts=[],
                    entities=[subject_entity],
                    candidate_reply="Okay.",
                )
                assert review.operations[0].current_anchor.message_id == current["id"]
                revalidate_bound_natural_review(
                    review,
                    subject_id=subject,
                    run_id=current["run_id"],
                    messages=messages,
                    facts=[],
                    entities=[subject_entity],
                )
                committed = await commit_natural_memory_review(
                    connection,
                    workspace_id=ids["workspace"],
                    subject_id=subject,
                    run_id=current["run_id"],
                    review=review,
                    operation_embeddings=(None, None),
                    embedding_fingerprint="none",
                    embedding_dimensions=0,
                    retrieval_policy_version="natural-v3",
                    expected_memory_generation=1,
                )
                memory = MemoryRepository(connection)
                sources = await memory.list_revision_sources(
                    committed[0]["revision_id"]
                )
                assert [
                    (row["authority_role"], row["message_id"]) for row in sources
                ] == [
                    ("user_antecedent", earlier["id"]),
                    ("user_resolution", current["id"]),
                ]
                facts = await memory.list_facts(subject)
                assert len(facts) == 2
                assert {fact["entity_id"] for fact in facts} == {
                    review.new_entities[0].id
                }

                correction = await record_m2_memory_turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "not a Husky",
                    sequence=3,
                )
                correction_messages = await conversations.list_messages(
                    ids["conversation_one"]
                )
                revised = NaturalReviewDecision.model_validate(
                    {
                        "decisions": [
                            {
                                "kind": "revise",
                                "target": "F1",
                                "reason": "correct",
                                "value": "not a Husky",
                                "evidence": {
                                    "mode": "direct",
                                    "current_quote": "not a Husky",
                                },
                            }
                        ]
                    }
                )
                held = prepare_natural_memory_review(
                    decision=revised,
                    subject_id=subject,
                    current_user_message=correction_messages[-1],
                    available_messages=correction_messages,
                    facts=facts,
                    entities=[
                        subject_entity,
                        {
                            "id": review.new_entities[0].id,
                            "subject_id": subject,
                            "kind": "pet",
                            "label": "Roxy",
                        },
                    ],
                    candidate_reply="Okay.",
                )
                await connection.execute(
                    update(memory_facts)
                    .where(memory_facts.c.id == held.operations[0].existing_fact["id"])
                    .values(version=2)
                )
                with pytest.raises(OptimisticLockError, match="target changed"):
                    revalidate_bound_natural_review(
                        held,
                        subject_id=subject,
                        run_id=correction["run_id"],
                        messages=correction_messages,
                        facts=await memory.list_facts(subject),
                        entities=await memory.list_entities(subject),
                    )
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_no_save_deferral_commits_only_independent_sibling(
    seed_m2_memory_resources, record_m2_memory_turn
) -> None:
    assert DATABASE_URL is not None

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                subject = ids["subject_one"]
                await record_m2_memory_turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "I prefer coffee in the morning. Don't save that. I now live in Toronto.",
                )
                messages = await ConversationRepository(connection).list_messages(
                    ids["conversation_one"]
                )
                current = messages[-1]
                entities = [{"id": subject, "subject_id": subject, "kind": "subject"}]
                defer = {
                    "kind": "defer",
                    "current_quote": "Don't save that",
                    "reason": "no_save",
                }
                residence = {
                    "kind": "subject_add",
                    "fact_type": "person.current_location",
                    "value": "Toronto",
                    "evidence": {
                        "mode": "direct",
                        "current_quote": "I now live in Toronto",
                    },
                }
                review = prepare_natural_memory_review(
                    decision=NaturalReviewDecision.model_validate(
                        {"decisions": [defer, residence]}
                    ),
                    subject_id=subject,
                    current_user_message=current,
                    available_messages=messages,
                    facts=[],
                    entities=entities,
                    candidate_reply="Okay.",
                )
                assert len(review.operations) == 1
                assert review.deferred_claims[0]["reason"] == "no_save"
                committed = await commit_natural_memory_review(
                    connection,
                    workspace_id=ids["workspace"],
                    subject_id=subject,
                    run_id=current["run_id"],
                    review=review,
                    operation_embeddings=(None,),
                    embedding_fingerprint="none",
                    embedding_dimensions=0,
                    retrieval_policy_version="natural-v3",
                    expected_memory_generation=1,
                )
                assert len(committed) == 1
                memory = MemoryRepository(connection)
                assert [
                    (item["fact_type"], item["value"])
                    for item in await memory.list_facts(subject)
                ] == [("person.current_location", "Toronto")]
                assert (await memory.get_subject(subject))["memory_generation"] == 2
                prohibited = {
                    "kind": "subject_add",
                    "fact_type": "person.preference",
                    "qualifier": "drink",
                    "value": "coffee in the morning",
                    "evidence": {
                        "mode": "direct",
                        "current_quote": "I prefer coffee in the morning",
                    },
                }
                for decisions in ([defer, prohibited], [prohibited, defer]):
                    with pytest.raises(RuntimeValidationError, match="No-save"):
                        prepare_natural_memory_review(
                            decision=NaturalReviewDecision.model_validate(
                                {"decisions": decisions}
                            ),
                            subject_id=subject,
                            current_user_message=current,
                            available_messages=messages,
                            facts=await memory.list_facts(subject),
                            entities=entities,
                            candidate_reply="Okay.",
                        )
                assert len(await memory.list_facts(subject)) == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())
