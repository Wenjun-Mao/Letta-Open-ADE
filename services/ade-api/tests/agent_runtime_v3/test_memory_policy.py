from __future__ import annotations

import pytest

from ade_api.features.agent_runtime_v3.errors import RuntimeValidationError
from ade_api.features.agent_runtime_v3.memory_policy import prepare_memory_review
from ade_api.features.agent_runtime_v3.memory_review import ReviewDecision


SUBJECT_ID = "00000000-0000-0000-0000-000000000001"
PET_ID = "00000000-0000-0000-0000-000000000002"
FACT_ID = "00000000-0000-0000-0000-000000000003"
MESSAGE = {
    "id": "00000000-0000-0000-0000-000000000004",
    "content": "Rocky is a Husky",
}
ENTITIES = [
    {"id": SUBJECT_ID, "subject_id": SUBJECT_ID, "kind": "subject", "label": ""},
    {"id": PET_ID, "subject_id": SUBJECT_ID, "kind": "pet", "label": "Rocky"},
]
FACTS = [
    {
        "id": FACT_ID,
        "subject_id": SUBJECT_ID,
        "entity_id": PET_ID,
        "normalized_key": f"pet.name|{PET_ID}",
        "fact_type": "pet.name",
        "qualifier": None,
        "value": "Rocky",
        "status": "active",
        "version": 1,
    }
]


def _decision(proposal: dict) -> ReviewDecision:
    return ReviewDecision.model_validate({"proposals": [proposal]})


def test_add_pet_breed_binds_existing_subject_entity_and_exact_evidence() -> None:
    prepared = prepare_memory_review(
        decision=_decision(
            {
                "operation": "add",
                "fact_type": "pet.breed",
                "value": "Husky",
                "evidence_quote": "Husky",
                "entity_ref": f"existing:{PET_ID}",
            }
        ),
        subject_id=SUBJECT_ID,
        current_user_message=MESSAGE,
        active_facts=FACTS,
        entities=ENTITIES,
    )

    operation = prepared.operations[0]
    assert operation.entity_id == PET_ID
    assert operation.normalized_key == f"pet.breed|{PET_ID}"
    assert operation.evidence.message_id == MESSAGE["id"]


def test_related_facts_must_reuse_the_staged_identity_entity() -> None:
    message = {**MESSAGE, "content": "Rocky is a Husky"}
    with pytest.raises(RuntimeValidationError, match="reuse the new entity_ref"):
        prepare_memory_review(
            decision=ReviewDecision.model_validate(
                {
                    "proposals": [
                        {
                            "operation": "add",
                            "fact_type": "pet.name",
                            "value": "Rocky",
                            "evidence_quote": "Rocky",
                            "entity_ref": "new:rocky",
                        },
                        {
                            "operation": "add",
                            "fact_type": "pet.breed",
                            "value": "Husky",
                            "evidence_quote": "Husky",
                            "entity_ref": "new:another-pet",
                        },
                    ]
                }
            ),
            subject_id=SUBJECT_ID,
            current_user_message=message,
            active_facts=[],
            entities=[ENTITIES[0]],
        )


def test_related_facts_share_one_staged_identity_entity() -> None:
    prepared = prepare_memory_review(
        decision=ReviewDecision.model_validate(
            {
                "proposals": [
                    {
                        "operation": "add",
                        "fact_type": "pet.breed",
                        "value": "Husky",
                        "evidence_quote": "Husky",
                        "entity_ref": "new:rocky",
                    },
                    {
                        "operation": "add",
                        "fact_type": "pet.name",
                        "value": "Rocky",
                        "evidence_quote": "Rocky",
                        "entity_ref": "new:rocky",
                    },
                ]
            }
        ),
        subject_id=SUBJECT_ID,
        current_user_message={**MESSAGE, "content": "Rocky is a Husky"},
        active_facts=[],
        entities=[ENTITIES[0]],
    )

    assert len(prepared.new_entities) == 1
    assert {operation.entity_id for operation in prepared.operations} == {
        prepared.new_entities[0].id
    }


def test_reviewer_cannot_select_another_subject_entity() -> None:
    with pytest.raises(RuntimeValidationError, match="bound subject"):
        prepare_memory_review(
            decision=_decision(
                {
                    "operation": "add",
                    "fact_type": "pet.breed",
                    "value": "Husky",
                    "evidence_quote": "Husky",
                    "entity_ref": "existing:another-subject-entity",
                }
            ),
            subject_id=SUBJECT_ID,
            current_user_message=MESSAGE,
            active_facts=FACTS,
            entities=ENTITIES,
        )


def test_add_against_existing_singleton_key_is_rejected_not_normalized() -> None:
    with pytest.raises(RuntimeValidationError, match="already uses key"):
        prepare_memory_review(
            decision=_decision(
                {
                    "operation": "add",
                    "fact_type": "pet.name",
                    "value": "Rocky",
                    "evidence_quote": "Rocky",
                    "entity_ref": f"existing:{PET_ID}",
                }
            ),
            subject_id=SUBJECT_ID,
            current_user_message=MESSAGE,
            active_facts=FACTS,
            entities=ENTITIES,
        )


def test_correction_requires_the_exact_optimistic_version() -> None:
    with pytest.raises(RuntimeValidationError, match="version changed"):
        prepare_memory_review(
            decision=_decision(
                {
                    "operation": "correct",
                    "fact_type": "pet.name",
                    "value": "Rocky",
                    "evidence_quote": "Rocky",
                    "fact_id": FACT_ID,
                    "expected_version": 2,
                }
            ),
            subject_id=SUBJECT_ID,
            current_user_message=MESSAGE,
            active_facts=FACTS,
            entities=ENTITIES,
        )


def test_forget_requires_explicit_removal_language() -> None:
    with pytest.raises(RuntimeValidationError, match="removal intent"):
        prepare_memory_review(
            decision=_decision(
                {
                    "operation": "forget",
                    "fact_type": "pet.name",
                    "value": None,
                    "evidence_quote": "Rocky",
                    "fact_id": FACT_ID,
                    "expected_version": 1,
                }
            ),
            subject_id=SUBJECT_ID,
            current_user_message=MESSAGE,
            active_facts=FACTS,
            entities=ENTITIES,
        )
