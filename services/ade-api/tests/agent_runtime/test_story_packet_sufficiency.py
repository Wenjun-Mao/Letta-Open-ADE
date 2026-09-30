"""Admission mechanics only; do not run selectors on the unannotated audit cases."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from ade_api.features.agent_runtime.context import (
    ConversationHistoryMetadata,
    estimate_tokens,
)
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.history_admission import admit_history
from ade_api.features.agent_runtime.history_capacity import (
    bind_history_probe_capacity,
    checked_history_probe_capacity,
)
from ade_api.features.agent_runtime.natural_context import (
    HISTORY_PROBE_POLICY,
    build_natural_context,
)
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    natural_review_request,
    preflight_reviewer_bundle,
    reviewer_suffix_limit,
)
from workflows.evals.character_memory_dev.story_continuity.packet_sufficiency.packet import (
    DIRECTORY,
    load_inputs,
)


MODEL = "deepseek::deepseek-flash"
ADAPTER = "deepseek_openai"
CURRENT = {"id": "current", "role": "user", "content": "What was said?", "sequence": 5}


def _capacity():
    definition = {
        "memory_policy_version": HISTORY_PROBE_POLICY,
        "deployment_snapshot": [
            {
                "role": role,
                "route_alias": MODEL if role != "retriever" else "qwen::embedding",
                "fingerprint": f"synthetic-{role}",
                "fingerprint_payload": {
                    "context_settings": {
                        "total_tokens": 16384,
                        "max_output_tokens": 4096,
                        "max_model_requests": 2,
                        "reviewer_repair_count": 0,
                    }
                },
            }
            for role in ("conversation", "reviewer", "retriever")
        ],
    }
    capacity = checked_history_probe_capacity(
        bind_history_probe_capacity(definition), purpose="evaluation"
    )
    frozen = json.loads((DIRECTORY / "freeze.json").read_bytes())["capacity"]
    assert capacity.conversation.input_limit == frozen["generation_input_tokens"]
    assert capacity.reviewer.input_limit == frozen["reviewer_input_tokens"]
    assert (
        capacity.conversation.max_output_tokens
        == frozen["generation_output_reserve_tokens"]
    )
    assert capacity.reviewer_request_max_tokens == frozen["reviewer_output_tokens"]
    assert capacity.reviewer_shared_suffix_tokens == frozen["shared_suffix_tokens"]
    return capacity


def _exchange(name="short", assistant="Earlier statement."):
    return {
        "run_id": name,
        "conversation_id": f"chat-{name}",
        "definition_version_id": "synthetic-prior-version",
        "archived": True,
        "messages": [
            {
                "id": f"{name}-{role}",
                "role": role,
                "content": text,
                "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "created_at": "2026-09-01T12:00:00+00:00",
                "sequence": index,
            }
            for index, (role, text) in enumerate(
                [("user", "Earlier question."), ("assistant", assistant)], 1
            )
        ],
        "annotations": {
            "links": [],
            "facts": [],
            "revisions": [],
            "predecessor_edges": [],
        },
    }


def _packets(exchanges, local=None):
    capacity = _capacity()
    context, _, _ = load_inputs()
    local = local or []
    suffix_limit = reviewer_suffix_limit(
        model_key=MODEL,
        provider_adapter=ADAPTER,
        current_user_message=CURRENT,
        facts=[],
        entities=[],
        input_token_limit=capacity.reviewer.input_limit,
        candidate_reply_reserve=capacity.conversation.max_output_tokens,
        history_capable=True,
    )
    base = build_natural_context(
        variant="B",
        system_prompt=context["generation_system_text"],
        persona=context["persona"],
        current_user=CURRENT,
        eligible_recent_messages=local,
        lifecycle_facts=[],
        retrieved_facts=[],
        entities=[],
        summary_content="",
        history_metadata=ConversationHistoryMetadata(
            completed_user_turns=len(local) // 2, summary_through_sequence=0
        ),
        budget=capacity.conversation,
        reviewer_suffix_limit=suffix_limit,
        shared_suffix_token_limit=capacity.reviewer_shared_suffix_tokens,
    )
    shared = list(base.source_messages)
    assert (
        sum(estimate_tokens(m["content"]) for m in shared if m["id"] != "current")
        <= 640
    )
    admission = admit_history(
        base=base.context,
        ranked_exchanges=exchanges,
        current_user=CURRENT,
        source_messages=shared,
        facts=[],
        entities=[],
        generation_model_key=MODEL,
        generation_adapter=ADAPTER,
        generation_tools={},
        generation_input_limit=capacity.conversation.input_limit,
        generation_max_output_tokens=capacity.conversation.max_output_tokens,
        reviewer_model_key=MODEL,
        reviewer_adapter=ADAPTER,
        reviewer_input_limit=capacity.reviewer.input_limit,
        reviewer_max_output_tokens=capacity.reviewer_request_max_tokens,
    )
    chosen = list(admission.exchanges)
    review_args = dict(
        model_key=MODEL,
        provider_adapter=ADAPTER,
        current_user_message=CURRENT,
        source_messages=shared,
        facts=[],
        entities=[],
        history_exchanges=chosen,
        history_capable=True,
        max_output_tokens=capacity.reviewer_request_max_tokens,
    )
    projected = preflight_reviewer_bundle(
        **review_args,
        candidate_reply_reserve=capacity.conversation.max_output_tokens,
        input_token_limit=capacity.reviewer.input_limit,
    )
    assert projected <= 11469
    assert admission.context.estimated_input_tokens <= 11213
    request = natural_review_request(**review_args, candidate_reply="Mechanics only.")
    packet = json.loads(request["messages"][1]["content"])
    generation_system = admission.context.messages[0]["content"]
    if chosen:
        generation_history = json.loads(
            generation_system.split("Historical evidence (read-only):\n", 1)[1]
        )
        assert generation_history == packet["history"]
    else:
        assert packet["history"] == []
        assert "Historical evidence (read-only):\n" not in generation_system
    return admission, packet


def test_empty_history_fits_real_source_owned_capacity():
    admission, packet = _packets([])
    assert admission.exchanges == admission.omitted_capacity == ()
    assert packet["eligible_support"] == []


@pytest.mark.parametrize("pressure", ["message", "annotation"])
def test_capacity_omits_complete_oversize_window_without_losing_later_fit(pressure):
    large = _exchange("oversize", "x" * 60_000 if pressure == "message" else "Short.")
    if pressure == "annotation":
        large["annotations"]["note"] = "x" * 60_000
    short = _exchange()
    before = copy.deepcopy([large, short])
    admission, packet = _packets([large, short])
    assert admission.omitted_capacity == ("oversize",)
    assert list(admission.exchanges) == [short]
    assert [row["run_id"] for row in packet["history"]] == ["short"]
    assert [large, short] == before


def test_annotations_and_local_text_overlap_keep_distinct_authority():
    history = _exchange()
    source = history["messages"][0]
    history["annotations"]["links"] = [
        {
            "message_id": source["id"],
            "span": [0, len(source["content"])],
            "quote": source["content"],
            "authority_role": "user_assertion",
            "fact_id": "synthetic-fact",
        }
    ]
    local = [
        {
            "id": f"local-{m['role']}",
            "run_id": "local",
            "role": m["role"],
            "content": m["content"],
            "sequence": m["sequence"],
        }
        for m in history["messages"]
    ]
    before = copy.deepcopy(history)
    _, packet = _packets([history], local)
    assert history == before
    assert packet["eligible_support"] == [
        {"handle": "U1", "role": "user"},
        {"handle": "A1", "role": "assistant"},
    ]
    window = packet["history"][0]
    assert [m["handle"] for m in window["messages"]] == ["H1", "H2"]
    assert window["annotations"]["links"][0]["message_handle"] == "H1"
    assert "message_id" not in window["annotations"]["links"][0]
    assert [m["content"] for m in packet["context"]] == [
        m["content"] for m in window["messages"]
    ]


def test_corrupt_source_hash_stops_admission():
    exchange = _exchange()
    exchange["messages"][1]["content"] = "Changed without rebinding the digest."
    with pytest.raises(RuntimeValidationError) as error:
        _packets([exchange])
    assert error.value.detail_code == "natural_history_integrity"
