"""Complete-delta mechanics for the revision-5 compact reviewer."""

from __future__ import annotations

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.natural_memory_binding import (
    build_natural_binding_map,
)
from ade_api.features.agent_runtime.natural_memory_policy import (
    prepare_natural_memory_review,
)
from ade_api.features.agent_runtime.natural_memory_review import (
    parse_natural_review_decision,
)

SUBJECT = "00000000-0000-0000-0000-000000000001"
USER = "00000000-0000-0000-0000-000000000002"
ASSISTANT = "00000000-0000-0000-0000-000000000003"
PRIOR = "00000000-0000-0000-0000-000000000004"
FACT = "00000000-0000-0000-0000-000000000005"


def _current(content: str):
    return {
        "id": USER,
        "role": "user",
        "content": content,
        "sequence": 4,
        "run_id": "run-1",
    }


def _prior(role: str, content: str):
    return {
        "id": PRIOR if role == "user" else ASSISTANT,
        "role": role,
        "content": content,
        "sequence": 2,
    }


def _fact(value: str = "morning coffee", status: str = "active"):
    return {
        "id": FACT,
        "subject_id": SUBJECT,
        "entity_id": SUBJECT,
        "fact_type": "person.preference",
        "qualifier": "drink",
        "normalized_key": f"person.preference|{SUBJECT}|drink|assertion:old",
        "value": value,
        "status": status,
        "version": 1,
        "current_revision_id": "00000000-0000-0000-0000-000000000006",
    }


def _subject_add(value: str, quote: str, evidence: dict | None = None):
    return {
        "kind": "subject_add",
        "fact_type": "person.preference",
        "qualifier": "drink",
        "value": value,
        "evidence": evidence or {"mode": "direct", "current_quote": quote},
    }


def _prepare(
    decisions: list[dict],
    *,
    current: str,
    prior: list[dict] | None = None,
    facts: list[dict] | None = None,
    candidate: str = "Okay",
):
    current_message = _current(current)
    return prepare_natural_memory_review(
        decision=parse_natural_review_decision({"decisions": decisions}),
        subject_id=SUBJECT,
        current_user_message=current_message,
        available_messages=[*(prior or []), current_message],
        facts=facts or [],
        entities=[{"id": SUBJECT, "subject_id": SUBJECT, "kind": "subject"}],
        candidate_reply=candidate,
    )


def test_deferral_is_no_write_and_unrelated_residence_survives() -> None:
    text = "I prefer coffee in the morning. Don't save that. I now live in Toronto."
    result = _prepare(
        [
            {"kind": "defer", "current_quote": "Don't save that", "reason": "no_save"},
            {
                "kind": "subject_add",
                "fact_type": "person.current_location",
                "value": "Toronto",
                "evidence": {
                    "mode": "direct",
                    "current_quote": "I now live in Toronto",
                },
            },
        ],
        current=text,
    )
    assert [item.value for item in result.operations] == ["Toronto"]
    assert result.new_entities == ()
    assert result.deferred_claims == (
        {"quote": "Don't save that", "reason": "no_save"},
    )
    with pytest.raises(RuntimeValidationError, match="No-save"):
        _prepare(
            [
                _subject_add("coffee in the morning", "I prefer coffee in the morning"),
                {
                    "kind": "subject_add",
                    "fact_type": "person.current_location",
                    "value": "Toronto",
                    "evidence": {
                        "mode": "direct",
                        "current_quote": "I now live in Toronto",
                    },
                },
            ],
            current=text,
        )


def test_chinese_no_save_is_claim_scoped() -> None:
    result = _prepare(
        [
            {"kind": "defer", "current_quote": "别保存这个", "reason": "no_save"},
            {
                "kind": "subject_add",
                "fact_type": "person.current_location",
                "value": "多伦多",
                "evidence": {"mode": "direct", "current_quote": "我现在住多伦多"},
            },
        ],
        current="早上我喜欢咖啡。别保存这个。我现在住多伦多。",
    )
    assert len(result.operations) == 1
    assert result.operations[0].value == "多伦多"


@pytest.mark.parametrize("mode", ["direct", "resolve_user", "endorse_assistant"])
def test_assistant_only_bare_name_cannot_write_breed_by_mode(mode: str) -> None:
    evidence = {"mode": mode, "current_quote": "Roxy"}
    if mode != "direct":
        evidence.update(
            support_handle="A1" if mode == "endorse_assistant" else "U1",
            support_quote="Is Roxy a Husky?",
        )
    prior = [_prior("assistant", "Is Roxy a Husky?")]
    with pytest.raises(RuntimeValidationError):
        _prepare(
            [
                {
                    "kind": "related_add",
                    "fact_type": "pet.breed",
                    "value": "Husky",
                    "entity_ref": "new:roxy",
                    "evidence": evidence,
                }
            ],
            current="Roxy",
            prior=prior,
        )


def test_user_antecedent_resolution_keeps_distinct_current_authority() -> None:
    # The identity add supplies the new entity and the breed shares its local ref.
    prior = [_prior("user", "One of my dogs is a Husky")]
    decisions = [
        {
            "kind": "related_add",
            "fact_type": "pet.name",
            "value": "Roxy",
            "entity_ref": "new:roxy",
            "evidence": {"mode": "direct", "current_quote": "Roxy"},
        },
        {
            "kind": "related_add",
            "fact_type": "pet.breed",
            "value": "Husky",
            "entity_ref": "new:roxy",
            "evidence": {
                "mode": "resolve_user",
                "current_quote": "Roxy",
                "support_handle": "U1",
                "support_quote": "One of my dogs is a Husky",
            },
        },
    ]
    result = _prepare(decisions, current="Roxy", prior=prior)
    assert len(result.new_entities) == 1
    assert [source.authority_role for source in result.operations[1].sources] == [
        "user_resolution",
        "user_antecedent",
    ]
    assert result.operations[1].current_anchor.message_id == USER
    reordered = prepare_natural_memory_review(
        decision=parse_natural_review_decision({"decisions": decisions}),
        subject_id=SUBJECT,
        current_user_message=_current("Roxy"),
        available_messages=[_current("Roxy"), *prior],
        facts=[],
        entities=[{"id": SUBJECT, "subject_id": SUBJECT, "kind": "subject"}],
        candidate_reply="Okay",
    )
    assert reordered.operations[1].current_anchor == result.operations[1].current_anchor


def test_prior_support_handles_follow_chronology_when_input_is_permuted() -> None:
    older = {**_prior("user", "One of my dogs is a Husky"), "sequence": 1}
    newer = {**_prior("user", "Which one?"), "id": "different", "sequence": 2}
    first = build_natural_binding_map(
        current_user_message=_current("Roxy"),
        source_messages=[older, newer, _current("Roxy")],
        facts=[],
        entities=[],
    )
    reversed_input = build_natural_binding_map(
        current_user_message=_current("Roxy"),
        source_messages=[_current("Roxy"), newer, older],
        facts=[],
        entities=[],
    )
    assert first.messages == reversed_input.messages
    assert first.messages["U1"]["id"] == older["id"]


def test_binding_snapshot_is_detached_from_caller_rows() -> None:
    earlier = _prior("user", "One of my dogs is a Husky")
    current = _current("Roxy")
    binding = build_natural_binding_map(
        current_user_message=current,
        source_messages=[earlier, current],
        facts=[],
        entities=[],
    )
    earlier["content"] = "changed after snapshot"
    current["content"] = "changed after snapshot"
    assert binding.messages["U1"]["content"] == "One of my dogs is a Husky"
    assert binding.current["content"] == "Roxy"
    with pytest.raises(TypeError):
        binding.messages["U1"]["content"] = "tampered"


def test_new_related_identity_can_follow_its_dependent_fact() -> None:
    prior = [_prior("user", "One of my dogs is a Husky")]
    decisions = [
        {
            "kind": "related_add",
            "fact_type": "pet.breed",
            "value": "Husky",
            "entity_ref": "new:roxy",
            "evidence": {
                "mode": "resolve_user",
                "current_quote": "Roxy",
                "support_handle": "U1",
                "support_quote": "One of my dogs is a Husky",
            },
        },
        {
            "kind": "related_add",
            "fact_type": "pet.name",
            "value": "Roxy",
            "entity_ref": "new:roxy",
            "evidence": {"mode": "direct", "current_quote": "Roxy"},
        },
    ]
    result = _prepare(decisions, current="Roxy", prior=prior)
    assert len(result.new_entities) == 1
    assert {item.entity_id for item in result.operations} == {result.new_entities[0].id}


@pytest.mark.parametrize(
    "antecedent",
    [
        "One of my dogs might be a Husky",
        "Don't save that one dog is a Husky",
        "I withdraw that one dog is a Husky",
    ],
)
def test_resolution_inherits_restrictions(antecedent: str) -> None:
    with pytest.raises(RuntimeValidationError):
        _prepare(
            [
                {
                    "kind": "related_add",
                    "fact_type": "pet.breed",
                    "value": "Husky",
                    "entity_ref": "new:roxy",
                    "evidence": {
                        "mode": "resolve_user",
                        "current_quote": "Roxy",
                        "support_handle": "U1",
                        "support_quote": antecedent,
                    },
                }
            ],
            current="Roxy",
            prior=[_prior("user", antecedent)],
        )


def test_short_assent_to_one_assistant_proposition_can_authorize_fact() -> None:
    # Existing identity is offered as E1, derived from a current pet.name fact.
    pet_id = "00000000-0000-0000-0000-000000000007"
    identity = {
        **_fact("Roxy"),
        "fact_type": "pet.name",
        "qualifier": None,
        "entity_id": pet_id,
        "normalized_key": f"pet.name|{pet_id}",
    }
    current = _current("Yes")
    result = prepare_natural_memory_review(
        decision=parse_natural_review_decision(
            {
                "decisions": [
                    {
                        "kind": "related_add",
                        "fact_type": "pet.breed",
                        "value": "Husky",
                        "entity_ref": "E1",
                        "evidence": {
                            "mode": "endorse_assistant",
                            "current_quote": "Yes",
                            "support_handle": "A1",
                            "support_quote": "Is Roxy a Husky?",
                        },
                    }
                ]
            }
        ),
        subject_id=SUBJECT,
        current_user_message=current,
        available_messages=[_prior("assistant", "Is Roxy a Husky?"), current],
        facts=[identity],
        entities=[
            {"id": SUBJECT, "subject_id": SUBJECT, "kind": "subject"},
            {"id": pet_id, "subject_id": SUBJECT, "kind": "pet", "label": "Roxy"},
        ],
        candidate_reply="Okay",
    )
    assert result.operations[0].entity_id == pet_id
    assert [s.authority_role for s in result.operations[0].sources] == [
        "user_endorsement",
        "assistant_referent",
    ]


def test_operation_specific_removal_and_factual_end_are_distinct() -> None:
    removal = {
        "kind": "forget",
        "target": "F1",
        "evidence": {
            "mode": "endorse_assistant",
            "current_quote": "Yes, please",
            "support_handle": "A1",
            "support_quote": "Shall I remove saved morning coffee?",
        },
    }
    result = _prepare(
        [removal],
        current="Yes, please",
        prior=[_prior("assistant", "Shall I remove saved morning coffee?")],
        facts=[_fact()],
    )
    assert result.operations[0].next_status == "forgotten"
    with pytest.raises(RuntimeValidationError, match="Forget requires"):
        _prepare(
            [
                {
                    **removal,
                    "evidence": {
                        **removal["evidence"],
                        "support_quote": "Is morning coffee no longer your preference?",
                    },
                }
            ],
            current="Yes, please",
            prior=[_prior("assistant", "Is morning coffee no longer your preference?")],
            facts=[_fact()],
        )
    ended = _prepare(
        [
            {
                "kind": "end",
                "target": "F1",
                "reason": "ended",
                "evidence": {
                    "mode": "endorse_assistant",
                    "current_quote": "Yes",
                    "support_handle": "A1",
                    "support_quote": "Is morning coffee no longer your preference?",
                },
            }
        ],
        current="Yes",
        prior=[_prior("assistant", "Is morning coffee no longer your preference?")],
        facts=[_fact()],
    )
    assert ended.operations[0].next_status == "inactive"


def test_read_only_conflict_needs_no_fabricated_write() -> None:
    with pytest.raises(RuntimeValidationError) as error:
        _prepare(
            [
                {
                    "kind": "conflict",
                    "current_quote": "What do I prefer?",
                    "candidate_reply_quote": "tea",
                    "references": ["F1"],
                }
            ],
            current="What do I prefer?",
            facts=[_fact()],
            candidate="tea",
        )
    assert error.value.detail_code == "natural_memory_reply_conflict"
    with pytest.raises(RuntimeValidationError, match="agrees"):
        _prepare(
            [
                {
                    "kind": "conflict",
                    "current_quote": "What do I prefer?",
                    "candidate_reply_quote": "morning coffee",
                    "references": ["F1"],
                }
            ],
            current="What do I prefer?",
            facts=[_fact()],
            candidate="morning coffee",
        )


def test_target_handles_are_local_and_version_is_server_owned() -> None:
    current = "Forget morning coffee memory."
    decision = {
        "kind": "forget",
        "target": "F1",
        "evidence": {"mode": "direct", "current_quote": current},
    }
    result = _prepare([decision], current=current, facts=[_fact()])
    assert result.operations[0].existing_fact["version"] == 1
    with pytest.raises(RuntimeValidationError):
        _prepare([{**decision, "target": "F2"}], current=current, facts=[_fact()])
    with pytest.raises(RuntimeValidationError):
        parse_natural_review_decision(
            {"decisions": [{**decision, "expected_version": 99}]}
        )
