"""Serialized request and strict completion for compact natural review."""

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
    natural_review_request,
    preflight_reviewer_bundle,
    serialized_review_tokens,
)

SUBJECT = "00000000-0000-0000-0000-000000000001"
USER = "00000000-0000-0000-0000-000000000002"
CURRENT = {"id": USER, "role": "user", "content": "I live in Toronto.", "sequence": 2}
ENTITIES = [{"id": SUBJECT, "subject_id": SUBJECT, "kind": "subject", "label": ""}]
WRITE = {
    "decisions": [
        {
            "kind": "subject_add",
            "fact_type": "person.current_location",
            "value": "Toronto",
            "evidence": {"mode": "direct", "current_quote": "I live in Toronto"},
        }
    ]
}


class _Transport:
    def __init__(self, content: object, finish_reason: str | None = "stop") -> None:
        self.content = content
        self.finish_reason = finish_reason
        self.calls: list[dict] = []

    async def chat_completion(self, payload, *, timeout_seconds):
        self.calls.append(payload)
        return {
            "id": "natural-review-request",
            "choices": [
                {
                    "finish_reason": self.finish_reason,
                    "message": {"content": self.content},
                }
            ],
            "usage": {"prompt_tokens": 40, "completion_tokens": 20},
        }


def _review(transport: _Transport, *, observe_request=None, observe_decision=None):
    def validate(decision) -> None:
        prepare_natural_memory_review(
            decision=decision,
            subject_id=SUBJECT,
            current_user_message=CURRENT,
            available_messages=[CURRENT],
            facts=[],
            entities=ENTITIES,
            candidate_reply="Okay.",
        )

    return asyncio.run(
        NaturalMemoryReviewer(transport, provider_adapter="deepseek_openai").review(
            model_key="source::reviewer",
            current_user_message=CURRENT,
            source_messages=[CURRENT],
            facts=[],
            entities=ENTITIES,
            candidate_reply="Okay.",
            timeout_seconds=10,
            validate_decision=validate,
            input_token_limit=100_000,
            observe_request=observe_request,
            observe_decision=observe_decision,
        )
    )


def test_reviewer_sends_one_compact_request_and_binds_accepted_write() -> None:
    transport = _Transport(json.dumps(WRITE))
    result = _review(transport)
    assert result.model_request_count == 1
    assert result.protocol_repaired is False
    assert result.usage == {"prompt_tokens": 40, "completion_tokens": 20}
    assert len(transport.calls) == 1
    packet = json.loads(transport.calls[0]["messages"][1]["content"])
    assert packet["current_user"]["content"] == CURRENT["content"]
    assert "id" not in packet["current_user"]
    assert packet["targets"] == []
    assert transport.calls[0]["response_format"] == {"type": "json_object"}
    assert '"decisions":[]' in transport.calls[0]["messages"][0]["content"]


def test_preflight_and_execution_serialize_the_same_bundle() -> None:
    request = natural_review_request(
        model_key="source::reviewer",
        provider_adapter="deepseek_openai",
        current_user_message=CURRENT,
        source_messages=[CURRENT],
        facts=[],
        entities=ENTITIES,
        candidate_reply="Okay.",
        max_output_tokens=4096,
    )
    assert request["max_tokens"] == 4096
    assert preflight_reviewer_bundle(
        model_key="source::reviewer",
        provider_adapter="deepseek_openai",
        current_user_message=CURRENT,
        source_messages=[CURRENT],
        facts=[],
        entities=ENTITIES,
        candidate_reply_reserve=512,
        input_token_limit=100_000,
        max_output_tokens=4096,
    ) >= serialized_review_tokens(request)


@pytest.mark.parametrize(
    "finish,code",
    [
        ("length", "natural_review_truncated"),
        ("content_filter", "natural_review_refusal"),
        (None, "natural_review_refusal"),
    ],
)
def test_partial_or_unsupported_finish_is_rejected_before_json_parse(
    finish, code
) -> None:
    transport = _Transport(json.dumps({"decisions": []}), finish)
    with pytest.raises(RuntimeValidationError) as error:
        _review(transport)
    assert error.value.detail_code == code
    assert len(transport.calls) == 1


def test_missing_shape_and_malformed_json_reject_without_repair() -> None:
    for content, code in (
        ("{}", "natural_review_schema"),
        ("{", "natural_review_json"),
    ):
        transport = _Transport(content)
        with pytest.raises(RuntimeValidationError) as error:
            _review(transport)
        assert error.value.detail_code == code
        assert len(transport.calls) == 1


def test_optional_reviewer_capture_cannot_veto_success() -> None:
    def fail(_value):
        raise OSError("synthetic capture error")

    result = _review(
        _Transport(json.dumps(WRITE)), observe_request=fail, observe_decision=fail
    )
    assert len(result.decision.decisions) == 1
