"""Narrow runtime-owned request construction for frozen synthetic story studies."""

from __future__ import annotations

import hashlib
import json

from ade_api.features.agent_runtime.context import (
    ConversationHistoryMetadata,
    estimate_tokens,
)
from ade_api.features.agent_runtime.executor import initial_conversation_request
from ade_api.features.agent_runtime.history_admission import (
    MAX_ADMITTED_WINDOWS,
    admit_history,
)
from ade_api.features.agent_runtime.history_capacity import (
    CONVERSATION_BUDGET,
    REVIEWER_BUDGET,
)
from ade_api.features.agent_runtime.natural_context import build_natural_context
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    natural_review_request,
    preflight_reviewer_bundle,
    reviewer_suffix_limit,
)


MODEL = "deepseek::deepseek-flash"
ADAPTER = "deepseek_openai"


def wire(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(wire(value).encode()).hexdigest()


def build_history_packet(
    *, current: dict, context: dict, sources: dict, selected: list[str]
):
    """Build requests only; caller owns corpus topology, labels and artifacts."""
    assert len(selected) == len(set(selected)) <= MAX_ADMITTED_WINDOWS
    assert set(selected) <= sources.keys()
    if any(context[key] for key in ("saved_facts", "local_suffix", "related_entities")):
        raise ValueError(
            "Synthetic story packet builder requires empty saved/local context"
        )
    assert CONVERSATION_BUDGET.input_limit == 11213
    assert REVIEWER_BUDGET.input_limit == 11469
    assert (
        CONVERSATION_BUDGET.max_output_tokens
        == REVIEWER_BUDGET.max_output_tokens
        == 4096
    )
    suffix_limit = reviewer_suffix_limit(
        model_key=MODEL,
        provider_adapter=ADAPTER,
        current_user_message=current,
        facts=[],
        entities=[],
        input_token_limit=REVIEWER_BUDGET.input_limit,
        candidate_reply_reserve=CONVERSATION_BUDGET.max_output_tokens,
        history_capable=True,
    )
    base = build_natural_context(
        variant="B",
        system_prompt=context["generation_system_text"],
        persona=context["persona"],
        current_user=current,
        eligible_recent_messages=[],
        lifecycle_facts=[],
        retrieved_facts=[],
        entities=[],
        summary_content="",
        history_metadata=ConversationHistoryMetadata(
            completed_user_turns=0, summary_through_sequence=0
        ),
        budget=CONVERSATION_BUDGET,
        reviewer_suffix_limit=suffix_limit,
        shared_suffix_token_limit=640,
    )
    assert list(base.source_messages) == [current]
    admission = admit_history(
        base=base.context,
        ranked_exchanges=[sources[source_id] for source_id in selected],
        current_user=current,
        source_messages=[current],
        facts=[],
        entities=[],
        generation_model_key=MODEL,
        generation_adapter=ADAPTER,
        generation_tools={},
        generation_input_limit=CONVERSATION_BUDGET.input_limit,
        generation_max_output_tokens=CONVERSATION_BUDGET.max_output_tokens,
        reviewer_model_key=MODEL,
        reviewer_adapter=ADAPTER,
        reviewer_input_limit=REVIEWER_BUDGET.input_limit,
        reviewer_max_output_tokens=REVIEWER_BUDGET.max_output_tokens,
    )
    review_args = dict(
        model_key=MODEL,
        provider_adapter=ADAPTER,
        current_user_message=current,
        source_messages=[current],
        facts=[],
        entities=[],
        history_exchanges=list(admission.exchanges),
        history_capable=True,
        max_output_tokens=REVIEWER_BUDGET.max_output_tokens,
    )
    projected = preflight_reviewer_bundle(
        **review_args,
        candidate_reply_reserve=CONVERSATION_BUDGET.max_output_tokens,
        input_token_limit=REVIEWER_BUDGET.input_limit,
    )
    generation = initial_conversation_request(
        model_key=MODEL,
        messages=admission.context.messages,
        max_output_tokens=CONVERSATION_BUDGET.max_output_tokens,
        tools={},
        provider_adapter=ADAPTER,
    )
    review = natural_review_request(
        **review_args,
        candidate_reply="Synthetic packet audit only; no model response was generated.",
    )
    reviewer_packet = json.loads(review["messages"][1]["content"])
    history = reviewer_packet["history"]
    system = generation["messages"][0]["content"]
    assert reviewer_packet["eligible_support"] == []
    if history:
        assert (
            json.loads(system.split("Historical evidence (read-only):\n", 1)[1])
            == history
        )
    else:
        assert "Historical evidence (read-only):\n" not in system
    assert (
        estimate_tokens(wire(generation))
        == admission.context.estimated_input_tokens
        <= 11213
    )
    assert projected <= 11469
    run_to_id = {
        exchange["run_id"]: source_id for source_id, exchange in sources.items()
    }
    admitted = [run_to_id[exchange["run_id"]] for exchange in admission.exchanges]
    return {
        "selected": selected,
        "admitted": admitted,
        "omitted_capacity": [
            run_to_id[run_id] for run_id in admission.omitted_capacity
        ],
        "generation_input_estimate": admission.context.estimated_input_tokens,
        "reviewer_input_with_full_reply_reserve": projected,
        "history_equal": True,
        "generation_sha256": digest(generation),
        "reviewer_sha256": digest(review),
    }, {"generation": generation, "reviewer": review}
