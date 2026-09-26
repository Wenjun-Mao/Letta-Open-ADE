"""Finite ranking probe; scores are supplied by literal or Qwen recipes."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any


TOP_K = 4
RECIPES = ("literal_token_match", "probe_local_qwen_cosine")


def query_text(current_user: str, local_suffix: Sequence[Mapping[str, str]]) -> str:
    """Build the same target-time query for both rankers, without scorer fields."""
    if not current_user.strip():
        raise ValueError("current user text is required")
    local = []
    for message in local_suffix:
        role = message["role"]
        if role not in {"user", "assistant"}:
            raise ValueError("local suffix contains an unsupported role")
        local.append({"role": role, "content": message["content"]})
    return json.dumps(
        {"current_user": current_user, "local_suffix": local},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def document_text(exchange: Mapping[str, str]) -> str:
    return f"User: {exchange['user']}\nAssistant: {exchange['assistant']}"


def literal_score(query: str, document: str) -> float:
    """Plain character-bigram overlap, without topic or phrase rules."""

    def bigrams(value: str) -> set[str]:
        normalized = "".join(char.casefold() for char in value if char.isalnum())
        return {normalized[index : index + 2] for index in range(len(normalized) - 1)}

    query_parts = bigrams(query)
    if not query_parts:
        return 0.0
    return len(query_parts & bigrams(document)) / len(query_parts)


def vector_recipe_identity(
    recipe: Mapping[str, Any], documents: Mapping[str, str]
) -> str:
    """Invalidate probe-local vectors when corpus text or recipe changes."""
    payload = {
        "recipe": dict(recipe),
        "documents": {
            exchange_id: hashlib.sha256(text.encode()).hexdigest()
            for exchange_id, text in sorted(documents.items())
        },
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def cosine_score(
    query_vector: Sequence[float], document_vector: Sequence[float], *, dimensions: int
) -> float:
    if len(query_vector) != dimensions or len(document_vector) != dimensions:
        raise ValueError("history vectors have the wrong dimension")
    if not all(math.isfinite(value) for value in (*query_vector, *document_vector)):
        raise ValueError("history vectors must be finite")
    query_norm = math.sqrt(sum(value * value for value in query_vector))
    document_norm = math.sqrt(sum(value * value for value in document_vector))
    if query_norm == 0 or document_norm == 0:
        raise ValueError("history vectors cannot be zero")
    return sum(a * b for a, b in zip(query_vector, document_vector, strict=True)) / (
        query_norm * document_norm
    )


def rank_windows(
    exchanges: Sequence[Mapping[str, Any]], scores: Mapping[str, float]
) -> list[dict[str, Any]]:
    """Select complete windows by score, then source time, then stable ID."""
    ids = [str(exchange["id"]) for exchange in exchanges]
    if len(ids) != len(set(ids)) or set(scores) != set(ids):
        raise ValueError("scores must cover each corpus exchange exactly once")
    if any(not math.isfinite(score) for score in scores.values()):
        raise ValueError("ranking scores must be finite")
    ordered = sorted(exchanges, key=lambda exchange: str(exchange["id"]))
    ordered.sort(key=lambda exchange: exchange["assistant_at"], reverse=True)
    ordered.sort(key=lambda exchange: scores[str(exchange["id"])], reverse=True)
    return [
        {"id": str(exchange["id"]), "score": scores[str(exchange["id"])]}
        for exchange in ordered[:TOP_K]
    ]


def assess_rank(
    corpus_ids: Sequence[str],
    ranked: Sequence[Mapping[str, Any]],
    minimum_evidence: Sequence[str],
) -> dict[str, Any]:
    corpus, selected, required = (
        set(corpus_ids),
        {str(item["id"]) for item in ranked},
        set(minimum_evidence),
    )
    if not required:
        return {
            "status": "irrelevant_admission",
            "admitted_irrelevant": len(ranked),
            "missing": [],
            "topic_hit": False,
        }
    missing = sorted(required - selected)
    topic_hit = bool(required & selected)
    status = (
        "corpus_miss"
        if required - corpus
        else "insufficient_evidence"
        if missing and topic_hit
        else "ranking_miss"
        if missing
        else "sufficient"
    )
    return {
        "status": status,
        "admitted_irrelevant": 0,
        "missing": missing,
        "topic_hit": topic_hit,
    }


def choose_ranker(
    assessments: Mapping[str, Mapping[str, Mapping[str, Any]]],
    positive_case_ids: Sequence[str],
    unrelated_case_id: str,
) -> dict[str, Any]:
    """Choose least complex adequate recipe; retain irrelevant-admission risk."""
    if set(assessments) != set(RECIPES):
        raise ValueError("both frozen rankers must be evaluated")
    adequate = [
        recipe
        for recipe in RECIPES
        if all(
            assessments[recipe][case_id]["status"] == "sufficient"
            for case_id in positive_case_ids
        )
    ]
    if not adequate:
        return {
            "selected": None,
            "reason": "minimum evidence not recovered",
            "assessments": assessments,
        }
    selected = min(
        adequate,
        key=lambda recipe: (
            assessments[recipe][unrelated_case_id]["admitted_irrelevant"],
            RECIPES.index(recipe),
        ),
    )
    return {
        "selected": selected,
        "reason": "least complex adequate recipe at measured unrelated admission",
        "assessments": assessments,
    }
