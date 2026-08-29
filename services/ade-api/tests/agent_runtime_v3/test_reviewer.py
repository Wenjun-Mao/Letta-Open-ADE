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
