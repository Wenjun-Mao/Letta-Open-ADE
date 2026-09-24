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


def test_deferral_binds_current_quote_and_unrelated_write_survives() -> None:
    result = _prepare(
        [
            {"kind": "defer", "current_quote": "Maybe tea", "reason": "uncertain"},
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
        current="Maybe tea. I now live in Toronto.",
    )
    assert [item.value for item in result.operations] == ["Toronto"]
    assert result.deferred_claims == ({"quote": "Maybe tea", "reason": "uncertain"},)
    with pytest.raises(RuntimeValidationError):
        _prepare(
            [{"kind": "defer", "current_quote": "unquoted", "reason": "uncertain"}],
            current="Maybe tea.",
        )


def test_natural_meaning_is_reviewer_owned_after_exact_quote_binding() -> None:
    result = _prepare(
        [_subject_add("prefers tea in the morning", "现在早上更喜欢茶了")],
        current="现在早上更喜欢茶了",
    )
    assert result.operations[0].value == "prefers tea in the morning"
    assert result.operations[0].current_anchor.quote == "现在早上更喜欢茶了"


def test_removed_no_save_reason_is_not_in_the_review_schema() -> None:
    with pytest.raises(RuntimeValidationError) as error:
        parse_natural_review_decision(
            {
                "decisions": [
                    {"kind": "defer", "current_quote": "anything", "reason": "no_save"}
                ]
            }
        )
    assert error.value.detail_code == "natural_review_schema"


def test_assistant_support_requires_actual_assistant_role() -> None:
    decision = {
        "kind": "related_add",
        "fact_type": "pet.breed",
        "value": "Husky",
        "entity_ref": "new:roxy",
        "evidence": {
            "mode": "endorse_assistant",
            "current_quote": "Roxy",
            "support_handle": "U1",
            "support_quote": "Is Roxy a Husky?",
        },
    }
    with pytest.raises(RuntimeValidationError) as error:
        _prepare(
            [decision],
            current="Roxy",
            prior=[_prior("user", "Is Roxy a Husky?")],
        )
    assert error.value.detail_code == "natural_review_schema"


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


def test_factual_end_and_forget_have_distinct_structural_effects() -> None:
    forgot = _prepare(
        [
            {
                "kind": "forget",
                "target": "F1",
                "evidence": {
                    "mode": "direct",
                    "current_quote": "Remove the morning coffee fact",
                },
            }
        ],
        current="Remove the morning coffee fact",
        facts=[_fact()],
    )
    assert forgot.operations[0].next_status == "forgotten"
    ended = _prepare(
        [
            {
                "kind": "end",
                "target": "F1",
                "reason": "ended",
                "evidence": {
                    "mode": "direct",
                    "current_quote": "I no longer prefer coffee in the morning",
                },
            }
        ],
        current="I no longer prefer coffee in the morning",
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
    # The exact candidate span and held F reference are structural checks.
    with pytest.raises(RuntimeValidationError, match="exact candidate span"):
        _prepare(
            [
                {
                    "kind": "conflict",
                    "current_quote": "What do I prefer?",
                    "candidate_reply_quote": "missing",
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


def test_factual_continuity_fixture_separates_habit_from_preference() -> None:
    # Injected decisions exercise complete deltas; they do not prove model judgment.
    habit = _prepare(
        [],
        current="最近喝咖啡总睡不着，早上也改喝茶了",
        facts=[_fact("prefers coffee in the morning")],
    )
    assert habit.operations == ()
    preference = _prepare(
        [
            {
                "kind": "revise",
                "target": "F1",
                "reason": "supersede",
                "value": "prefers tea in the morning",
                "evidence": {"mode": "direct", "current_quote": "现在早上更喜欢茶了"},
            }
        ],
        current="现在早上更喜欢茶了",
        facts=[_fact("prefers coffee in the morning")],
    )
    assert len(preference.operations) == 1
    assert (
        preference.operations[0].existing_fact["value"]
        == "prefers coffee in the morning"
    )
    assert preference.operations[0].value == "prefers tea in the morning"
    assert preference.operations[0].revision_reason == "supersede"


def test_scoped_correction_changes_only_active_morning_chain() -> None:
    current = "不对，我说的是晚上更喜欢茶，早上仍喜欢咖啡"
    decisions = [
        {
            "kind": "revise",
            "target": "F1",
            "reason": "correct",
            "value": "prefers coffee in the morning",
            "evidence": {"mode": "direct", "current_quote": "早上仍喜欢咖啡"},
        },
        _subject_add("prefers tea in the evening", "晚上更喜欢茶"),
    ]
    result = _prepare(
        decisions, current=current, facts=[_fact("prefers tea in the morning")]
    )
    assert [
        (item.fact_type, item.value, item.next_status) for item in result.operations
    ] == [
        ("person.preference", "prefers coffee in the morning", "active"),
        ("person.preference", "prefers tea in the evening", "active"),
    ]
    with pytest.raises(RuntimeValidationError, match="active target"):
        _prepare(
            decisions,
            current=current,
            facts=[_fact("prefers tea in the morning", status="inactive")],
        )
