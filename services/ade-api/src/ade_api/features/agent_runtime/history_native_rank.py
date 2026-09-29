"""Source-guarded, probe-local ranking of one frozen historical snapshot."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .embeddings import EmbeddingClient
from .errors import RuntimeValidationError
from .history_ranking import (
    cosine_score,
    document_text,
    literal_score,
    query_text,
    rank_windows,
    vector_recipe_identity,
)
from .router_transport import RouterRequestError

HISTORY_EMBEDDING_ROUTE = "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B"
HISTORY_VECTOR_RECIPE: dict[str, Any] = {
    "route": HISTORY_EMBEDDING_ROUTE,
    "artifact_reference": "Qwen/Qwen3-Embedding-0.6B",
    "artifact_revision": "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3",
    "dimensions": 1024,
    "query_format": "history-query-json-v1 via history_ranking.query_text; no fact-space instruction",
    "document_format": "history-exchange-roles-v1 via history_ranking.document_text",
    "normalization": "L2 at probe comparison",
    "comparison": "cosine similarity",
    "identity": "SHA-256 of this recipe and sorted exchange-ID/document-text hashes; regenerate all probe-local vectors on recipe or corpus change",
}
HISTORY_VECTOR_RECIPE_V2: dict[str, Any] = {
    **HISTORY_VECTOR_RECIPE,
    "query_format": (
        "history-query-json-v2: current-only and current-plus-local-suffix "
        "via history_ranking.query_text"
    ),
    "comparison": "0.7 current-only cosine + 0.3 contextual cosine",
}
QWEN_RECIPES = frozenset({"probe_local_qwen_cosine", "probe_local_qwen_cosine_v2"})


@dataclass(frozen=True)
class NativeHistoryRank:
    exchanges: list[dict[str, Any]]
    ranked: list[dict[str, Any]]
    all_scores: dict[str, float]
    status: str
    query_sha256: str
    recipe_identity: str
    document_hashes: dict[str, str]
    embedding_dispatches: int
    embedding_seconds: float


async def rank_native_history(
    *,
    exchanges: Sequence[dict[str, Any]],
    current_user: str,
    local_suffix: Sequence[dict[str, Any]],
    recipe: Literal[
        "literal_token_match", "probe_local_qwen_cosine", "probe_local_qwen_cosine_v2"
    ],
    embeddings: EmbeddingClient | None,
    model_key: str | None,
    deadline: float,
    authorize_sources: Callable[[list[dict[str, Any]]], Awaitable[set[str]]],
    mark_exposed: Callable[[], None],
) -> NativeHistoryRank:
    """Read only snapshot rows; guard every source-bearing embedding dispatch.

    Authorization returns genuinely missing run IDs only before exposure. SQL,
    scope, hash, generation and deadline failures remain fatal at this boundary.
    """
    corpus = list(exchanges)
    query = query_text(current_user, local_suffix)
    query_inputs = (
        [query_text(current_user, []), query]
        if recipe == "probe_local_qwen_cosine_v2" and local_suffix
        else [query]
    )
    dispatches = 0
    elapsed = 0.0
    status = "ranked"
    if recipe not in {"literal_token_match", *QWEN_RECIPES}:
        raise RuntimeValidationError("Unknown frozen history ranking recipe")
    if recipe in QWEN_RECIPES and (
        embeddings is None or model_key != HISTORY_EMBEDDING_ROUTE
    ):
        raise RuntimeValidationError("Frozen Qwen history route is unavailable")

    documents = {
        str(exchange["run_id"]): document_text(
            {
                "user": exchange["messages"][0]["content"],
                "assistant": exchange["messages"][1]["content"],
            }
        )
        for exchange in corpus
    }
    if len(documents) != len(corpus):
        raise RuntimeValidationError("Historical corpus has duplicate run IDs")
    if recipe in QWEN_RECIPES and corpus:
        # A genuine purge before first exposure removes whole windows. A database
        # error, altered row or purge after exposure cannot become an empty rank.
        while corpus:
            missing = await authorize_sources(corpus)
            if not missing:
                break
            corpus = [item for item in corpus if str(item["run_id"]) not in missing]
            status = "purged"
        documents = {
            key: value
            for key, value in documents.items()
            if key in {str(item["run_id"]) for item in corpus}
        }
        if corpus:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeValidationError(
                    "History ranking deadline expired",
                    detail_code="natural_history_timeout",
                )
            mark_exposed()
            started = time.monotonic()
            dispatches += 1
            try:
                document_vectors = await embeddings.embed(
                    model_key=model_key,
                    inputs=list(documents.values()),
                    timeout_seconds=remaining,
                )
            except (RouterRequestError, TimeoutError) as exc:
                raise RuntimeValidationError(
                    "History document embedding failed without retry",
                    detail_code="natural_history_embedding_unavailable",
                ) from exc
            elapsed += time.monotonic() - started
            # Query format contains only the selected current/local suffix. The
            # source corpus is still authorized afresh immediately before send.
            missing = await authorize_sources(corpus)
            if missing:
                raise RuntimeValidationError(
                    "Exposed ranking source was removed",
                    detail_code="natural_history_missing",
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeValidationError(
                    "History ranking deadline expired",
                    detail_code="natural_history_timeout",
                )
            started = time.monotonic()
            dispatches += 1
            try:
                query_vectors = await embeddings.embed(
                    model_key=model_key,
                    inputs=query_inputs,
                    timeout_seconds=remaining,
                )
            except (RouterRequestError, TimeoutError) as exc:
                raise RuntimeValidationError(
                    "History query embedding failed without retry",
                    detail_code="natural_history_embedding_unavailable",
                ) from exc
            elapsed += time.monotonic() - started
            scores = {}
            for exchange_id, vector in zip(documents, document_vectors, strict=True):
                contextual_score = cosine_score(
                    query_vectors[-1],
                    vector,
                    dimensions=HISTORY_VECTOR_RECIPE["dimensions"],
                )
                scores[exchange_id] = (
                    0.7
                    * cosine_score(
                        query_vectors[0],
                        vector,
                        dimensions=HISTORY_VECTOR_RECIPE["dimensions"],
                    )
                    + 0.3 * contextual_score
                    if len(query_vectors) == 2
                    else contextual_score
                )
        else:
            scores = {}
    else:
        scores = {
            key: literal_score(query, document) for key, document in documents.items()
        }

    windows = [
        {"id": str(item["run_id"]), "assistant_at": item["messages"][1]["created_at"]}
        for item in corpus
    ]
    ranked = rank_windows(windows, scores) if windows else []
    by_id = {str(item["run_id"]): item for item in corpus}
    return NativeHistoryRank(
        exchanges=[by_id[item["id"]] for item in ranked],
        ranked=ranked,
        all_scores=scores,
        status=status,
        query_sha256=hashlib.sha256(
            (
                query
                if len(query_inputs) == 1
                else json.dumps(query_inputs, ensure_ascii=False, separators=(",", ":"))
            ).encode()
        ).hexdigest(),
        recipe_identity=vector_recipe_identity(
            (
                HISTORY_VECTOR_RECIPE_V2
                if recipe == "probe_local_qwen_cosine_v2"
                else HISTORY_VECTOR_RECIPE
            )
            if recipe in QWEN_RECIPES
            else {
                "literal_recipe": "casefolded alphanumeric character bigram query overlap fraction"
            },
            documents,
        ),
        document_hashes={
            key: hashlib.sha256(value.encode()).hexdigest()
            for key, value in documents.items()
        },
        embedding_dispatches=dispatches,
        embedding_seconds=elapsed,
    )
