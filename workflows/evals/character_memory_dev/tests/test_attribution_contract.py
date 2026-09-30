"""Source packets and scripted decisions, never simulated model-quality results."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ade_api.features.agent_runtime.context import (
    ContextBudget,
    ConversationHistoryMetadata,
    MEMORY_CONTROL_INSTRUCTIONS,
)
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.history_admission import admit_history
from ade_api.features.agent_runtime.natural_context import build_natural_context
from ade_api.features.agent_runtime.natural_memory_binding import (
    build_natural_binding_map,
)
from ade_api.features.agent_runtime.natural_memory_policy import (
    prepare_natural_memory_review,
)
from ade_api.features.agent_runtime.natural_memory_review import (
    parse_natural_review_decision,
)
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    natural_review_request,
)


FIXTURE = (
    Path(__file__).parents[1] / "fixtures/history_recall/attribution_contrasts.json"
)
CASES = json.loads(FIXTURE.read_text())["cases"]
SUBJECT = "00000000-0000-0000-0000-000000000001"
ENTITIES = [{"id": SUBJECT, "kind": "subject", "subject_id": SUBJECT}]


def _sources(case):
    current = {
        "id": "current-user",
        "role": "user",
        "content": case["current_user"],
        "sequence": 1,
    }
    exchange = {
        "run_id": "earlier-run",
        "conversation_id": "earlier-chat",
        "definition_version_id": "earlier-definition",
        "archived": True,
        "messages": [
            {
                "id": f"earlier-{role}",
                "role": role,
                "content": case[f"history_{role}"],
                "content_sha256": hashlib.sha256(
                    case[f"history_{role}"].encode()
                ).hexdigest(),
                "created_at": "2026-01-01T00:00:00+00:00",
                "sequence": sequence,
            }
            for sequence, role in enumerate(("user", "assistant"), 1)
        ],
        "annotations": {
            "links": [],
            "facts": [],
            "revisions": [],
            "predecessor_edges": [],
        },
    }
    return current, exchange


@pytest.mark.parametrize("variant", ["A", "A0", "B"])
@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_shared_generation_and_h_review_preserve_attributed_sources(case, variant):
    current, exchange = _sources(case)
    base = build_natural_context(
        variant=variant,
        system_prompt="Respond naturally.",
        persona="A conversational companion.",
        current_user=current,
        eligible_recent_messages=[],
        lifecycle_facts=[],
        retrieved_facts=[],
        entities=ENTITIES,
        summary_content="",
        history_metadata=ConversationHistoryMetadata(0, 0),
        budget=ContextBudget(16384, 4096, 256),
        reviewer_suffix_limit=640,
    )
    admission = admit_history(
        base=base.context,
        ranked_exchanges=[exchange],
        current_user=current,
        source_messages=[current],
        facts=[],
        entities=ENTITIES,
        generation_model_key="source::model",
        generation_adapter="deepseek_openai",
        generation_tools={},
        generation_input_limit=11213,
        generation_max_output_tokens=4096,
        reviewer_model_key="source::model",
        reviewer_adapter="deepseek_openai",
        reviewer_input_limit=11469,
        reviewer_max_output_tokens=4096,
    )
    assert admission.exchanges == (exchange,)
    generation = admission.context.messages[0]["content"]
    assert MEMORY_CONTROL_INSTRUCTIONS in generation
    for requirement in (
        "preserve its speaker, uncertainty and temporal scope",
        "separately states or endorses them",
        "Present new suggestions and tentative inferences as such",
    ):
        assert requirement in " ".join(generation.split())
    for reply_key in ("faithful_reply", "unfaithful_reply"):
        if reply_key not in case:
            continue
        review = natural_review_request(
            model_key="source::model",
            provider_adapter="deepseek_openai",
            current_user_message=current,
            source_messages=[current],
            facts=[],
            entities=ENTITIES,
            candidate_reply=case[reply_key],
            history_exchanges=[exchange],
            history_capable=True,
        )
        packet = json.loads(review["messages"][1]["content"])
        generated_history = json.loads(
            generation.split("Historical evidence (read-only):\n", 1)[1]
        )
        assert packet["history"] == generated_history
        messages = packet["history"][0]["messages"]
        assert [(m["handle"], m["role"], m["content"]) for m in messages] == [
            ("H1", "user", case["history_user"]),
            ("H2", "assistant", case["history_assistant"]),
        ]
        assert packet["current_user"]["content"] == case["current_user"]
        assert packet["candidate_visible_reply"] == case[reply_key]
        system = " ".join(review["messages"][0]["content"].split())
        for requirement in (
            "source establishes a speaker mismatch",
            "including later explicit endorsement",
            "Endorsement supports only its own time and scope",
            "shared wording alone does not establish one",
            "Missing evidence alone is not a contradiction",
            "Questions, new suggestions and explicitly tentative inferences",
        ):
            assert requirement in system


def _prepare(case, reply, decisions):
    current, exchange = _sources(case)
    binding = build_natural_binding_map(
        current_user_message=current,
        source_messages=[current],
        facts=[],
        entities=ENTITIES,
        history_exchanges=[exchange],
    )
    return prepare_natural_memory_review(
        decision=parse_natural_review_decision({"decisions": decisions}),
        subject_id=SUBJECT,
        current_user_message=current,
        available_messages=[current],
        facts=[],
        entities=ENTITIES,
        candidate_reply=reply,
        binding_map=binding,
    )


def test_scripted_speaker_conflict_rejects_and_requires_real_source_quote():
    case = CASES[0]
    conflict = case["scripted_conflict"]
    with pytest.raises(RuntimeValidationError) as rejected:
        _prepare(case, case["unfaithful_reply"], [conflict])
    assert rejected.value.detail_code == "natural_memory_reply_conflict"
    fabricated = {
        **conflict,
        "history": {"handle": "H2", "quote": "The user said this."},
    }
    with pytest.raises(RuntimeValidationError) as ungrounded:
        _prepare(case, case["unfaithful_reply"], [fabricated])
    assert ungrounded.value.detail_code == "natural_review_binding"


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_scripted_no_change_is_not_replaced_by_an_ade_semantic_veto(case):
    for reply_key in ("faithful_reply", "unfaithful_reply"):
        if reply_key in case:
            prepared = _prepare(case, case[reply_key], [])
            assert prepared.operations == ()
            assert prepared.new_entities == ()
            assert prepared.deferred_claims == ()


def test_explicit_current_endorsement_can_write_without_promoting_h_to_authority():
    case = CASES[-1]
    prepared = _prepare(case, case["faithful_reply"], [case["scripted_write"]])
    assert len(prepared.operations) == 1
    operation = prepared.operations[0]
    assert operation.value == case["scripted_write"]["value"]
    assert operation.entity_id == SUBJECT
    assert operation.current_anchor.message_id == "current-user"
    assert operation.current_anchor.authority_role == "user_assertion"
    assert len(operation.sources) == 1
    assert prepared.new_entities == ()
