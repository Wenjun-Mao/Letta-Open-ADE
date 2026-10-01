"""Query-relative author judgments evaluated only after source selection."""

from __future__ import annotations


def reference_sets(judgment: dict) -> dict[tuple[str, ...], list[str]]:
    references: dict[tuple[str, ...], list[str]] = {}
    for field in (
        "answer_routes",
        "correction_explanation",
        "correction_intent",
        "mistaken_retelling",
        "optional_detail",
    ):
        for group in judgment[field]:
            key = tuple(sorted(group))
            references.setdefault(key, []).append(field)
    return references


def assess_packet(judgment: dict, admitted: list[str]) -> dict:
    selected = set(admitted)

    def supported(field):
        return any(set(group) <= selected for group in judgment[field])

    correction = judgment["dependency"]["trigger"]
    antecedent = judgment["dependency"]["antecedent"]
    if correction not in selected:
        dependency = "correction_absent"
    elif judgment["variant"] == "self_contained":
        dependency = "not_applicable"
    else:
        dependency = "resolved" if antecedent in selected else "missing"
    return {
        "named_answer_supported": supported("answer_routes"),
        "answer_alternatives": [
            {
                "sources": group,
                "supported": set(group) <= selected,
                "missing": sorted(set(group) - selected),
            }
            for group in judgment["answer_routes"]
        ],
        "correction_admitted": correction in selected,
        "dependency_status": dependency,
        "correction_explanation_supported": supported("correction_explanation"),
        "correction_intent_visible": supported("correction_intent"),
        "mistaken_retelling_visible": supported("mistaken_retelling"),
        "optional_detail_supported": supported("optional_detail"),
        "unrelated_admitted": sorted(selected & set(judgment["unrelated"])),
        "other_episode_admitted": sorted(selected & set(judgment["other_episode"])),
        "unresolved": judgment["uncertainty"],
    }
