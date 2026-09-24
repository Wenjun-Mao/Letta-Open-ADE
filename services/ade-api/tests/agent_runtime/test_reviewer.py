from __future__ import annotations

import asyncio
import json
from pathlib import Path

from ade_api.features.agent_runtime.memory_policy import prepare_memory_review
from ade_api.features.agent_runtime.reviewer import MemoryReviewer


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


def test_reviewer_repairs_subject_bound_structural_validation_once() -> None:
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
    assert "review_mode" not in reviewer_packet
    assert set(reviewer_packet["operation_contracts"]) == {"add", "correct", "forget"}
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


def test_factual_forgetting_uses_the_common_schema_on_first_request() -> None:
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
    assert "review_mode" not in packet
    assert set(packet["operation_contracts"]) == {"add", "correct", "forget"}
    assert packet["worked_examples"]["explicit_forgetting"]["operation"] == "forget"
    schema_text = str(request["response_format"]["json_schema"]["schema"])
    assert all(
        name in schema_text
        for name in ("ForgetProposal", "AddProposal", "CorrectProposal")
    )


def test_deepseek_reviewer_uses_json_object_with_local_typed_validation() -> None:
    fact_id = "00000000-0000-0000-0000-000000000003"
    message = {"id": "message-1", "content": "Please forget that I like blue."}
    facts = [
        {
            "id": fact_id,
            "subject_id": SUBJECT_ID,
            "entity_id": SUBJECT_ID,
            "normalized_key": f"person.preference|{SUBJECT_ID}|color",
            "fact_type": "person.preference",
            "qualifier": "color",
            "value": "blue",
            "status": "active",
            "version": 2,
        }
    ]
    entities = [
        {"id": SUBJECT_ID, "subject_id": SUBJECT_ID, "kind": "subject", "label": ""}
    ]
    transport = _Transport(
        [
            {
                "proposals": [
                    {
                        "operation": "forget",
                        "value": None,
                        "fact_id": fact_id,
                        "expected_version": 2,
                        "evidence_quote": message["content"],
                    }
                ]
            }
        ]
    )

    result = asyncio.run(
        MemoryReviewer(transport, provider_adapter="deepseek_openai").review(
            model_key="deepseek::deepseek-flash",
            current_user_message=message,
            recent_user_messages=[],
            active_facts=facts,
            entities=entities,
            timeout_seconds=30,
            max_model_requests=1,
            validate_decision=lambda decision: prepare_memory_review(
                decision=decision,
                subject_id=SUBJECT_ID,
                current_user_message=message,
                active_facts=facts,
                entities=entities,
            ),
        )
    )
    assert result.model_request_count == 1
    assert result.decision.proposals[0].fact_id == fact_id
    request = transport.calls[0][0]
    assert request["response_format"] == {"type": "json_object"}
    assert request["thinking"] == {"type": "enabled"}
    assert request["reasoning_effort"] == "high"
    assert "temperature" not in request
    assert "chat_template_kwargs" not in request
    assert "JSON" in request["messages"][0]["content"]


def test_ordinary_new_fact_uses_common_schema_when_other_facts_exist() -> None:
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
    assert "review_mode" not in packet
    assert set(packet["operation_contracts"]) == {"add", "correct", "forget"}
    schema_text = str(request["response_format"]["json_schema"]["schema"])
    assert all(
        name in schema_text
        for name in ("AddProposal", "CorrectProposal", "ForgetProposal")
    )


def test_factual_correction_uses_common_schema() -> None:
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
    assert "review_mode" not in packet
    assert set(packet["operation_contracts"]) == {"add", "correct", "forget"}
    assert (
        packet["worked_examples"]["explicit_location_correction"]["proposal"][
            "operation"
        ]
        == "correct"
    )
    schema_text = str(request["response_format"]["json_schema"]["schema"])
    assert all(
        name in schema_text
        for name in ("CorrectProposal", "AddProposal", "ForgetProposal")
    )


def test_agent_studio_correction_draft_uses_common_reviewer_contract() -> None:
    path = (
        Path(__file__).resolve().parents[4]
        / "config/agent-studio/memory-action-contract.json"
    )
    contract = json.loads(path.read_text(encoding="utf-8"))
    transport = _Transport([{"proposals": []}])
    asyncio.run(
        MemoryReviewer(transport).review(
            model_key="source::reviewer",
            current_user_message={
                "id": "message-1",
                "content": contract["correction_message"],
            },
            recent_user_messages=[],
            active_facts=[
                {
                    "id": contract["fact"]["id"],
                    "subject_id": SUBJECT_ID,
                    "entity_id": SUBJECT_ID,
                    "fact_type": contract["fact"]["fact_type"],
                    "value": contract["fact"]["value"],
                    "status": "active",
                    "version": 1,
                }
            ],
            entities=[{"id": SUBJECT_ID, "kind": "subject", "subject_id": SUBJECT_ID}],
            timeout_seconds=30,
            validate_decision=lambda _: None,
        )
    )
    packet = json.loads(transport.calls[0][0]["messages"][1]["content"])
    assert "review_mode" not in packet
    assert set(packet["operation_contracts"]) == {"add", "correct", "forget"}
