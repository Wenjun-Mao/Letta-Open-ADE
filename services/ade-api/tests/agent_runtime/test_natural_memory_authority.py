"""Mode-independent inherited authority and narrow conflict contrasts."""

from __future__ import annotations

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.natural_memory_policy import (
    prepare_natural_memory_review,
)
from ade_api.features.agent_runtime.natural_memory_review import (
    parse_natural_review_decision,
)

SUBJECT = "00000000-0000-0000-0000-000000000001"


def _message(sequence: int, role: str, content: str) -> dict:
    return {
        "id": f"00000000-0000-0000-0000-{sequence:012d}",
        "sequence": sequence,
        "role": role,
        "content": content,
        "run_id": "run-current" if sequence == 4 else "run-prior",
    }


def _coffee(mode: str, current_quote: str) -> dict:
    evidence = {"mode": mode, "current_quote": current_quote}
    if mode == "endorse_assistant":
        evidence.update(support_handle="A1", support_quote="Do you like coffee?")
    elif mode == "resolve_user":
        evidence.update(support_handle="U1", support_quote="I like coffee")
    return {
        "kind": "subject_add",
        "fact_type": "person.preference",
        "qualifier": "drink",
        "value": "coffee",
        "evidence": evidence,
    }


def _toronto() -> dict:
    return {
        "kind": "subject_add",
        "fact_type": "person.current_location",
        "value": "Toronto",
        "evidence": {"mode": "direct", "current_quote": "I now live in Toronto"},
    }


def _pet_name_fact(value: str = "Roxy") -> dict:
    return {
        "id": "fact-roxy",
        "subject_id": SUBJECT,
        "entity_id": "pet-roxy",
        "fact_type": "pet.name",
        "qualifier": None,
        "normalized_key": "pet.name|pet-roxy",
        "value": value,
        "status": "active",
        "version": 1,
        "current_revision_id": "revision-roxy",
    }


def _prepare(decisions: list[dict], *, prior: str, current: str):
    messages = [
        _message(2, "user", prior),
        _message(3, "assistant", "Do you like coffee?"),
        _message(4, "user", current),
    ]
    return prepare_natural_memory_review(
        decision=parse_natural_review_decision({"decisions": decisions}),
        subject_id=SUBJECT,
        current_user_message=messages[-1],
        available_messages=messages,
        facts=[],
        entities=[{"id": SUBJECT, "subject_id": SUBJECT, "kind": "subject"}],
        candidate_reply="Okay.",
    )


@pytest.mark.parametrize(
    "prior",
    [
        "I like coffee. Do not save that.",
        "I might like coffee.",
        "I withdraw my coffee preference.",
    ],
)
def test_terse_assent_cannot_launder_inherited_restriction(prior: str) -> None:
    with pytest.raises(RuntimeValidationError, match="Inherited"):
        _prepare([_coffee("endorse_assistant", "Yes")], prior=prior, current="Yes")


@pytest.mark.parametrize(
    "prior",
    [
        "I like coffee. Do not save that.",
        "I might like coffee.",
        "I withdraw my coffee preference.",
    ],
)
def test_direct_value_fragment_cannot_launder_inherited_restriction(prior: str) -> None:
    with pytest.raises(RuntimeValidationError, match="Inherited"):
        _prepare([_coffee("direct", "coffee")], prior=prior, current="coffee")


def test_fresh_assertion_and_explicit_save_intent_are_distinct() -> None:
    for prior in ("I might like coffee.", "I withdraw my coffee preference."):
        review = _prepare(
            [_coffee("direct", "I like coffee")], prior=prior, current="I like coffee"
        )
        assert [operation.value for operation in review.operations] == ["coffee"]
    with pytest.raises(RuntimeValidationError, match="no-save"):
        _prepare(
            [_coffee("direct", "I like coffee")],
            prior="I like coffee. Do not save that.",
            current="I like coffee",
        )
    permitted = _prepare(
        [_coffee("direct", "I like coffee. You can save that now.")],
        prior="I like coffee. Do not save that.",
        current="I like coffee. You can save that now.",
    )
    assert [operation.value for operation in permitted.operations] == ["coffee"]
    endorsed = _prepare(
        [_coffee("endorse_assistant", "Yes. You can save that now.")],
        prior="I like coffee. Do not save that.",
        current="Yes. You can save that now.",
    )
    assert [operation.value for operation in endorsed.operations] == ["coffee"]
    with pytest.raises(RuntimeValidationError, match="Inherited no-save"):
        _prepare(
            [_coffee("endorse_assistant", "Yes")],
            prior="I like coffee. Do not save that.",
            current="Yes. You can save that now.",
        )
    with pytest.raises(RuntimeValidationError, match="Inherited no-save"):
        _prepare(
            [_coffee("endorse_assistant", "Yes. You can save tea now.")],
            prior="I like coffee. Do not save that.",
            current="Yes. You can save tea now.",
        )
    with pytest.raises(RuntimeValidationError, match="Inherited no-save"):
        _prepare(
            [_coffee("endorse_assistant", "Yes. I like tea. You can save that now.")],
            prior="I like coffee. Do not save that.",
            current="Yes. I like tea. You can save that now.",
        )


def test_intervening_user_restriction_binds_earlier_claim() -> None:
    messages = [
        _message(1, "user", "I like coffee"),
        _message(2, "user", "Do not save that"),
        _message(3, "assistant", "Do you like coffee?"),
        _message(4, "user", "Coffee"),
    ]
    decision = parse_natural_review_decision(
        {
            "decisions": [
                {
                    **_coffee("resolve_user", "Coffee"),
                    "evidence": {
                        "mode": "resolve_user",
                        "current_quote": "Coffee",
                        "support_handle": "U1",
                        "support_quote": "I like coffee",
                    },
                }
            ]
        }
    )
    with pytest.raises(RuntimeValidationError, match="Inherited no-save"):
        prepare_natural_memory_review(
            decision=decision,
            subject_id=SUBJECT,
            current_user_message=messages[-1],
            available_messages=messages,
            facts=[],
            entities=[{"id": SUBJECT, "subject_id": SUBJECT, "kind": "subject"}],
            candidate_reply="Okay.",
        )


def test_restricted_coffee_does_not_block_independent_residence() -> None:
    prior = "I like coffee. Do not save that."
    current = "Yes. I now live in Toronto."
    result = _prepare([_toronto()], prior=prior, current=current)
    assert [operation.value for operation in result.operations] == ["Toronto"]
    for decisions in (
        [_coffee("endorse_assistant", "Yes"), _toronto()],
        [_toronto(), _coffee("endorse_assistant", "Yes")],
    ):
        with pytest.raises(RuntimeValidationError, match="Inherited"):
            _prepare(decisions, prior=prior, current=current)


def test_unrelated_prior_restriction_does_not_veto_new_claim() -> None:
    result = _prepare(
        [_coffee("endorse_assistant", "Yes")],
        prior="I like tea. Do not save that.",
        current="Yes",
    )
    assert [operation.value for operation in result.operations] == ["coffee"]
    result_with_named_restriction = _prepare(
        [_coffee("endorse_assistant", "Yes")],
        prior="I like coffee. Do not save that tea claim.",
        current="Yes",
    )
    assert [
        operation.value for operation in result_with_named_restriction.operations
    ] == ["coffee"]


def test_current_named_no_save_does_not_attach_to_previous_claim() -> None:
    result = _prepare(
        [_coffee("direct", "I like coffee")],
        prior="I like tea.",
        current="I like coffee. Do not save that tea claim.",
    )
    assert [operation.value for operation in result.operations] == ["coffee"]


@pytest.mark.parametrize(
    ("stored_name", "answer", "conflicts"),
    [
        ("Roxy", "Your dog is Rocky.", True),
        ("Rocky", "Your dog is Rocky.", False),
        ("Roxy", "Your dog is Roxy.", False),
        ("Roxy", "Roxy. What else is new?", False),
    ],
)
def test_grounded_conflict_respects_full_sentence_answer(
    stored_name: str, answer: str, conflicts: bool
) -> None:
    current = _message(4, "user", "What is my dog's name?")
    decision = parse_natural_review_decision(
        {
            "decisions": [
                {
                    "kind": "conflict",
                    "current_quote": "What is my dog's name?",
                    "candidate_reply_quote": answer,
                    "references": ["F1"],
                }
            ]
        }
    )
    with pytest.raises(RuntimeValidationError) as error:
        prepare_natural_memory_review(
            decision=decision,
            subject_id=SUBJECT,
            current_user_message=current,
            available_messages=[current],
            facts=[_pet_name_fact(stored_name)],
            entities=[{"id": SUBJECT, "subject_id": SUBJECT, "kind": "subject"}],
            candidate_reply=answer,
        )
    assert error.value.detail_code == (
        "natural_memory_reply_conflict" if conflicts else "natural_review_semantic"
    )


def test_correct_full_sentence_with_no_change_review_is_deliverable() -> None:
    current = _message(4, "user", "What is my dog's name?")
    result = prepare_natural_memory_review(
        decision=parse_natural_review_decision({"decisions": []}),
        subject_id=SUBJECT,
        current_user_message=current,
        available_messages=[current],
        facts=[_pet_name_fact()],
        entities=[{"id": SUBJECT, "subject_id": SUBJECT, "kind": "subject"}],
        candidate_reply="Your dog is Roxy. What else is new?",
    )
    assert result.operations == ()


def test_conflict_references_only_read_only_snapshot_handles() -> None:
    with pytest.raises(RuntimeValidationError) as error:
        parse_natural_review_decision(
            {
                "decisions": [
                    {
                        "kind": "conflict",
                        "current_quote": "What is my dog's name?",
                        "candidate_reply_quote": "Rocky",
                        "references": ["U1"],
                    }
                ]
            }
        )
    assert error.value.detail_code == "natural_review_schema"
