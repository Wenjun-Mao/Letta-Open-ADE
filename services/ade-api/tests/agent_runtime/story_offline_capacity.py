"""ADR 0058 counterfactual requests, retaining complete sources even on overflow."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ade_api.features.agent_runtime.context import (
    ConversationHistoryMetadata,
    estimate_tokens,
)
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.executor import initial_conversation_request
from ade_api.features.agent_runtime.history_admission import _context_with_history
from ade_api.features.agent_runtime.history_capacity import (
    CONVERSATION_BUDGET,
    REVIEWER_BUDGET,
)
from ade_api.features.agent_runtime.natural_context import build_natural_context
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    natural_review_request,
    preflight_reviewer_bundle,
    reviewer_suffix_limit,
    serialized_review_tokens,
)
from workflows.evals.character_memory_dev.story_continuity.evidence_selection.offline_inputs import (
    DIRECTORY,
    ROOT,
    ROWS,
    load_offline_inputs,
    validate_row,
)

if __package__:
    from .story_correction_comparison import current_message, exchanges, select
    from .story_packet_builder import ADAPTER, MODEL, build_history_packet, digest, wire
else:
    from story_correction_comparison import current_message, exchanges, select
    from story_packet_builder import ADAPTER, MODEL, build_history_packet, digest, wire


SYNTHETIC_REPLY = "Synthetic packet audit only; no model response was generated."
FULL_REPLY = "x" * (4 * CONVERSATION_BUDGET.max_output_tokens)


def capacity(estimate: int, limit: int) -> dict:
    return {
        "input_estimate": estimate,
        "input_limit": limit,
        "headroom": limit - estimate,
        "overflow": max(0, estimate - limit),
        "fits": estimate <= limit,
    }


def source_order(case: dict, sources: dict, included: list[str], history: list) -> list:
    """Verify synthetic reader bindings absent from H; never add them to requests."""
    expected = exchanges(case, {"history_annotations": sources["E01"]["annotations"]})
    receipt = []
    for source_id, supplied in zip(included, history, strict=True):
        source = sources[source_id]
        original_binding = expected[source_id]
        for field in ("run_id", "conversation_id", "definition_version_id", "archived"):
            if (
                source[field] != original_binding[field]
                or supplied[field] != source[field]
            ):
                raise ValueError(f"Frozen historical scope binding differs: {field}")
        for original, bound, message in zip(
            original_binding["messages"],
            source["messages"],
            supplied["messages"],
            strict=True,
        ):
            for field in ("id", "role", "sequence", "created_at"):
                if bound[field] != original[field]:
                    raise ValueError(
                        f"Frozen historical message binding differs: {field}"
                    )
            if any(
                message[field] != bound[field]
                for field in ("role", "content", "content_sha256", "created_at")
            ):
                raise ValueError("Historical serialization changed source content")
            receipt.append(
                {
                    "source_id": source_id,
                    "message_id": bound["id"],
                    "run_id": source["run_id"],
                    "conversation_id": source["conversation_id"],
                    "definition_version_id": source["definition_version_id"],
                    "archived": source["archived"],
                    "sequence": bound["sequence"],
                    "role": bound["role"],
                    "handle": message["handle"],
                    "created_at": message["created_at"],
                    "content_sha256": message["content_sha256"],
                }
            )
    return receipt


def build_complete_packet(
    *, case: dict, context: dict, sources: dict, included: list[str]
):
    """Test-only orchestration: render once, measure twice, never admit or prune."""
    if len(included) != len(set(included)) or not set(included) <= sources.keys():
        raise ValueError("Complete packets require unique known source IDs")
    if len(included) > 4 and not (case["id"] == "D04" and included == list(ROWS[2][2])):
        raise ValueError(
            "Only D04's chronological eight-source diagnostic exceeds four"
        )
    if case["id"] not in {"D02", "D04"} or list(sources) != list(ROWS[2][2]):
        raise ValueError("Offline source scope/count differs")
    if any(context[key] for key in ("saved_facts", "local_suffix", "related_entities")):
        raise ValueError("Offline diagnostic requires empty saved/local context")
    if any(
        source["annotations"] != context["history_annotations"]
        for source in sources.values()
    ):
        raise ValueError("Historical annotations differ from the controlled context")
    current = current_message(case)
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
    selected = [sources[source_id] for source_id in included]
    rendered = _context_with_history(
        base.context,
        selected,
        current_user=current,
        source_messages=[current],
        facts=[],
        entities=[],
    )
    generation = initial_conversation_request(
        model_key=MODEL,
        messages=rendered.messages,
        max_output_tokens=CONVERSATION_BUDGET.max_output_tokens,
        tools={},
        provider_adapter=ADAPTER,
    )
    review_args = dict(
        model_key=MODEL,
        provider_adapter=ADAPTER,
        current_user_message=current,
        source_messages=[current],
        facts=[],
        entities=[],
        history_exchanges=selected,
        history_capable=True,
        max_output_tokens=REVIEWER_BUDGET.max_output_tokens,
    )
    review = natural_review_request(**review_args, candidate_reply=SYNTHETIC_REPLY)
    full_review = natural_review_request(**review_args, candidate_reply=FULL_REPLY)
    full_estimate = serialized_review_tokens(full_review)
    preflight_error = None
    try:
        projected = preflight_reviewer_bundle(
            **review_args,
            candidate_reply_reserve=CONVERSATION_BUDGET.max_output_tokens,
            input_token_limit=REVIEWER_BUDGET.input_limit,
        )
    except RuntimeValidationError as exc:
        if exc.detail_code != "natural_reviewer_capacity":
            raise
        if full_estimate <= REVIEWER_BUDGET.input_limit:
            raise AssertionError(
                "Reviewer preflight disagrees with full request"
            ) from exc
        preflight_error = exc.detail_code
    else:
        assert projected == full_estimate <= REVIEWER_BUDGET.input_limit
    packet = json.loads(review["messages"][1]["content"])
    history = packet["history"]
    assert history == json.loads(full_review["messages"][1]["content"])["history"]
    system = generation["messages"][0]["content"]
    if history:
        assert (
            json.loads(system.split("Historical evidence (read-only):\n", 1)[1])
            == history
        )
    else:
        assert "Historical evidence (read-only):\n" not in system
    generation_capacity = capacity(
        estimate_tokens(wire(generation)), CONVERSATION_BUDGET.input_limit
    )
    reviewer_capacity = capacity(full_estimate, REVIEWER_BUDGET.input_limit)
    requests = {
        "generation": generation,
        "reviewer": review,
        "reviewer_full_reserve": full_review,
    }
    receipt = {
        "included": list(included),
        "included_source_count": len(history),
        "included_message_count": sum(len(row["messages"]) for row in history),
        "source_order": source_order(case, sources, included, history),
        "history_equal": True,
        "history_sha256": digest(history),
        "generation": generation_capacity,
        "reviewer_full_reserve": reviewer_capacity,
        "reviewer_synthetic": capacity(
            serialized_review_tokens(review), REVIEWER_BUDGET.input_limit
        ),
        "reviewer_preflight_error": preflight_error,
        "counterfactual_capacity_status": "fits"
        if generation_capacity["fits"] and reviewer_capacity["fits"]
        else "overflow",
        "runtime_admission": "not_attempted",
        **{f"{name}_sha256": digest(request) for name, request in requests.items()},
    }
    return receipt, requests


def measure():
    context, cases, freeze = load_offline_inputs()
    by_id = {case["id"]: case for case in cases}
    assert (CONVERSATION_BUDGET.input_limit, REVIEWER_BUDGET.input_limit) == (
        11213,
        11469,
    )
    assert (
        CONVERSATION_BUDGET.max_output_tokens
        == REVIEWER_BUDGET.max_output_tokens
        == 4096
    )
    literal = select(by_id["D04"])[1]["baseline"]
    if literal != list(ROWS[1][2]):
        raise ValueError("Unchanged D04 literal ranker differs from frozen control")
    rows, artifacts = [], []
    for key, case_id, source_ids in ROWS:
        included = list(source_ids)
        validate_row(key, case_id, included)
        case = by_id[case_id]
        sources = exchanges(case, context)
        receipt, requests = build_complete_packet(
            case=case, context=context, sources=sources, included=included
        )
        parity = "outside_historical_four_window_contract"
        if len(included) <= 4:
            old_receipt, old_requests = build_history_packet(
                current=current_message(case),
                context=context,
                sources=sources,
                selected=included,
            )
            assert old_receipt["admitted"] == included
            assert wire(old_requests) == wire(
                {name: requests[name] for name in old_requests}
            )
            assert (
                old_receipt["generation_input_estimate"]
                == receipt["generation"]["input_estimate"]
            )
            assert (
                old_receipt["reviewer_input_with_full_reply_reserve"]
                == receipt["reviewer_full_reserve"]["input_estimate"]
            )
            parity = "byte_exact"
        rows.append({"key": key, **receipt, "historical_builder_parity": parity})
        artifacts.append({"key": key, **requests})
    execution = [Path(__file__), DIRECTORY / "offline_inputs.py"]
    summary = {
        "kind": "offline_counterfactual_capacity_not_runtime_admission_or_model_evaluation",
        **freeze,
        "context_sha256": digest(context),
        "execution_sources": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in execution
        },
        "capacity_contract": {
            "generation_input_limit": 11213,
            "reviewer_input_limit": 11469,
            "generation_output_reserve": 4096,
            "reviewer_output_reserve": 4096,
            "candidate_reply_reserve_tokens": 4096,
            "candidate_reply_placeholder_ascii_chars": len(FULL_REPLY),
            "shared_suffix_limit": 640,
            "model": MODEL,
            "adapter": ADAPTER,
            "provider_configuration_status": "serializer_only_not_provider_verified",
            "count_exception": "D04/whole-pool only; runtime and selector remain four",
        },
        "eligibility": "Frozen synthetic same-workspace/subject/character-root assumption; not database observation",
        "literal_four": literal,
        "rows": rows,
        "packets_sha256": hashlib.sha256(
            "".join(wire(packet) + "\n" for packet in artifacts).encode()
        ).hexdigest(),
        "unmeasured": [
            "provider_tokens",
            "latency",
            "generated_answers",
            "reviewer_behavior",
            "persistence",
            "production_retrieval",
        ],
    }
    return summary, artifacts


if __name__ == "__main__":
    summary, artifacts = measure()
    (DIRECTORY / "offline_capacity.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    (DIRECTORY / "offline_packets.jsonl").write_text(
        "".join(wire(packet) + "\n" for packet in artifacts)
    )
    for row in summary["rows"]:
        print(
            wire(
                {
                    key: row[key]
                    for key in (
                        "key",
                        "included_source_count",
                        "generation",
                        "reviewer_full_reserve",
                        "counterfactual_capacity_status",
                    )
                }
            )
        )
