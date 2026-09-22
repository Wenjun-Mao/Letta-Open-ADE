from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.ext.asyncio import AsyncConnection

from ade_api.features.agent_runtime.context import ContextBudget, build_context
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.fact_registry import (
    FactRegistryError,
    fact_type_spec,
)
from ade_api.features.agent_runtime.memory_policy import prepare_memory_review
from ade_api.features.agent_runtime.memory_review import ReviewDecision
from ade_api.features.agent_runtime.persistence.memory import MemoryRepository
from workflows.evals.character_memory_dev.m2_comparison import (
    REQUIRED_CASE_IDS,
    load_comparison_spec,
)


SUBJECT_ID = "00000000-0000-0000-0000-000000000101"
OTHER_SUBJECT_ID = "00000000-0000-0000-0000-000000000102"
FACT_ID = "00000000-0000-0000-0000-000000000103"
MESSAGE_ID = "00000000-0000-0000-0000-000000000104"


class _EmptyRows:
    def mappings(self) -> _EmptyRows:
        return self

    def all(self) -> list[dict[str, Any]]:
        return []

    def __iter__(self):
        return iter(())


class _SearchConnection:
    def __init__(self) -> None:
        self.statement: Any | None = None

    async def execute(self, statement: Any) -> _EmptyRows:
        self.statement = statement
        return _EmptyRows()


def _subject_entities() -> list[dict[str, str]]:
    return [
        {"id": SUBJECT_ID, "subject_id": SUBJECT_ID, "kind": "subject", "label": ""}
    ]


def _active_preference() -> list[dict[str, Any]]:
    return [
        {
            "id": FACT_ID,
            "subject_id": SUBJECT_ID,
            "entity_id": SUBJECT_ID,
            "normalized_key": f"person.preference|{SUBJECT_ID}|drink",
            "fact_type": "person.preference",
            "qualifier": "drink",
            "value": "咖啡",
            "status": "active",
            "version": 1,
            "current_revision_id": "revision-1",
        }
    ]


def test_m2_fixture_has_one_common_budget_and_every_required_case() -> None:
    specification = load_comparison_spec()

    assert specification["shared_budget"] == {
        "recent_transcript_tokens": 3000,
        "memory_to_dialogue_tokens": 3000,
        "source_inspection_tokens": 1500,
        "max_reply_tokens": 512,
    }
    assert {case["id"] for case in specification["cases"]} == REQUIRED_CASE_IDS


def test_current_ade_preference_is_separately_correctable_and_forgettable() -> None:
    corrected_message = {"id": MESSAGE_ID, "content": "更正一下，我现在更喜欢花茶。"}
    corrected = prepare_memory_review(
        decision=ReviewDecision.model_validate(
            {
                "proposals": [
                    {
                        "operation": "correct",
                        "value": "花茶",
                        "evidence_quote": "我现在更喜欢花茶",
                        "fact_id": FACT_ID,
                        "expected_version": 1,
                    }
                ]
            }
        ),
        subject_id=SUBJECT_ID,
        current_user_message=corrected_message,
        active_facts=_active_preference(),
        entities=_subject_entities(),
    ).operations[0]
    forgotten = prepare_memory_review(
        decision=ReviewDecision.model_validate(
            {
                "proposals": [
                    {
                        "operation": "forget",
                        "value": None,
                        "evidence_quote": "请忘掉我喜欢咖啡这件事",
                        "fact_id": FACT_ID,
                        "expected_version": 1,
                    }
                ]
            }
        ),
        subject_id=SUBJECT_ID,
        current_user_message={"id": MESSAGE_ID, "content": "请忘掉我喜欢咖啡这件事。"},
        active_facts=_active_preference(),
        entities=_subject_entities(),
    ).operations[0]

    assert corrected.value == "花茶"
    assert corrected.normalized_key == forgotten.normalized_key
    assert corrected.evidence.message_id == MESSAGE_ID
    assert forgotten.proposal.operation.value == "forget"


def test_current_ade_retrieval_contract_filters_subject_and_forgotten_facts() -> None:
    connection = _SearchConnection()
    repository = MemoryRepository(cast(AsyncConnection, connection))

    rows = asyncio.run(
        repository.search_active_facts(
            subject_id=SUBJECT_ID,
            query_embedding=[0.1, 0.2],
            model_fingerprint="embedding-fingerprint",
            retrieval_policy_version="comparison-v1",
            limit=8,
        )
    )

    assert rows == []
    assert connection.statement is not None
    statement = connection.statement.compile(dialect=dialect())
    sql = str(statement)
    assert "memory_facts.subject_id" in sql
    assert "memory_embeddings.subject_id" in sql
    assert "memory_facts.status" in sql
    assert "active" in statement.params.values()
    assert SUBJECT_ID in statement.params.values()
    assert OTHER_SUBJECT_ID not in statement.params.values()


def test_current_ade_context_exposes_active_distractors_before_semantic_retrieval() -> (
    None
):
    context = build_context(
        system_prompt="system",
        persona="persona",
        active_facts=[
            {"id": "dog", "version": 1, "key": "pet.name|s", "value": "Rocky"},
            {
                "id": "trip",
                "version": 1,
                "key": "person.preference|s|place",
                "value": "青岛",
            },
        ],
        retrieved_facts=[],
        recent_messages=[],
        current_user_content="今天工作好多，我有点乱。",
        budget=ContextBudget(
            context_window=8_000,
            max_output_tokens=512,
            tool_schema_tokens=256,
        ),
    )

    system_message = context.messages[0]["content"]
    assert "Rocky" in system_message
    assert "青岛" in system_message
    assert context.retrieved_fact_ids == []


@pytest.mark.parametrize(
    "fact_type",
    ["person.concern", "conversation.promise", "conversation.shared_experience"],
)
def test_current_ade_does_not_claim_unsupported_temporal_or_transcript_types(
    fact_type: str,
) -> None:
    with pytest.raises(FactRegistryError):
        fact_type_spec(fact_type)


def test_cross_subject_correction_remains_rejected_by_current_contract() -> None:
    other_fact = {**_active_preference()[0], "subject_id": OTHER_SUBJECT_ID}
    with pytest.raises(RuntimeValidationError, match="bound subject"):
        prepare_memory_review(
            decision=ReviewDecision.model_validate(
                {
                    "proposals": [
                        {
                            "operation": "correct",
                            "value": "花茶",
                            "evidence_quote": "我现在更喜欢花茶",
                            "fact_id": FACT_ID,
                            "expected_version": 1,
                        }
                    ]
                }
            ),
            subject_id=SUBJECT_ID,
            current_user_message={"id": MESSAGE_ID, "content": "我现在更喜欢花茶。"},
            active_facts=[other_fact],
            entities=_subject_entities(),
        )
