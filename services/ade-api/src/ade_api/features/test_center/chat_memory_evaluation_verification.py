from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def recompute_deterministic_score(
    *,
    assistant_texts: Iterable[str],
    initial_human_memory: str,
    final_human_memory: str,
    expected_facts: Iterable[Mapping[str, Any]],
    forbidden_reply_substrings: Iterable[str],
) -> dict[str, Any]:
    """Independently reconstruct the workflow's deterministic score from evidence."""

    forbidden = tuple(str(item) for item in forbidden_reply_substrings)
    forbidden_hits = [
        {
            "assistant_reply": text,
            "hits": [needle for needle in forbidden if needle.lower() in text.lower()],
        }
        for text in assistant_texts
    ]
    forbidden_hits = [item for item in forbidden_hits if item["hits"]]

    normalized_memory = final_human_memory.lower()
    fact_scores: list[dict[str, Any]] = []
    for fact in expected_facts:
        aliases = [str(alias) for alias in fact.get("aliases", [])]
        matches = [alias for alias in aliases if alias.lower() in normalized_memory]
        fact_scores.append(
            {
                "key": str(fact.get("key", "")),
                "label": str(fact.get("label", "")),
                "passed": bool(matches),
                "matched_aliases": matches,
                "aliases": aliases,
            }
        )

    missing = [score["key"] for score in fact_scores if not score["passed"]]
    memory_changed = initial_human_memory.strip() != final_human_memory.strip()
    return {
        "pass": memory_changed and not missing and not forbidden_hits,
        "forbidden_hits": forbidden_hits,
        "forbidden_hit_count": len(forbidden_hits),
        "human_memory_changed": memory_changed,
        "expected_fact_scores": fact_scores,
        "expected_facts_passed": not missing,
        "missing_expected_facts": missing,
    }
