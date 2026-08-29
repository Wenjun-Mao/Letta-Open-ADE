from __future__ import annotations

import pytest

from ade_api.features.agent_runtime_v3.context import (
    ContextBudget,
    build_context,
    estimate_tokens,
)


def test_context_keeps_current_user_and_drops_oldest_recent_messages() -> None:
    recent = [
        {"id": f"message-{index}", "role": "user", "content": "旧消息" * 80}
        for index in range(5)
    ]
    context = build_context(
        system_prompt="system",
        persona="persona",
        active_facts=[],
        retrieved_facts=[],
        recent_messages=recent,
        current_user_content="当前消息必须保留",
        budget=ContextBudget(
            context_window=1_000,
            max_output_tokens=200,
            tool_schema_tokens=100,
            recent_tokens=150,
        ),
    )
    assert context.messages[-1] == {"role": "user", "content": "当前消息必须保留"}
    assert context.omitted_message_ids
    assert context.estimated_input_tokens <= 650


def test_context_rejects_mandatory_input_that_cannot_fit() -> None:
    with pytest.raises(ValueError, match="mandatory prompt"):
        build_context(
            system_prompt="s" * 1_000,
            persona="persona",
            active_facts=[],
            retrieved_facts=[],
            recent_messages=[],
            current_user_content="u" * 2_000,
            budget=ContextBudget(
                context_window=800,
                max_output_tokens=100,
                tool_schema_tokens=50,
            ),
        )


def test_token_estimate_is_multilingual_and_nonzero() -> None:
    assert estimate_tokens("张伟") > 0
    assert estimate_tokens("") == 0
