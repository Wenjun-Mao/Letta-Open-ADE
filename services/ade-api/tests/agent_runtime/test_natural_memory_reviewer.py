from __future__ import annotations

import asyncio
import json

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.natural_memory_policy import (
    prepare_natural_memory_review,
)
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    NaturalMemoryReviewer,
    reviewer_suffix_limit,
)


SUBJECT = "00000000-0000-0000-0000-000000000001"
USER = "00000000-0000-0000-0000-000000000002"


class _Transport:
    def __init__(self, decision: dict) -> None:
        self.decision = decision
        self.calls: list[dict] = []

    async def chat_completion(self, payload, *, timeout_seconds):
        self.calls.append(payload)
        return {
            "id": "natural-review-request",
            "choices": [{"message": {"content": json.dumps(self.decision)}}],
            "usage": {"prompt_tokens": 40, "completion_tokens": 20},
        }


def _review(transport: _Transport):
    current = {"id": USER, "role": "user", "content": "I live in Toronto."}
    entities = [{"id": SUBJECT, "subject_id": SUBJECT, "kind": "subject", "label": ""}]

    def validate(decision) -> None:
        prepare_natural_memory_review(
            decision=decision,
            subject_id=SUBJECT,
            current_user_message=current,
            available_messages=[current],
            facts=[],
            entities=entities,
            candidate_reply="Okay.",
        )

    return asyncio.run(
        NaturalMemoryReviewer(transport, provider_adapter="deepseek_openai").review(
            model_key="source::reviewer",
            current_user_message=current,
            source_messages=[current],
            facts=[],
            entities=entities,
            candidate_reply="Okay.",
            timeout_seconds=10,
            validate_decision=validate,
            input_token_limit=100_000,
        )
    )


def test_natural_reviewer_sends_mixed_schema_and_one_call() -> None:
    transport = _Transport(
        {
            "proposals": [
                {
                    "claim_id": "residence",
                    "operation": "add",
                    "fact_type": "person.current_location",
                    "value": "Toronto",
                    "evidence_quote": "I live in Toronto",
                    "sources": [
                        {
                            "message_id": USER,
                            "quote": "I live in Toronto",
                            "role": "user_assertion",
                        }
                    ],
                }
            ],
            "claim_dispositions": [
                {
                    "claim_id": "residence",
                    "outcome": "allow",
                    "reason": "supported",
                }
            ],
        }
    )
    result = _review(transport)
    assert result.model_request_count == 1
    assert result.protocol_repaired is False
    assert result.usage == {"prompt_tokens": 40, "completion_tokens": 20}
    assert len(transport.calls) == 1
    request = transport.calls[0]
    assert request["max_tokens"] == 1024
    assert request["response_format"] == {"type": "json_object"}
    packet = json.loads(request["messages"][1]["content"])
    assert packet["candidate_visible_reply"] == "Okay."
    assert packet["source_messages"][0]["id"] == USER
    assert "NaturalRevise" in request["messages"][0]["content"]


def test_natural_reviewer_rejects_false_veto_without_retry() -> None:
    transport = _Transport(
        {
            "proposals": [],
            "claim_dispositions": [
                {
                    "claim_id": "missing",
                    "outcome": "contradiction",
                    "reason": "reply_conflict",
                    "candidate_reply_quote": "Okay",
                }
            ],
        }
    )
    with pytest.raises(RuntimeValidationError, match="closed schema"):
        _review(transport)
    assert len(transport.calls) == 1


def test_reviewer_required_capacity_is_checked_before_generation() -> None:
    with pytest.raises(RuntimeValidationError) as error:
        reviewer_suffix_limit(
            current_user_message={"content": "What about Roxy?"},
            facts=[
                {
                    "id": "fact-1",
                    "fact_type": "pet.identity",
                    "qualifier": None,
                    "value": "Roxy is a Husky" * 100,
                    "status": "active",
                    "version": 1,
                }
            ],
            entities=[{"id": SUBJECT, "kind": "subject", "label": ""}],
            input_token_limit=512,
            candidate_reply_reserve=256,
        )
    assert error.value.detail_code == "natural_reviewer_capacity"
