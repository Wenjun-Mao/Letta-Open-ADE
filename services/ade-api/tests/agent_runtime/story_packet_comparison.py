"""Offline runtime-owned packet audit. No providers, database or semantic oracle in selection."""

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
from ade_api.features.agent_runtime.history_ranking import (
    TOP_K,
    document_text,
    literal_score,
    query_text,
    rank_windows,
)
from ade_api.features.agent_runtime.natural_context import build_natural_context
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    natural_review_request,
    preflight_reviewer_bundle,
    reviewer_suffix_limit,
)
from workflows.evals.character_memory_dev.story_continuity.packet_sufficiency.judgments import (
    JUDGMENTS_SHA256,
    assess_packet,
    load_judgments,
)
from workflows.evals.character_memory_dev.story_continuity.packet_sufficiency.packet import (
    DIRECTORY,
    FREEZE_SHA256,
    load_inputs,
)
from workflows.evals.character_memory_dev.story_continuity.retrieval_diversity.selector import (
    LIMIT,
    Window,
    select_diverse,
)


LABEL_COMMIT = "bed18094eaaeabe66c5d754cb098fcccf29ec952"
MODEL = "deepseek::deepseek-flash"
ADAPTER = "deepseek_openai"


def wire(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(wire(value).encode()).hexdigest()


def select(case):
    """Only allowlisted transcript fields reach either unchanged selector."""
    windows = [
        Window(row["id"], row["at"], document_text(row)) for row in case["exchanges"]
    ]
    query = query_text(case["query"], [])
    scores = {window.id: literal_score(query, window.text) for window in windows}
    baseline = rank_windows(
        [{"id": window.id, "assistant_at": window.assistant_at} for window in windows],
        scores,
    )
    return scores, {
        "baseline": [row["id"] for row in baseline],
        "candidate": select_diverse(windows, scores),
    }


def exchanges(case, context):
    return {
        row["id"]: {
            "run_id": f"{case['id']}-{row['id']}",
            "conversation_id": f"chat-{case['id']}-{row['id']}",
            "definition_version_id": "synthetic-prior-version",
            "archived": True,
            "messages": [
                {
                    "id": f"{case['id']}-{row['id']}-{role}",
                    "role": role,
                    "content": row[role],
                    "content_sha256": hashlib.sha256(row[role].encode()).hexdigest(),
                    "created_at": row["at"],
                    "sequence": index,
                }
                for index, role in enumerate(("user", "assistant"), 1)
            ],
            "annotations": context["history_annotations"],
        }
        for row in case["exchanges"]
    }


def build_packet(case, context, selected):
    assert len(selected) == len(set(selected)) <= MAX_ADMITTED_WINDOWS
    current = {
        "id": f"{case['id']}-current",
        "role": "user",
        "content": case["query"],
        "sequence": 1,
        "created_at": "2026-09-30T12:00:00+00:00",
    }
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
    by_id = exchanges(case, context)
    admission = admit_history(
        base=base.context,
        ranked_exchanges=[by_id[source_id] for source_id in selected],
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
    run_to_id = {exchange["run_id"]: source_id for source_id, exchange in by_id.items()}
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


def compact_assessment(judgment, admitted):
    full = assess_packet(judgment, admitted)
    return {
        "answer_routes": {row["id"]: row["supported"] for row in full["answer_routes"]},
        "visibility": {row["id"]: row["supported"] for row in full["visibility"]},
        "dependencies": {
            row["id"]: "not_triggered"
            if not row["trigger_present"]
            else "resolved"
            if row["supported"]
            else "missing"
            for row in full["dependencies"]
        },
        "optional": {row["id"]: row["supported"] for row in full["optional"]},
        "other_episode_admitted": full["other_episode_admitted"],
        "unrelated_admitted": full["unrelated_admitted"],
    }


def compare():
    context, cases, _ = load_inputs()
    labels = load_judgments()
    assert (
        CONVERSATION_BUDGET.input_limit == 11213
        and REVIEWER_BUDGET.input_limit == 11469
    )
    assert (
        CONVERSATION_BUDGET.max_output_tokens
        == REVIEWER_BUDGET.max_output_tokens
        == 4096
    )
    assert LIMIT == TOP_K == MAX_ADMITTED_WINDOWS == 4
    assert (
        context["saved_facts"]
        == context["local_suffix"]
        == context["related_entities"]
        == []
    )
    mapping = json.loads((DIRECTORY / "mapping.json").read_bytes())
    historical = json.loads(
        (DIRECTORY.parent / "retrieval_diversity/observed.json").read_bytes()
    )["cases"]
    summary = {
        "kind": "synthetic_nonblind_packet_diagnostic_not_model_evaluation",
        "labels_commit": LABEL_COMMIT,
        "judgments_sha256": JUDGMENTS_SHA256,
        "input_manifest_sha256": FREEZE_SHA256,
        "context_sha256": digest(context),
        "cases": [],
    }
    artifacts = []
    for case, judgment in zip(cases, labels["cases"], strict=True):
        scores, choices = select(case)
        origin = mapping[case["id"]]
        if origin["fixture"] == "historical":
            for arm, selected in choices.items():
                assert selected == [
                    f"E{ord(source_id) - ord('a') + 1:02d}"
                    for source_id in historical[origin["id"]][arm]
                ]
        choices["empty"] = []
        # References enter only after selection, and remain evaluator-only.
        reference_uses = {}
        for field in ("answer_routes", "visibility"):
            for route in judgment[field]:
                for group in route["sets"]:
                    name = "reference-" + ("-".join(group) or "empty")
                    choices[name] = group
                    reference_uses.setdefault(name, []).append(f"{field}/{route['id']}")
        row = {"id": case["id"], "literal_scores": scores, "packets": {}}
        for name, selected in choices.items():
            receipt, requests = build_packet(case, context, selected)
            key = f"{case['id']}/{name}"
            row["packets"][name] = {
                **receipt,
                "artifact_key": key,
                "reference_for": reference_uses.get(name, []),
                "assessment": compact_assessment(judgment, receipt["admitted"]),
            }
            artifacts.append({"key": key, **requests})
        summary["cases"].append(row)
    summary["packets_sha256"] = hashlib.sha256(
        "".join(wire(packet) + "\n" for packet in artifacts).encode()
    ).hexdigest()
    return summary, artifacts


if __name__ == "__main__":
    result, packets = compare()
    (DIRECTORY / "comparison.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    (DIRECTORY / "packets.jsonl").write_text(
        "".join(wire(packet) + "\n" for packet in packets)
    )
    for case in result["cases"]:
        print(
            wire(
                {
                    "case": case["id"],
                    **{
                        name: {
                            "admitted": case["packets"][name]["admitted"],
                            "assessment": case["packets"][name]["assessment"],
                        }
                        for name in ("baseline", "candidate")
                    },
                }
            )
        )
