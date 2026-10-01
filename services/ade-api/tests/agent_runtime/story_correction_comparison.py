"""Frozen non-blind matched correction study; no providers, database or oracle selection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ade_api.features.agent_runtime.history_admission import MAX_ADMITTED_WINDOWS
from ade_api.features.agent_runtime.history_ranking import (
    TOP_K,
    document_text,
    literal_score,
    query_text,
    rank_windows,
)
from workflows.evals.character_memory_dev.story_continuity.correction_dependencies.assessment import (
    assess_packet,
    reference_sets,
)
from workflows.evals.character_memory_dev.story_continuity.correction_dependencies.inputs import (
    DIRECTORY,
    FREEZE_SHA256,
    ROOT,
    load_inputs,
    load_judgments,
)
from workflows.evals.character_memory_dev.story_continuity.retrieval_diversity.selector import (
    LIMIT,
    Window,
    select_diverse,
)


if __package__:
    from .story_packet_builder import build_history_packet, digest, wire
else:
    from story_packet_builder import build_history_packet, digest, wire


LABEL_COMMIT = "2447917ddd979a8459d23e1998c421aa22f196bf"
ARMS = ("baseline", "candidate")


def select(case):
    """Only transcript fields, opaque IDs, chronology and literal scores reach selectors."""
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
    result = {}
    for row in case["exchanges"]:
        run_id = f"{case['conversation_id']}-{row['id']}"
        result[row["id"]] = {
            "run_id": run_id,
            "conversation_id": case["conversation_id"],
            "definition_version_id": "synthetic-prior-version",
            "archived": True,
            "messages": [
                {
                    "id": f"{run_id}-{role}",
                    "role": role,
                    "content": row[role],
                    "content_sha256": hashlib.sha256(row[role].encode()).hexdigest(),
                    "created_at": row["user_at"] if role == "user" else row["at"],
                    "sequence": row[f"{role}_sequence"],
                }
                for role in ("user", "assistant")
            ],
            "annotations": context["history_annotations"],
        }
    return result


def current_message(case):
    return {
        "id": f"{case['conversation_id']}-current-user",
        "role": "user",
        "content": case["query"],
        "sequence": 1,
        "created_at": "2026-09-30T12:00:00+00:00",
    }


def build_packet(case, context, selected):
    sources = exchanges(case, context)
    receipt, requests = build_history_packet(
        current=current_message(case),
        context=context,
        sources=sources,
        selected=selected,
    )
    history = json.loads(requests["reviewer"]["messages"][1]["content"])["history"]
    source_order = []
    for source_id, supplied in zip(receipt["admitted"], history, strict=True):
        source = sources[source_id]
        for original, message in zip(
            source["messages"], supplied["messages"], strict=True
        ):
            source_order.append(
                {
                    "source_id": source_id,
                    "message_id": original["id"],
                    "conversation_id": source["conversation_id"],
                    "sequence": original["sequence"],
                    "role": original["role"],
                    "handle": message["handle"],
                    "created_at": message["created_at"],
                    "content_sha256": message["content_sha256"],
                }
            )
    return {**receipt, "source_order": source_order}, requests


def paired_signals(rows):
    by_id = {row["id"]: row for row in rows}
    pairs = []
    for index in range(1, 4):
        direct = by_id[f"D{index * 2 - 1:02d}"]
        dependent = by_id[f"D{index * 2:02d}"]
        reference = dependent["packets"]["reference-E01-E07"]
        resolvable = (
            not reference["omitted_capacity"]
            and reference["assessment"]["named_answer_supported"]
            and reference["assessment"]["correction_explanation_supported"]
        )
        signals = {}
        for arm in ARMS:
            first_packet = direct["packets"][arm]
            second_packet = dependent["packets"][arm]
            first = first_packet["assessment"]
            second = second_packet["assessment"]
            signals[arm] = (
                not first_packet["omitted_capacity"]
                and not second_packet["omitted_capacity"]
                and first["correction_admitted"]
                and first["named_answer_supported"]
                and second["correction_admitted"]
                and not second["named_answer_supported"]
                and second["dependency_status"] == "missing"
                and not first["unresolved"]
                and not second["unresolved"]
                and resolvable
            )
        pairs.append(
            {
                "id": f"P{index:02d}",
                "self_contained": direct["id"],
                "antecedent_dependent": dependent["id"],
                "reference_resolves": resolvable,
                "dependency_specific_signal": signals,
            }
        )
    return {
        "pairs": pairs,
        "investment_trigger_met": {
            arm: sum(pair["dependency_specific_signal"][arm] for pair in pairs) >= 2
            for arm in ARMS
        },
        "meaning": "A diagnostic investment trigger only; never selector adoption or a quality score.",
    }


def compare():
    context, cases = load_inputs()
    assert LIMIT == TOP_K == MAX_ADMITTED_WINDOWS == 4
    # Finish both unchanged selections before decoding evaluator judgments.
    selections = {case["id"]: select(case) for case in cases}
    labels = load_judgments()
    execution_paths = [
        Path(__file__),
        Path(__file__).with_name("story_packet_builder.py"),
        DIRECTORY / "inputs.py",
        DIRECTORY / "assessment.py",
    ]
    summary = {
        "kind": "nonblind_author_matched_packet_measurement_not_model_evaluation",
        "labels_commit": LABEL_COMMIT,
        "input_manifest_sha256": FREEZE_SHA256,
        "context_sha256": digest(context),
        "execution_sources": {
            str(path.resolve().relative_to(ROOT)): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in execution_paths
        },
        "cases": [],
    }
    artifacts = []
    for case, judgment in zip(cases, labels["cases"], strict=True):
        scores, chosen = selections[case["id"]]
        choices = {**chosen, "empty": []}
        uses = {}
        for sources, fields in reference_sets(judgment).items():
            name = "reference-" + "-".join(sources)
            choices[name] = list(sources)
            uses[name] = fields
        row = {
            "id": case["id"],
            "pair": judgment["id"],
            "variant": judgment["variant"],
            "historical_conversation_id": case["conversation_id"],
            "current_conversation_id": f"fresh-{case['conversation_id']}",
            "literal_scores": scores,
            "text_lengths": {
                "unit": "unicode_code_points",
                "current_user": len(case["query"]),
                "scored_query": len(query_text(case["query"], [])),
                "sources": {
                    source["id"]: {
                        "user": len(source["user"]),
                        "assistant": len(source["assistant"]),
                        "scored_document": len(document_text(source)),
                    }
                    for source in case["exchanges"]
                },
            },
            "packets": {},
        }
        for name, selected in choices.items():
            receipt, requests = build_packet(case, context, selected)
            key = f"{case['id']}/{name}"
            not_requested = sorted(
                {source["id"] for source in case["exchanges"]} - set(selected)
            )
            row["packets"][name] = {
                **receipt,
                "artifact_key": key,
                "reference_for": uses.get(name, []),
                "omissions": {
                    "selection": not_requested if name in ARMS else [],
                    "capacity": receipt["omitted_capacity"],
                    "evaluator_not_requested": [] if name in ARMS else not_requested,
                },
                "assessment": assess_packet(judgment, receipt["admitted"]),
            }
            artifacts.append({"key": key, **requests})
        summary["cases"].append(row)
    summary["paired_assessment"] = paired_signals(summary["cases"])
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
    for row in result["cases"]:
        print(
            wire(
                {
                    "case": row["id"],
                    "variant": row["variant"],
                    **{
                        arm: {
                            "admitted": row["packets"][arm]["admitted"],
                            "assessment": row["packets"][arm]["assessment"],
                        }
                        for arm in ARMS
                    },
                }
            )
        )
    print(wire(result["paired_assessment"]))
