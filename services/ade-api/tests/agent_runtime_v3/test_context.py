from __future__ import annotations

import pytest

from ade_api.features.agent_runtime_v3.context import (
    ConversationHistoryMetadata,
    ContextBudget,
    build_context,
    conversation_history_metadata,
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


def test_history_metadata_counts_only_completed_user_turns() -> None:
    metadata = conversation_history_metadata(
        messages=[
            {"sequence": 1, "role": "user", "run_id": "completed-1"},
            {"sequence": 2, "role": "assistant", "run_id": "completed-1"},
            {"sequence": 3, "role": "user", "run_id": "failed"},
            {"sequence": 4, "role": "user", "run_id": "completed-2"},
            {"sequence": 5, "role": "assistant", "run_id": "completed-2"},
            {"sequence": 6, "role": "user", "run_id": "current"},
        ],
        current_sequence=6,
        summary_through_sequence=2,
    )

    assert metadata == ConversationHistoryMetadata(
        completed_user_turns=2,
        summary_through_sequence=2,
    )


def test_context_marks_exact_history_metadata_as_authoritative() -> None:
    context = build_context(
        system_prompt="system",
        persona="persona",
        active_facts=[],
        retrieved_facts=[],
        recent_messages=[],
        current_user_content="我们之前聊了多少轮？",
        conversation_summary="模型生成的叙述错误地估计为10轮。",
        history_metadata=ConversationHistoryMetadata(
            completed_user_turns=40,
            summary_through_sequence=48,
        ),
        budget=ContextBudget(
            context_window=2_000,
            max_output_tokens=200,
            tool_schema_tokens=100,
        ),
    )

    system_message = context.messages[0]["content"]
    assert "Conversation history metadata (authoritative)" in system_message
    assert "Completed user turns before current: 40" in system_message
    assert "Summary covers messages through sequence: 48" in system_message
    assert "metadata above overrides the narrative summary" in system_message
