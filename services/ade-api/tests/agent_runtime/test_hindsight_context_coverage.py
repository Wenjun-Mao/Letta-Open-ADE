"""The planner owns a complete summary-prefix/raw-suffix dialogue partition."""

from dataclasses import replace

import pytest

from ade_api.features.agent_runtime.compaction import plan_compaction
from ade_api.features.agent_runtime.context import ContextBudget, estimate_tokens
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.hindsight_context import (
    build_hindsight_context,
    validate_input,
)


DEFINITION = {
    "id": "definition",
    "prompt_content": "Synthetic authored instructions",
    "persona_content": "Synthetic persona",
}
BUDGET = ContextBudget(
    context_window=65536,
    max_output_tokens=512,
    tool_schema_tokens=256,
)


def history(contents):
    return [
        {
            "id": f"message-{index}",
            "sequence": index,
            "role": "user" if index % 2 else "assistant",
            "content": content,
            "run_id": f"run-{(index + 1) // 2}",
        }
        for index, content in enumerate(contents, 1)
    ]


def current_after(messages, *, content="Current input"):
    return {
        "id": "current",
        "sequence": max((row["sequence"] for row in messages), default=0) + 1,
        "role": "user",
        "content": content,
        "run_id": "current-run",
    }


def compose(
    messages,
    *,
    budget=BUDGET,
    summary=None,
    current=None,
    memories=(),
    definition=DEFINITION,
):
    return build_hindsight_context(
        definition=definition,
        messages=messages,
        current_user=current or current_after(messages),
        summary=summary,
        memories=list(memories),
        budget=budget,
        tools={},
        provider_adapter="",
        model_key="synthetic::character",
    )


def local_ids(context):
    return [
        identity
        for part in context.components
        if part["kind"] == "local_dialogue"
        for identity in part["source_ids"]
    ]


def planned_summary(plan):
    return {
        "id": "new-summary",
        "through_sequence": plan.through_sequence,
        "content": "Synthetic summary, not a semantic quality claim",
    }


def test_review_reproducer_retains_both_messages_when_no_compaction_was_planned():
    messages = history(["x" * 5966, "y" * 5966])
    current = current_after(messages)
    assert (
        plan_compaction(
            messages=[*messages, current],
            current_user_message_id=current["id"],
            summary=None,
            recent_token_budget=3000,
            compaction_input_token_budget=BUDGET.input_limit,
        )
        is None
    )
    context = compose(messages)
    assert local_ids(context) == [row["id"] for row in messages]
    assert context.omitted_message_ids == []


@pytest.mark.parametrize(
    "text",
    ["ascii" * 80, "\u4e2d\u6587" * 100, '\\"\n' * 100],
    ids=["ascii", "mandarin", "escaped"],
)
@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_summary_and_raw_suffix_cover_history_at_shared_budget_threshold(text, delta):
    messages = history([text, text])
    current = current_after(messages)
    tokens = sum(
        estimate_tokens(f"{row['role']}: {row['content']}") for row in messages
    )
    budget = replace(BUDGET, recent_tokens=tokens + delta)
    plan = plan_compaction(
        messages=[*messages, current],
        current_user_message_id=current["id"],
        summary=None,
        recent_token_budget=budget.recent_tokens,
        compaction_input_token_budget=budget.input_limit,
    )
    assert (plan is not None) == (delta < 0)
    context = compose(
        messages, budget=budget, summary=planned_summary(plan) if plan else None
    )
    prefix = list(plan.source_message_ids) if plan else []
    assert prefix + local_ids(context) == [row["id"] for row in messages]
    assert context.omitted_message_ids == []


@pytest.mark.parametrize("count", [11, 64, 65])
def test_ten_message_suffix_limit_applies_only_after_compaction_triggers(count):
    messages = history(["short"] * count)
    current = current_after(messages)
    plan = plan_compaction(
        messages=[*messages, current],
        current_user_message_id=current["id"],
        summary=None,
        recent_token_budget=BUDGET.recent_tokens,
        compaction_input_token_budget=BUDGET.input_limit,
    )
    assert (plan is not None) == (count > 64)
    context = compose(messages, summary=planned_summary(plan) if plan else None)
    assert len(local_ids(context)) == (10 if count > 64 else count)
    prefix = list(plan.source_message_ids) if plan else []
    assert prefix + local_ids(context) == [row["id"] for row in messages]


def test_summary_extension_and_failed_run_user_input_keep_ordered_coverage():
    messages = history(["first", "reply", "previous", "unanswered", "newer"])
    messages[3]["role"] = "user"
    current = current_after(messages)
    previous = {
        "id": "prior-summary",
        "version": 1,
        "through_sequence": 3,
        "content": "Prior summary",
    }
    plan = plan_compaction(
        messages=[*messages, current],
        current_user_message_id=current["id"],
        summary=previous,
        recent_token_budget=4,
        compaction_input_token_budget=BUDGET.input_limit,
    )
    assert plan.previous_summary_id == "prior-summary"
    assert [row["sequence"] for row in plan.incremental_messages] == [4]
    context = compose(
        list(reversed(messages)),
        budget=replace(BUDGET, recent_tokens=4),
        summary=planned_summary(plan),
    )
    assert list(plan.source_message_ids) + local_ids(context) == [
        row["id"] for row in messages
    ]
    assert current["id"] not in plan.source_message_ids


def test_oversized_latest_message_is_summarized_instead_of_discarded():
    messages = history(["short", "long" * 500])
    current = current_after(messages)
    plan = plan_compaction(
        messages=[*messages, current],
        current_user_message_id=current["id"],
        summary=None,
        recent_token_budget=100,
        compaction_input_token_budget=BUDGET.input_limit,
    )
    context = compose(
        messages,
        budget=replace(BUDGET, recent_tokens=100),
        summary=planned_summary(plan),
    )
    assert list(plan.source_message_ids) == [row["id"] for row in messages]
    assert local_ids(context) == []


def test_unplanned_oversized_raw_suffix_fails_instead_of_omitting_messages():
    with pytest.raises(RuntimeValidationError) as caught:
        compose(history(["x" * 1000]), budget=replace(BUDGET, recent_tokens=100))
    assert caught.value.detail_code == "context_history_requires_compaction"


def test_optional_recall_is_trimmed_before_any_complete_local_dialogue():
    messages = history(["local user", "local reply"])
    base = compose(messages)
    tight = replace(BUDGET, context_window=base.estimated_input_tokens + 1044)
    assert tight.input_limit == base.estimated_input_tokens + 20
    context = compose(
        messages, budget=tight, memories=[{"id": "optional", "text": "x" * 800}]
    )
    assert context.retrieved_fact_ids == []
    assert local_ids(context) == [row["id"] for row in messages]
    assert context.estimated_input_tokens <= tight.input_limit


@pytest.mark.parametrize("with_summary", [False, True])
def test_full_serialized_overflow_does_not_trim_local_history_or_summary(with_summary):
    contents = ["u" * 2000, "a" * 2000]
    messages = history(
        ["previous user", "previous reply", *contents] if with_summary else contents
    )
    definition = {**DEFINITION, "prompt_content": "p" * 3000}
    current = current_after(messages, content="c" * 5000)
    budget = replace(BUDGET, context_window=4096)
    summary = (
        {"id": "summary", "through_sequence": 2, "content": "Preserved summary"}
        if with_summary
        else None
    )
    validate_input(definition, current["content"], budget)
    with pytest.raises(RuntimeValidationError) as caught:
        compose(
            messages,
            budget=budget,
            definition=definition,
            current=current,
            summary=summary,
        )
    assert caught.value.detail_code == "context_serialized_overflow"
