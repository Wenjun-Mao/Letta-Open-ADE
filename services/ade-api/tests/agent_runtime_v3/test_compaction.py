from __future__ import annotations

import asyncio
import hashlib

from ade_api.features.agent_runtime_v3.compaction import plan_compaction
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
                        "content": "The user and assistant discussed Rocky.",
                    },
                }
            ],
        }


def test_compaction_summarizes_an_omitted_contiguous_history_prefix() -> None:
    messages = [
        {"id": "message-1", "sequence": 1, "role": "user", "content": "I have Rocky."},
        {"id": "message-2", "sequence": 2, "role": "assistant", "content": "Nice."},
        {"id": "message-3", "sequence": 3, "role": "user", "content": "He is a Husky."},
        {"id": "message-4", "sequence": 4, "role": "user", "content": "What breed is Rocky?"},
    ]
    plan = plan_compaction(
        messages=messages,
        current_user_message_id="message-4",
        summary=None,
        omitted_message_ids=["message-1", "message-2"],
    )

    assert plan is not None
    assert plan.through_sequence == 2
    assert plan.source_message_ids == ("message-1", "message-2")
    assert [message["sequence"] for message in plan.incremental_messages] == [1, 2]

    transport = _Transport()
    result = asyncio.run(
        ConversationExecutor(transport).compact(
            model_key="source::model",
            plan=plan,
            timeout_seconds=30,
            max_output_tokens=100,
        )
    )

    assert result.content == "The user and assistant discussed Rocky."
    assert result.provider_request_id == "summary-request-1"
    assert len(result.prompt_sha256) == 64
    assert len(result.input_sha256) == 64
    assert "tools" not in transport.calls[0][0]
    assert result.input_sha256 == hashlib.sha256(
        transport.calls[0][0]["messages"][1]["content"].encode("utf-8")
    ).hexdigest()
