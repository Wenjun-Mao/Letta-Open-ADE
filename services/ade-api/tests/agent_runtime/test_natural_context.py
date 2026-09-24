from __future__ import annotations

import pytest

from ade_api.features.agent_runtime.context import (
    ContextBudget,
    ConversationHistoryMetadata,
)
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.natural_context import (
    build_natural_context,
    full_lifecycle_snapshot_fits,
)


def _fact(number: int, *, size: int = 48) -> dict:
    return {
        "id": f"fact-{number}",
        "subject_id": "subject",
        "entity_id": "subject",
        "normalized_key": f"person.preference|subject|{number:03d}",
        "value": f"memory-{number}-" + "x" * size,
        "version": 1,
        "status": "inactive" if number % 3 == 0 else "active",
    }


def _messages() -> list[dict]:
    return [
        {
            "id": "u1",
            "run_id": "r1",
            "sequence": 1,
            "role": "user",
            "content": "The afternoon product-role interview is my choice.",
        },
        {
            "id": "a1",
            "run_id": "r1",
            "sequence": 2,
            "role": "assistant",
            "content": "You chose the afternoon product-role interview.",
        },
        {
            "id": "u2",
            "run_id": "r2",
            "sequence": 3,
            "role": "user",
            "content": "My dog Roxy is a Husky.",
        },
        {
            "id": "a2",
            "run_id": "r2",
            "sequence": 4,
            "role": "assistant",
            "content": "Roxy is your Husky.",
        },
    ]


def _build(variant: str, *, facts: list[dict], retrieved: list[dict] | None = None):
    return build_natural_context(
        variant=variant,
        system_prompt="Policy",
        persona="Companion",
        current_user={
            "id": "u3",
            "run_id": "r3",
            "sequence": 5,
            "role": "user",
            "content": "What did I choose for the interview?",
        },
        eligible_recent_messages=_messages(),
        lifecycle_facts=facts,
        retrieved_facts=retrieved or [],
        entities=[{"id": "subject", "kind": "subject", "label": ""}],
        summary_content="Earlier I chose the afternoon interview.",
        history_metadata=ConversationHistoryMetadata(
            completed_user_turns=2, summary_through_sequence=0
        ),
        budget=ContextBudget(
            context_window=4096,
            max_output_tokens=512,
            tool_schema_tokens=128,
        ),
        reviewer_suffix_limit=640,
    )


def test_pressure_a_withholds_optional_narrative_b_keeps_shared_suffix() -> None:
    facts = [_fact(index, size=240) for index in range(48)]
    assert not full_lifecycle_snapshot_fits(
        system_prompt="Policy",
        persona="Companion",
        current_user_content="What did I choose for the interview?",
        lifecycle_facts=facts,
        history_metadata=ConversationHistoryMetadata(
            completed_user_turns=2, summary_through_sequence=0
        ),
        input_limit=ContextBudget(
            context_window=4096, max_output_tokens=512, tool_schema_tokens=128
        ).input_limit,
    )
    a = _build("A", facts=facts, retrieved=[facts[0]])
    a0 = _build("A0", facts=facts, retrieved=[facts[0]])
    b = _build("B", facts=facts, retrieved=[facts[0]])
    assert a.lifecycle_withheld is True
    assert [message["id"] for message in a.source_messages] == ["u3"]
    assert a.context.omitted_message_ids == ["u1", "a1", "u2", "a2"]
    assert b.lifecycle_withheld is False
    assert [message["id"] for message in b.source_messages] == [
        "u1",
        "a1",
        "u2",
        "a2",
        "u3",
    ]
    assert b.context.retrieved_fact_ids == ["fact-0"]
    assert "INACTIVE" in b.context.messages[0]["content"]
    assert a0.lifecycle_withheld is True
    assert a0.context.messages == a.context.messages
    assert a0.source_messages == a.source_messages
    assert a0.context.retrieved_fact_ids == a.context.retrieved_fact_ids == ["fact-0"]
    assert a0.context.omitted_message_ids == a.context.omitted_message_ids
    assert a0.context.section_tokens == a.context.section_tokens
    assert "Prior dialogue and summary WITHHELD" in a.context.messages[0]["content"]
    assert (
        "The afternoon product-role interview" not in a.context.messages[0]["content"]
    )
    assert a.context.messages != b.context.messages


def test_a0_preserves_a_raw_cutoff_and_nonsummary_sections() -> None:
    facts = [_fact(index) for index in range(12)]
    assert full_lifecycle_snapshot_fits(
        system_prompt="Policy",
        persona="Companion",
        current_user_content="What did I choose for the interview?",
        lifecycle_facts=facts,
        history_metadata=ConversationHistoryMetadata(
            completed_user_turns=2, summary_through_sequence=0
        ),
        input_limit=ContextBudget(
            context_window=4096, max_output_tokens=512, tool_schema_tokens=128
        ).input_limit,
    )
    a = _build("A", facts=facts)
    a0 = _build("A0", facts=facts)
    assert [message["id"] for message in a.source_messages] == [
        message["id"] for message in a0.source_messages
    ]
    assert a.context.retrieved_fact_ids == a0.context.retrieved_fact_ids
    assert a.context.omitted_message_ids == a0.context.omitted_message_ids
    assert (
        a.context.section_tokens["lifecycle_views"]
        == a0.context.section_tokens["lifecycle_views"]
    )
    assert a.context.section_tokens["conversation_summary"] > 0
    assert a0.context.section_tokens["conversation_summary"] == 0
    assert (
        a.context.messages[0]["content"].replace(
            "\n\nConversation summary (attributed, not certified current):\n"
            "Earlier I chose the afternoon interview.",
            "",
        )
        == a0.context.messages[0]["content"]
    )


def test_b_admits_only_whole_records() -> None:
    facts = [_fact(index, size=300) for index in range(12)]
    b = _build("B", facts=facts, retrieved=facts)
    system = b.context.messages[0]["content"]
    for fact in facts:
        if fact["id"] in b.context.retrieved_fact_ids:
            assert fact["value"] in system
        else:
            assert fact["value"] not in system
    assert len(b.context.retrieved_fact_ids) <= 8


@pytest.mark.parametrize("count", [0, 12, 48, 128, 256])
@pytest.mark.parametrize("size", [24, 240])
def test_full_snapshot_whole_request_boundary(count: int, size: int) -> None:
    facts = [_fact(index, size=size) for index in range(count)]

    def assemble(context_window: int, variant: str = "A0"):
        return build_natural_context(
            variant=variant,
            system_prompt="Policy",
            persona="Companion",
            current_user={
                "id": "u3",
                "run_id": "r3",
                "sequence": 5,
                "role": "user",
                "content": "What did I choose for the interview?",
            },
            eligible_recent_messages=_messages(),
            lifecycle_facts=facts,
            retrieved_facts=facts[:1],
            entities=[{"id": "subject", "kind": "subject", "label": ""}],
            summary_content="Earlier I chose the afternoon interview.",
            history_metadata=ConversationHistoryMetadata(
                completed_user_turns=2, summary_through_sequence=0
            ),
            budget=ContextBudget(
                context_window=context_window,
                max_output_tokens=512,
                tool_schema_tokens=128,
            ),
            reviewer_suffix_limit=640,
        )

    low, high = 0, 65_536
    assert assemble(high).lifecycle_withheld is False
    while low + 1 < high:
        middle = (low + high) // 2
        try:
            fits = not assemble(middle).lifecycle_withheld
        except RuntimeValidationError:
            fits = False
        if fits:
            high = middle
        else:
            low = middle
    try:
        below = assemble(high - 1)
    except RuntimeValidationError as error:
        # At zero records the selective-view marker can itself exceed
        # the limit immediately below the tiny empty-snapshot boundary.
        assert count == 0
        assert error.detail_code == "natural_context_suffix_overflow"
        below = None
    at_boundary = assemble(high)
    control_a = assemble(high, "A")
    try:
        recent_first = assemble(high, "B")
    except RuntimeValidationError as error:
        # The empty selective-view marker is larger than the empty snapshot.
        assert count == 0
        assert error.detail_code == "natural_context_suffix_overflow"
        recent_first = None
    if below is not None:
        assert below.lifecycle_withheld is True
        control_below = assemble(high - 1, "A")
        assert control_below.context.messages == below.context.messages
        assert control_below.source_messages == below.source_messages
        assert (
            control_below.context.retrieved_fact_ids == below.context.retrieved_fact_ids
        )
    assert at_boundary.lifecycle_withheld is False
    assert control_a.lifecycle_withheld is False
    assert [item["id"] for item in control_a.source_messages] == [
        item["id"] for item in at_boundary.source_messages
    ]
    assert (
        control_a.context.retrieved_fact_ids == at_boundary.context.retrieved_fact_ids
    )
    assert len(at_boundary.context.retrieved_fact_ids) == count
    if recent_first is not None:
        assert recent_first.lifecycle_withheld is False
        assert len(recent_first.context.retrieved_fact_ids) <= 8
        assert (
            recent_first.context.estimated_input_tokens
            <= ContextBudget(
                context_window=high,
                max_output_tokens=512,
                tool_schema_tokens=128,
            ).input_limit
        )
    assert (
        at_boundary.context.estimated_input_tokens
        <= ContextBudget(
            context_window=high,
            max_output_tokens=512,
            tool_schema_tokens=128,
        ).input_limit
    )
