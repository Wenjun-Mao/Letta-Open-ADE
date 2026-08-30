from __future__ import annotations

import asyncio
import hashlib

import pytest

from ade_api.features.agent_runtime_v3.compaction import (
    parse_compaction_response,
    plan_compaction,
)
from ade_api.features.agent_runtime_v3.errors import RuntimeValidationError
from ade_api.features.agent_runtime_v3.executor import ConversationExecutor


class _Transport:
    def __init__(self) -> None:
        self.calls = []

    async def chat_completion(self, payload, *, timeout_seconds):
        self.calls.append((payload, timeout_seconds))
        return {
            "id": "summary-request-1",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": (
                            '{"summary":"The user and assistant discussed Rocky."}'
                        ),
                    },
                }
            ],
        }


def test_compaction_summarizes_an_omitted_contiguous_history_prefix() -> None:
    messages = [
        {
            "id": f"message-{sequence}",
            "sequence": sequence,
            "role": "user" if sequence % 2 else "assistant",
            "content": f"history {sequence}",
        }
        for sequence in range(1, 72)
    ]
    plan = plan_compaction(
        messages=messages,
        current_user_message_id="message-71",
        summary=None,
        recent_token_budget=100_000,
        compaction_input_token_budget=100_000,
    )

    assert plan is not None
    assert plan.through_sequence == 60
    assert plan.source_message_ids == tuple(
        f"message-{sequence}" for sequence in range(1, 61)
    )
    assert [message["sequence"] for message in plan.incremental_messages] == list(
        range(1, 61)
    )

    transport = _Transport()
    result = asyncio.run(
        ConversationExecutor(transport).compact(
            model_key="source::model",
            model_fingerprint="f" * 64,
            plan=plan,
            timeout_seconds=30,
            max_output_tokens=100,
            summary_token_budget=1_500,
        )
    )

    assert result.content == "The user and assistant discussed Rocky."
    assert result.provider_request_id == "summary-request-1"
    assert len(result.prompt_sha256) == 64
    assert len(result.input_sha256) == 64
    assert len(result.content_sha256) == 64
    assert len(result.policy_sha256) == 64
    assert result.model_fingerprint == "f" * 64
    assert "tools" not in transport.calls[0][0]
    assert transport.calls[0][0]["temperature"] == 0
    assert transport.calls[0][0]["chat_template_kwargs"] == {"enable_thinking": False}
    assert transport.calls[0][0]["response_format"]["json_schema"]["strict"] is True
    assert (
        result.input_sha256
        == hashlib.sha256(
            transport.calls[0][0]["messages"][1]["content"].encode("utf-8")
        ).hexdigest()
    )


def test_compaction_extends_the_prior_summary_with_only_the_contiguous_delta() -> None:
    messages = [
        {
            "id": f"message-{sequence}",
            "sequence": sequence,
            "role": "user" if sequence % 2 else "assistant",
            "content": f"history {sequence}",
        }
        for sequence in range(1, 82)
    ]

    plan = plan_compaction(
        messages=messages,
        current_user_message_id="message-81",
        summary={
            "id": "summary-1",
            "version": 2,
            "through_sequence": 50,
            "content": "Earlier summary.",
        },
        recent_token_budget=1,
        compaction_input_token_budget=100_000,
    )

    assert plan is not None
    assert plan.previous_summary_id == "summary-1"
    assert plan.expected_summary_version == 2
    assert plan.previous_summary_content == "Earlier summary."
    assert plan.through_sequence == 80
    assert plan.source_message_ids[0] == "message-1"
    assert plan.source_message_ids[-1] == "message-80"
    assert [message["sequence"] for message in plan.incremental_messages] == list(
        range(51, 81)
    )


def test_compaction_fails_closed_when_its_incremental_input_cannot_fit() -> None:
    messages = [
        {
            "id": f"message-{sequence}",
            "sequence": sequence,
            "role": "user" if sequence % 2 else "assistant",
            "content": "history " + ("x" * 1_000),
        }
        for sequence in range(1, 72)
    ]

    with pytest.raises(RuntimeValidationError, match="compaction input budget"):
        plan_compaction(
            messages=messages,
            current_user_message_id="message-71",
            summary=None,
            recent_token_budget=3_000,
            compaction_input_token_budget=100,
        )


def test_compaction_response_must_fit_the_summary_context_budget() -> None:
    with pytest.raises(RuntimeValidationError, match="summary exceeds"):
        parse_compaction_response(
            '{"summary":"' + ("x" * 100) + '"}', summary_token_budget=10
        )
