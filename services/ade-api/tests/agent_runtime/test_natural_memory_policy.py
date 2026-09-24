from __future__ import annotations

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.natural_memory_policy import (
    prepare_natural_memory_review,
)
from ade_api.features.agent_runtime.natural_memory_review import (
    NaturalReviewDecision,
    bind_natural_sources,
)


SUBJECT = "00000000-0000-0000-0000-000000000001"
USER = "00000000-0000-0000-0000-000000000002"
ASSISTANT = "00000000-0000-0000-0000-000000000003"
FACT = "00000000-0000-0000-0000-000000000004"


def _source(quote: str, *, role: str = "user_assertion", message_id: str = USER):
    return {"message_id": message_id, "quote": quote, "role": role}


def _add(claim_id: str, value: str, quote: str, **overrides):
    return {
        "claim_id": claim_id,
        "operation": "add",
        "fact_type": "person.current_location",
        "value": value,
        "evidence_quote": quote,
        "sources": [_source(quote)],
        **overrides,
    }


def _disposition(claim_id: str, outcome: str, reason: str, **overrides):
    return {"claim_id": claim_id, "outcome": outcome, "reason": reason, **overrides}


def _prepare(
    payload: dict,
    *,
    current: str,
    prior_assistant: str | None = None,
    facts: list[dict] | None = None,
    candidate_reply: str = "Okay.",
):
    messages = [{"id": USER, "role": "user", "content": current}]
    if prior_assistant is not None:
        messages.insert(
            0, {"id": ASSISTANT, "role": "assistant", "content": prior_assistant}
        )
    return prepare_natural_memory_review(
        decision=NaturalReviewDecision.model_validate(payload),
        subject_id=SUBJECT,
        current_user_message=messages[-1],
        available_messages=messages,
        facts=facts or [],
        entities=[{"id": SUBJECT, "subject_id": SUBJECT, "kind": "subject"}],
        candidate_reply=candidate_reply,
    )


def test_mixed_deferred_pet_and_valid_residence_stages_only_survivors() -> None:
    text = "My dog is Rocky, but don't save that. I now live in Toronto."
    payload = {
        "proposals": [
            {
                "claim_id": "pet",
                "operation": "add",
                "fact_type": "pet.name",
                "value": "Rocky",
                "entity_ref": "new:rocky",
                "evidence_quote": "My dog is Rocky",
                "sources": [_source("My dog is Rocky")],
            },
            _add("residence", "Toronto", "I now live in Toronto"),
        ],
        "claim_dispositions": [
            _disposition("pet", "defer", "no_save"),
            _disposition("residence", "allow", "supported"),
        ],
    }
    prepared = _prepare(payload, current=text)
    assert [item.proposal.claim_id for item in prepared.operations] == ["residence"]
    assert prepared.new_entities == ()
    assert prepared.deferred_claims == ({"claim_id": "pet", "reason": "no_save"},)

    payload["claim_dispositions"][0] = _disposition("pet", "allow", "supported")
    with pytest.raises(RuntimeValidationError, match="No-save"):
        _prepare(payload, current=text)


def test_no_save_for_dog_does_not_block_residence_in_same_sentence() -> None:
    prepared = _prepare(
        {
            "proposals": [_add("residence", "Toronto", "I live in Toronto")],
            "claim_dispositions": [_disposition("residence", "allow", "supported")],
        },
        current="Don't save Rocky the dog, but I live in Toronto.",
    )
    assert len(prepared.operations) == 1


def test_all_deferred_has_no_entities_or_writes() -> None:
    prepared = _prepare(
        {
            "proposals": [_add("residence", "Toronto", "I live in Toronto")],
            "claim_dispositions": [
                _disposition("residence", "defer", "unresolved_reference")
            ],
        },
        current="I live in Toronto",
    )
    assert prepared.operations == ()
    assert prepared.new_entities == ()


def test_independent_preference_assertions_share_category_not_mutation_identity() -> (
    None
):
    payload = {
        "proposals": [
            {
                "claim_id": claim_id,
                "operation": "add",
                "fact_type": "person.preference",
                "qualifier": "drink",
                "value": value,
                "evidence_quote": value,
                "sources": [_source(value)],
            }
            for claim_id, value in (
                ("morning", "coffee in the morning"),
                ("evening", "flower tea in the evening"),
            )
        ],
        "claim_dispositions": [
            _disposition("morning", "allow", "supported"),
            _disposition("evening", "allow", "supported"),
        ],
    }
    prepared = _prepare(
        payload,
        current="I prefer coffee in the morning and flower tea in the evening.",
    )
    assert len(prepared.operations) == 2
    assert len({item.normalized_key for item in prepared.operations}) == 2
    assert all("|assertion:" in item.normalized_key for item in prepared.operations)
    payload["proposals"][1]["value"] = "coffee in the morning"
    payload["proposals"][1]["evidence_quote"] = "coffee in the morning"
    payload["proposals"][1]["sources"] = [_source("coffee in the morning")]
    with pytest.raises(RuntimeValidationError, match="Equivalent preference"):
        _prepare(payload, current="I prefer coffee in the morning.")


def test_assistant_referent_requires_current_user_endorsement() -> None:
    text = "Yes, Toronto is right."
    payload = {
        "proposals": [
            _add(
                "residence",
                "Toronto",
                "Yes, Toronto is right",
                sources=[
                    _source("Yes, Toronto is right", role="user_endorsement"),
                    _source(
                        "You live in Toronto",
                        role="assistant_referent",
                        message_id=ASSISTANT,
                    ),
                ],
            )
        ],
        "claim_dispositions": [_disposition("residence", "allow", "supported")],
    }
    prepared = _prepare(payload, current=text, prior_assistant="You live in Toronto.")
    assert [source.authority_role for source in prepared.operations[0].sources] == [
        "user_endorsement",
        "assistant_referent",
    ]
    proposal = NaturalReviewDecision.model_validate(payload).proposals[0]
    with pytest.raises(RuntimeValidationError, match="outside its bundle"):
        bind_natural_sources(
            proposal,
            current_user_message={"id": USER, "role": "user", "content": text},
            available_messages=[{"id": USER, "role": "user", "content": text}],
        )


def test_correction_can_invalidate_without_inventing_new_value() -> None:
    fact = {
        "id": FACT,
        "subject_id": SUBJECT,
        "entity_id": SUBJECT,
        "fact_type": "person.current_location",
        "qualifier": None,
        "normalized_key": f"person.current_location|{SUBJECT}",
        "value": "Beijing",
        "status": "active",
        "version": 1,
    }
    prepared = _prepare(
        {
            "proposals": [
                {
                    "claim_id": "invalidate",
                    "operation": "revise",
                    "reason": "correct",
                    "fact_id": FACT,
                    "expected_version": 1,
                    "value": None,
                    "evidence_quote": "Beijing was wrong",
                    "sources": [_source("Beijing was wrong")],
                }
            ],
            "claim_dispositions": [_disposition("invalidate", "allow", "supported")],
        },
        current="Beijing was wrong. I won't say where I live.",
        facts=[fact],
    )
    assert prepared.operations[0].value is None
    assert prepared.operations[0].next_status == "inactive"
    assert prepared.operations[0].revision_reason == "invalidated"


def test_reply_conflict_is_terminal_and_bound_to_visible_candidate() -> None:
    payload = {
        "proposals": [_add("residence", "Toronto", "I live in Toronto")],
        "claim_dispositions": [
            _disposition(
                "residence",
                "contradiction",
                "reply_conflict",
                candidate_reply_quote="You live in Beijing",
            )
        ],
    }
    with pytest.raises(RuntimeValidationError, match="contradicts"):
        _prepare(
            payload,
            current="I live in Toronto",
            candidate_reply="You live in Beijing.",
        )
    with pytest.raises(RuntimeValidationError, match="visible candidate span"):
        _prepare(payload, current="I live in Toronto")


@pytest.mark.parametrize("reverse", [False, True])
def test_add_forget_same_slot_rejected_independent_of_order(reverse: bool) -> None:
    fact = {
        "id": FACT,
        "subject_id": SUBJECT,
        "entity_id": SUBJECT,
        "fact_type": "person.current_location",
        "qualifier": None,
        "normalized_key": f"person.current_location|{SUBJECT}",
        "value": "Beijing",
        "status": "active",
        "version": 1,
    }
    add = _add("add", "Toronto", "I live in Toronto")
    forget = {
        "claim_id": "forget",
        "operation": "forget",
        "fact_id": FACT,
        "expected_version": 1,
        "value": None,
        "evidence_quote": "Forget my old city",
        "sources": [_source("Forget my old city")],
    }
    proposals = [add, forget]
    if reverse:
        proposals.reverse()
    with pytest.raises(RuntimeValidationError):
        _prepare(
            {
                "proposals": proposals,
                "claim_dispositions": [
                    _disposition("add", "allow", "supported"),
                    _disposition("forget", "allow", "supported"),
                ],
            },
            current="Forget my old city. I live in Toronto",
            facts=[fact],
        )
