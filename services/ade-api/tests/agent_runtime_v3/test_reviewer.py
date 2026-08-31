from __future__ import annotations

import asyncio
import json

from ade_api.features.agent_runtime_v3.memory_policy import prepare_memory_review
from ade_api.features.agent_runtime_v3.reviewer import MemoryReviewer


SUBJECT_ID = "00000000-0000-0000-0000-000000000001"


class _Transport:
    def __init__(self, decisions: list[dict]) -> None:
        self.decisions = list(decisions)
        self.calls = []

    async def chat_completion(self, payload, *, timeout_seconds):
        self.calls.append((payload, timeout_seconds))
        return {
            "id": f"request-{len(self.calls)}",
            "choices": [
                {
                    "message": {
                        "content": json.dumps(self.decisions.pop(0), ensure_ascii=False)
                    }
                }
            ],
        }


def test_reviewer_repairs_subject_bound_semantic_validation_once() -> None:
    transport = _Transport(
        [
            {
                "proposals": [
                    {
                        "operation": "add",
                        "fact_type": "pet.name",
                        "value": "Rocky",
                        "evidence_quote": "Rocky",
                        "entity_ref": "new:pet",
                        "new_entity_label": "Rocky",
                    },
                    {
                        "operation": "add",
                        "fact_type": "pet.breed",
                        "value": "哈士奇",
                        "evidence_quote": "哈士奇",
                    },
                ]
            },
            {
                "proposals": [
                    {
                        "operation": "add",
                        "fact_type": "pet.name",
                        "value": "Rocky",
                        "evidence_quote": "Rocky",
                        "entity_ref": "new:pet",
                        "new_entity_label": "Rocky",
                    },
                    {
                        "operation": "add",
                        "fact_type": "pet.breed",
                        "value": "哈士奇",
                        "evidence_quote": "哈士奇",
                        "entity_ref": "new:pet",
                    },
                ]
            },
        ]
    )
    message = {
        "id": "00000000-0000-0000-0000-000000000002",
        "content": "我养了一只叫 Rocky 的哈士奇。",
    }
    entities = [
        {
            "id": SUBJECT_ID,
            "subject_id": SUBJECT_ID,
            "kind": "subject",
            "label": "",
        }
    ]

    def validate(decision) -> None:
        prepare_memory_review(
            decision=decision,
            subject_id=SUBJECT_ID,
            current_user_message=message,
            active_facts=[],
            entities=entities,
        )

    result = asyncio.run(
        MemoryReviewer(transport).review(
            model_key="source::reviewer",
            current_user_message=message,
            recent_user_messages=[],
            active_facts=[],
            entities=entities,
            timeout_seconds=30,
            validate_decision=validate,
        )
    )

    assert result.model_request_count == 2
    assert result.protocol_repaired is True
    assert len(result.decision.proposals) == 2
    prepared = prepare_memory_review(
        decision=result.decision,
        subject_id=SUBJECT_ID,
        current_user_message=message,
        active_facts=[],
        entities=entities,
    )
    assert len(prepared.new_entities) == 1
    assert len({operation.entity_id for operation in prepared.operations}) == 1
    repair_message = transport.calls[1][0]["messages"][-1]["content"]
    assert "pet.breed requires existing:<id> or new:<local-ref>" in repair_message
    reviewer_packet = json.loads(transport.calls[0][0]["messages"][1]["content"])
    assert reviewer_packet["review_mode"] == "add_only_no_active_facts"
    assert set(reviewer_packet["operation_contracts"]) == {"add"}
    assert reviewer_packet["operation_contracts"]["add"]["excludes"] == [
        "explicit_forgetting"
    ]
    assert (
        reviewer_packet["worked_examples"]["subject_name_then_pet_name"]["never"]
        == "correct person.name; Rocky names the pet, not the subject"
    )
    assert (
        reviewer_packet["worked_examples"]["preference_qualifiers_are_distinct_slots"][
            "proposal"
        ]["qualifier"]
        == "food"
    )
    assert "explicit_forgetting" not in reviewer_packet["worked_examples"]
    preference_contract = next(
        item
        for item in reviewer_packet["allowed_fact_contracts"]
        if item["fact_type"] == "person.preference"
    )
    assert preference_contract["allowed_qualifiers"] == [
        "activity",
        "color",
        "drink",
        "food",
        "language",
        "media",
        "music",
        "place",
        "season",
        "style",
        "other",
    ]
    assert preference_contract["cardinality"] == "one_per_entity_per_qualifier"
    pet_name_contract = next(
        item
        for item in reviewer_packet["allowed_fact_contracts"]
        if item["fact_type"] == "pet.name"
    )
    assert pet_name_contract["defines_entity_identity"] is True


def test_explicit_forgetting_uses_a_forget_only_schema_on_first_request() -> None:
    fact_id = "00000000-0000-0000-0000-000000000003"
    message = {
        "id": "00000000-0000-0000-0000-000000000002",
        "content": "请忘掉我喜欢蓝色这件事。",
    }
    facts = [
        {
            "id": fact_id,
            "subject_id": SUBJECT_ID,
            "entity_id": SUBJECT_ID,
            "normalized_key": f"person.preference|{SUBJECT_ID}|color",
            "fact_type": "person.preference",
            "qualifier": "color",
            "value": "蓝色",
            "status": "active",
            "version": 1,
        }
    ]
    entities = [
        {
            "id": SUBJECT_ID,
            "subject_id": SUBJECT_ID,
            "kind": "subject",
            "label": "",
        }
    ]
    transport = _Transport(
        [
            {
                "proposals": [
                    {
                        "operation": "forget",
                        "value": None,
                        "fact_id": fact_id,
                        "expected_version": 1,
                        "evidence_quote": "请忘掉我喜欢蓝色这件事。",
                    }
                ]
            }
        ]
    )

    def validate(decision) -> None:
        prepare_memory_review(
            decision=decision,
            subject_id=SUBJECT_ID,
            current_user_message=message,
            active_facts=facts,
            entities=entities,
        )

    result = asyncio.run(
        MemoryReviewer(transport).review(
            model_key="source::reviewer",
            current_user_message=message,
            recent_user_messages=[],
            active_facts=facts,
            entities=entities,
            timeout_seconds=30,
            validate_decision=validate,
        )
    )

    assert result.model_request_count == 1
    request = transport.calls[0][0]
    packet = json.loads(request["messages"][1]["content"])
    assert packet["review_mode"] == "explicit_forgetting"
    assert packet["operation_contracts"] == {
        "forget": {
            "when": "the current message explicitly asks to remove an active fact",
            "value": None,
            "uses_active_fact_id_and_version": True,
        }
    }
    assert (
        packet["worked_examples"]["explicit_forgetting"]["current_message"]
        == "请忘掉我喜欢蓝色这件事。"
    )
    assert packet["worked_examples"]["explicit_forgetting"]["operation"] == "forget"
    schema_text = str(request["response_format"]["json_schema"]["schema"])
    assert "ForgetProposal" in schema_text
    assert "AddProposal" not in schema_text
    assert "CorrectProposal" not in schema_text


def test_ordinary_new_fact_uses_add_only_schema_when_other_facts_exist() -> None:
    message = {
        "id": "00000000-0000-0000-0000-000000000002",
        "content": "My favorite food is 豆浆. Please remember it.",
    }
    facts = [
        {
            "id": "00000000-0000-0000-0000-000000000003",
            "subject_id": SUBJECT_ID,
            "entity_id": SUBJECT_ID,
            "normalized_key": f"person.preference|{SUBJECT_ID}|place",
            "fact_type": "person.preference",
            "qualifier": "place",
            "value": "Royal Ontario Museum",
            "status": "active",
            "version": 1,
        }
    ]
    entities = [
        {
            "id": SUBJECT_ID,
            "subject_id": SUBJECT_ID,
            "kind": "subject",
            "label": "",
        }
    ]
    transport = _Transport(
        [
            {
                "proposals": [
                    {
                        "operation": "add",
                        "fact_type": "person.preference",
                        "qualifier": "food",
                        "value": "豆浆",
                        "evidence_quote": "豆浆",
                        "entity_ref": None,
                        "new_entity_label": "",
                    }
                ]
            }
        ]
    )

    def validate(decision) -> None:
        prepare_memory_review(
            decision=decision,
            subject_id=SUBJECT_ID,
            current_user_message=message,
            active_facts=facts,
            entities=entities,
        )

    result = asyncio.run(
        MemoryReviewer(transport).review(
            model_key="source::reviewer",
            current_user_message=message,
            recent_user_messages=[],
            active_facts=facts,
            entities=entities,
            timeout_seconds=30,
            validate_decision=validate,
        )
    )

    assert result.model_request_count == 1
    request = transport.calls[0][0]
    packet = json.loads(request["messages"][1]["content"])
    assert packet["review_mode"] == "add_only_no_explicit_correction"
    assert set(packet["operation_contracts"]) == {"add"}
    schema_text = str(request["response_format"]["json_schema"]["schema"])
    assert "AddProposal" in schema_text
    assert "CorrectProposal" not in schema_text
    assert "ForgetProposal" not in schema_text


def test_explicit_correction_uses_correct_only_schema() -> None:
    fact_id = "00000000-0000-0000-0000-000000000003"
    message = {
        "id": "00000000-0000-0000-0000-000000000002",
        "content": "更正一下，我现在住在多伦多。",
    }
    facts = [
        {
            "id": fact_id,
            "subject_id": SUBJECT_ID,
            "entity_id": SUBJECT_ID,
            "normalized_key": f"person.current_location|{SUBJECT_ID}",
            "fact_type": "person.current_location",
            "qualifier": None,
            "value": "北京",
            "status": "active",
            "version": 1,
        }
    ]
    entities = [
        {
            "id": SUBJECT_ID,
            "subject_id": SUBJECT_ID,
            "kind": "subject",
            "label": "",
        }
    ]
    transport = _Transport(
        [
            {
                "proposals": [
                    {
                        "operation": "correct",
                        "value": "多伦多",
                        "fact_id": fact_id,
                        "expected_version": 1,
                        "evidence_quote": "多伦多",
                    }
                ]
            }
        ]
    )

    def validate(decision) -> None:
        prepare_memory_review(
            decision=decision,
            subject_id=SUBJECT_ID,
            current_user_message=message,
            active_facts=facts,
            entities=entities,
        )

    result = asyncio.run(
        MemoryReviewer(transport).review(
            model_key="source::reviewer",
            current_user_message=message,
            recent_user_messages=[],
            active_facts=facts,
            entities=entities,
            timeout_seconds=30,
            validate_decision=validate,
        )
    )

    assert result.model_request_count == 1
    request = transport.calls[0][0]
    packet = json.loads(request["messages"][1]["content"])
    assert packet["review_mode"] == "explicit_correction"
    assert set(packet["operation_contracts"]) == {"correct"}
    assert (
        packet["worked_examples"]["explicit_location_correction"]["proposal"][
            "operation"
        ]
        == "correct"
    )
    schema_text = str(request["response_format"]["json_schema"]["schema"])
    assert "CorrectProposal" in schema_text
    assert "AddProposal" not in schema_text
    assert "ForgetProposal" not in schema_text
