from __future__ import annotations

import pytest

from ade_api.features.agent_runtime.context import (
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
            context_window=1_400,
            max_output_tokens=200,
            tool_schema_tokens=100,
            recent_tokens=150,
        ),
    )
    assert context.messages[-1] == {"role": "user", "content": "当前消息必须保留"}
    assert context.omitted_message_ids
    assert context.estimated_input_tokens <= 844


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
    assert "Exact completed conversation rounds before current: 40" in system_message
    assert (
        "Use this exact integer for count questions; do not estimate" in system_message
    )
    assert "Summary covers messages through sequence: 48" in system_message
    assert "metadata above overrides the narrative summary" in system_message


def test_context_labels_bound_memory_as_current_user_facts() -> None:
    context = build_context(
        system_prompt="system",
        persona="My name is Lin Xiaotang.",
        active_facts=[
            {
                "id": "fact-name",
                "version": 1,
                "key": "person.name|subject-1",
                "value": "Alice",
            }
        ],
        retrieved_facts=[
            {
                "id": "fact-city",
                "version": 1,
                "key": "person.location|subject-1",
                "value": "Toronto",
            }
        ],
        recent_messages=[],
        current_user_content="你还记得我的名字吗？",
        budget=ContextBudget(
            context_window=2_000,
            max_output_tokens=200,
            tool_schema_tokens=100,
        ),
    )

    system_message = context.messages[0]["content"]
    assert "bound memory-subject profile and search results" in system_message
    assert "never the assistant persona" in system_message
    assert "state its concrete value" in system_message
    assert (
        "Active facts about the current user (bound memory subject)" in system_message
    )
    assert (
        "Retrieved older facts about the current user (bound memory subject)"
        in system_message
    )


def test_removal_reply_contract_does_not_promise_future_suppression() -> None:
    context = build_context(
        system_prompt="system",
        persona="persona",
        active_facts=[
            {
                "id": "fact-drink",
                "version": 2,
                "key": "person.preference|subject-1|drink",
                "value": "绿茶",
            }
        ],
        retrieved_facts=[],
        recent_messages=[],
        current_user_content="请从已保存的信息中移除我喜欢喝绿茶这件事。",
        budget=ContextBudget(
            context_window=2_000,
            max_output_tokens=200,
            tool_schema_tokens=100,
        ),
    )
    system_message = context.messages[0]["content"]
    assert "only after your reply" in system_message
    assert "Earlier messages, summaries, and revision history remain" in system_message
    assert "Acknowledge the request as pending review" in system_message
    assert "do not imply it already succeeded" in system_message
    assert "promise that the detail can never reappear" in system_message


def test_future_check_in_request_does_not_become_a_memory_promise() -> None:
    context = build_context(
        system_prompt="system",
        persona="persona",
        active_facts=[],
        retrieved_facts=[],
        recent_messages=[],
        current_user_content="下次聊天时你能问问我还好吗？",
        budget=ContextBudget(
            context_window=2_000,
            max_output_tokens=200,
            tool_schema_tokens=100,
        ),
    )
    system_message = context.messages[0]["content"]
    assert "cannot initiate a future conversation" in system_message
    assert (
        "A concern or request to ask next time is not durable memory" in system_message
    )
    assert "Do not promise to remember it" in system_message
    assert "offer to listen or ask about it now" in system_message
