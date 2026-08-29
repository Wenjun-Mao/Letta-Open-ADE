"""Deterministic, study-only semantic retrieval primitives.

This module deliberately has no dependency on the ADE API or the production
memory store.  Its remote embeddings client is OpenAI-compatible, but all
evaluation helpers accept an :class:`EmbeddingProvider`, so static tests can
use a fake and never make a network request.
"""

from __future__ import annotations

import json
import math
import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_EMBEDDINGS_BASE_URL = "http://127.0.0.1:8001/v1"
DEFAULT_EMBEDDINGS_MODEL = "Qwen/Qwen3-Embedding-0.6B"
DEFAULT_EMBEDDING_DIMENSIONS = 1024
DEFAULT_QUERY_INSTRUCTION = (
    "Given a user-memory question, retrieve relevant stored memories that "
    "answer the query."
)

Vector = tuple[float, ...]


class EmbeddingRequestError(RuntimeError):
    """Raised when the configured embeddings endpoint cannot serve one request."""


class FixtureError(ValueError):
    """Raised when a semantic retrieval fixture is malformed."""


class RetrievalStrategy(str, Enum):
    LEXICAL = "lexical"
    ALIAS = "alias"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Small synchronous protocol shared by remote and fake embedding clients."""

    def embed(self, texts: Sequence[str]) -> tuple[Vector, ...]:
        """Return one embedding vector for each input, in the same order."""


@dataclass(frozen=True, slots=True)
class EmbeddingClientConfig:
    """Explicit OpenAI-compatible embeddings endpoint settings.

    ``max_retries`` is intentionally fixed at zero.  This study needs the
    measured caller-visible latency and failure behavior, not client-side retry
    smoothing.  Defaults are dataclass defaults rather than ``value or default``
    substitutions, so any explicit caller value remains observable.
    """

    base_url: str = DEFAULT_EMBEDDINGS_BASE_URL
    model: str = DEFAULT_EMBEDDINGS_MODEL
    dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS
    timeout_seconds: float = 10.0
    api_key: str | None = None
    max_retries: int = 0
    extra_headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.base_url.strip():
            raise ValueError("base_url is required")
        if not self.model.strip():
            raise ValueError("model is required")
        if self.dimensions <= 0:
            raise ValueError("dimensions must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_retries != 0:
            raise ValueError("semantic retrieval embeddings client permits zero retries")

    @property
    def embeddings_url(self) -> str:
        base = self.base_url.rstrip("/")
        return base if base.endswith("/embeddings") else f"{base}/embeddings"


class OpenAICompatibleEmbeddingsClient:
    """A one-attempt OpenAI ``/embeddings`` client with strict response checks."""

    def __init__(
        self,
        config: EmbeddingClientConfig | None = None,
        *,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config if config is not None else EmbeddingClientConfig()
        self._opener = opener if opener is not None else urlopen

    def embed(self, texts: Sequence[str]) -> tuple[Vector, ...]:
        values = tuple(texts)
        if not values:
            return ()
        if any(not isinstance(value, str) for value in values):
            raise TypeError("embedding inputs must be strings")

        payload = json.dumps(
            {
                "model": self.config.model,
                "input": list(values),
                "dimensions": self.config.dimensions,
            }
        ).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **dict(self.config.extra_headers),
        }
        if self.config.api_key is not None:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        request = Request(
            self.config.embeddings_url,
            data=payload,
            headers=headers,
            method="POST",
        )

        # There is intentionally exactly one opener call: no SDK, transport, or
        # local retry loop is allowed in this study client.
        try:
            with self._opener(request, timeout=self.config.timeout_seconds) as response:
                raw_body = response.read()
        except (HTTPError, URLError, OSError, TimeoutError) as error:
            raise EmbeddingRequestError(
                f"Embeddings request to {self.config.embeddings_url} failed"
            ) from error
        try:
            payload_data = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise EmbeddingRequestError("Embeddings endpoint returned invalid JSON") from error
        return self._parse_response(payload_data, len(values))

    def _parse_response(self, payload: object, expected_count: int) -> tuple[Vector, ...]:
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise EmbeddingRequestError("Embeddings response must contain a data array")
        records = payload["data"]
        indexed: dict[int, Vector] = {}
        for record in records:
            if not isinstance(record, dict):
                raise EmbeddingRequestError("Embeddings response data item must be an object")
            index = record.get("index")
            embedding = record.get("embedding")
            if not isinstance(index, int) or not isinstance(embedding, list):
                raise EmbeddingRequestError(
                    "Embeddings response item requires integer index and embedding array"
                )
            if index in indexed or index < 0 or index >= expected_count:
                raise EmbeddingRequestError("Embeddings response contains an invalid index")
            try:
                vector = tuple(float(value) for value in embedding)
            except (TypeError, ValueError) as error:
                raise EmbeddingRequestError("Embedding values must be numeric") from error
            if len(vector) != self.config.dimensions:
                raise EmbeddingRequestError(
                    f"Expected {self.config.dimensions} dimensions, received {len(vector)}"
                )
            indexed[index] = vector
        if len(indexed) != expected_count:
            raise EmbeddingRequestError("Embeddings response count does not match input count")
        return tuple(indexed[index] for index in range(expected_count))


def format_qwen3_query(
    query: str, instruction: str | None = DEFAULT_QUERY_INSTRUCTION
) -> str:
    """Format a Qwen3 query while leaving document text unmodified.

    Pass ``None`` or an explicit empty string to disable instruction wrapping.
    """

    if instruction is None or not instruction.strip():
        return query
    return f"Instruct: {instruction.strip()}\nQuery: {query}"


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Return stable cosine similarity; zero vectors have zero similarity."""

    if len(left) != len(right):
        raise ValueError("cosine similarity requires vectors with equal dimensions")
    if not left:
        raise ValueError("cosine similarity requires non-empty vectors")
    dot = sum(float(a) * float(b) for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(float(value) ** 2 for value in left))
    right_norm = math.sqrt(sum(float(value) ** 2 for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


@dataclass(frozen=True, slots=True)
class RetrievalDocument:
    id: str
    subject_id: str
    text: str
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("document id is required")
        if not self.subject_id.strip():
            raise ValueError("document subject_id is required")
        if not self.text.strip():
            raise ValueError("document text is required")


@dataclass(frozen=True, slots=True)
class RetrievalConfig:
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    limit: int = 3
    minimum_score: float | None = None
    query_instruction: str | None = DEFAULT_QUERY_INSTRUCTION
    semantic_weight: float = 0.65
    lexical_weight: float = 0.20
    alias_weight: float = 0.15

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("limit must be positive")
        if self.minimum_score is not None and not -1.0 <= self.minimum_score <= 1.0:
            raise ValueError("minimum_score must fall between -1 and 1")
        if min(self.semantic_weight, self.lexical_weight, self.alias_weight) < 0:
            raise ValueError("hybrid weights cannot be negative")
        if self.semantic_weight + self.lexical_weight + self.alias_weight <= 0:
            raise ValueError("at least one hybrid weight must be positive")


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    document: RetrievalDocument
    score: float
    lexical_score: float
    alias_score: float
    semantic_score: float | None


class SemanticRetriever:
    """Subject-bound deterministic ranker with optional embedding-backed modes."""

    def __init__(
        self,
        documents: Sequence[RetrievalDocument],
        embeddings: EmbeddingProvider | None = None,
        *,
        config: RetrievalConfig | None = None,
    ) -> None:
        seen_ids: set[str] = set()
        for document in documents:
            if document.id in seen_ids:
                raise ValueError(f"document ids must be unique: {document.id}")
            seen_ids.add(document.id)
        self._documents = tuple(documents)
        self._embeddings = embeddings
        self.config = config if config is not None else RetrievalConfig()
        self._document_vectors: dict[str, Vector] = {}

    @property
    def documents(self) -> tuple[RetrievalDocument, ...]:
        return self._documents

    def search(
        self,
        subject_id: str,
        query: str,
        *,
        strategy: RetrievalStrategy | str | None = None,
        limit: int | None = None,
        minimum_score: float | None | object = ...,
        query_instruction: str | None | object = ...,
    ) -> tuple[RetrievalResult, ...]:
        """Rank only documents owned by ``subject_id``.

        ``None`` for ``limit`` returns every eligible candidate, which is useful
        for calibration.  The ellipsis sentinel distinguishes an omitted
        threshold/instruction from an explicit ``None`` supplied by a caller.
        """

        selected_strategy = RetrievalStrategy(
            self.config.strategy if strategy is None else strategy
        )
        selected_limit = self.config.limit if limit is None else limit
        if selected_limit is not None and selected_limit <= 0:
            raise ValueError("limit must be positive or None")
        selected_threshold = (
            self.config.minimum_score
            if minimum_score is ...
            else minimum_score
        )
        if selected_threshold is not None and not isinstance(selected_threshold, float | int):
            raise TypeError("minimum_score must be a number or None")
        instruction = (
            self.config.query_instruction
            if query_instruction is ...
            else query_instruction
        )
        if instruction is not None and not isinstance(instruction, str):
            raise TypeError("query_instruction must be a string or None")

        candidates = tuple(
            document for document in self._documents if document.subject_id == subject_id
        )
        need_semantic = selected_strategy in {
            RetrievalStrategy.SEMANTIC,
            RetrievalStrategy.HYBRID,
        }
        query_vector: Vector | None = None
        if need_semantic:
            if self._embeddings is None:
                raise ValueError("semantic retrieval requires an embedding provider")
            self._ensure_document_vectors(candidates)
            query_vector = self._one_embedding(format_qwen3_query(query, instruction))

        results: list[RetrievalResult] = []
        for document in candidates:
            lexical_score = lexical_similarity(query, document.text)
            alias_score = alias_similarity(query, document.aliases)
            semantic_score = (
                cosine_similarity(query_vector, self._document_vectors[document.id])
                if query_vector is not None
                else None
            )
            score = _strategy_score(
                selected_strategy,
                lexical_score=lexical_score,
                alias_score=alias_score,
                semantic_score=semantic_score,
                config=self.config,
            )
            if selected_threshold is None or score >= float(selected_threshold):
                results.append(
                    RetrievalResult(
                        document=document,
                        score=score,
                        lexical_score=lexical_score,
                        alias_score=alias_score,
                        semantic_score=semantic_score,
                    )
                )

        # Document id is a deliberate final tie breaker, so equal vectors and
        # equal lexical scores never inherit insertion-order nondeterminism.
        results.sort(key=lambda result: (-result.score, result.document.id))
        return tuple(results if selected_limit is None else results[:selected_limit])

    def _ensure_document_vectors(self, documents: Sequence[RetrievalDocument]) -> None:
        pending = tuple(document for document in documents if document.id not in self._document_vectors)
        if not pending:
            return
        vectors = self._embeddings_or_raise().embed(tuple(document.text for document in pending))
        if len(vectors) != len(pending):
            raise ValueError("embedding provider returned an unexpected document count")
        for document, vector in zip(pending, vectors, strict=True):
            self._document_vectors[document.id] = _coerce_vector(vector)

    def _one_embedding(self, text: str) -> Vector:
        vectors = self._embeddings_or_raise().embed((text,))
        if len(vectors) != 1:
            raise ValueError("embedding provider must return exactly one query vector")
        return _coerce_vector(vectors[0])

    def _embeddings_or_raise(self) -> EmbeddingProvider:
        if self._embeddings is None:
            raise ValueError("semantic retrieval requires an embedding provider")
        return self._embeddings


def lexical_similarity(query: str, document_text: str) -> float:
    """Return token-overlap recall from the query into a document."""

    query_tokens = set(_tokens(query))
    if not query_tokens:
        return 0.0
    document_tokens = set(_tokens(document_text))
    return len(query_tokens & document_tokens) / len(query_tokens)


def alias_similarity(query: str, aliases: Sequence[str]) -> float:
    """Return the best alias match, including non-Latin exact-substring matches."""

    normalized_query = _normalized(query)
    if not normalized_query:
        return 0.0
    query_tokens = set(_tokens(query))
    best = 0.0
    for alias in aliases:
        normalized_alias = _normalized(alias)
        if not normalized_alias:
            continue
        if normalized_query in normalized_alias or normalized_alias in normalized_query:
            return 1.0
        alias_tokens = set(_tokens(alias))
        if query_tokens and alias_tokens:
            best = max(best, len(query_tokens & alias_tokens) / len(query_tokens))
    return best


def _strategy_score(
    strategy: RetrievalStrategy,
    *,
    lexical_score: float,
    alias_score: float,
    semantic_score: float | None,
    config: RetrievalConfig,
) -> float:
    if strategy is RetrievalStrategy.LEXICAL:
        return lexical_score
    if strategy is RetrievalStrategy.ALIAS:
        return alias_score
    if strategy is RetrievalStrategy.SEMANTIC:
        return semantic_score if semantic_score is not None else 0.0
    assert semantic_score is not None
    total_weight = config.semantic_weight + config.lexical_weight + config.alias_weight
    return (
        semantic_score * config.semantic_weight
        + lexical_score * config.lexical_weight
        + alias_score * config.alias_weight
    ) / total_weight


def _coerce_vector(vector: Sequence[float]) -> Vector:
    values = tuple(float(value) for value in vector)
    if not values:
        raise ValueError("embedding vectors cannot be empty")
    return values


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _tokens(value: str) -> tuple[str, ...]:
    normalized = _normalized(value)
    words = re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
    cjk = re.findall(r"[\u3400-\u9fff]", normalized)
    return tuple(words + cjk)


@dataclass(frozen=True, slots=True)
class RetrievalFixtureCase:
    id: str
    subject_id: str
    query: str
    expected_document_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    hard_negative: bool = False
    split: str = "held_out"

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.subject_id.strip() or not self.query.strip():
            raise ValueError("fixture case id, subject_id, and query are required")
        if self.hard_negative and self.expected_document_ids:
            raise ValueError("hard-negative cases cannot specify expected documents")
        if self.split not in {"calibration", "held_out"}:
            raise ValueError("fixture case split must be calibration or held_out")

    @property
    def is_cross_lingual(self) -> bool:
        return "cross_lingual" in self.tags


@dataclass(frozen=True, slots=True)
class RetrievalFixture:
    documents: tuple[RetrievalDocument, ...]
    cases: tuple[RetrievalFixtureCase, ...]
    corpus_size: int = 1000

    def __post_init__(self) -> None:
        if self.corpus_size < len(self.documents):
            raise ValueError("corpus_size cannot be smaller than fixture documents")


def load_retrieval_fixture(path: str | Path) -> RetrievalFixture:
    fixture_path = Path(path)
    try:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise FixtureError(f"Fixture suite not found: {fixture_path}") from error
    except json.JSONDecodeError as error:
        raise FixtureError(f"Fixture suite contains invalid JSON: {fixture_path}") from error
    if not isinstance(payload, dict):
        raise FixtureError("fixture suite must be an object")
    documents = tuple(_fixture_document(value) for value in _fixture_list(payload, "documents"))
    cases = tuple(_fixture_case(value) for value in _fixture_list(payload, "cases"))
    if not documents or not cases:
        raise FixtureError("fixture suite requires documents and cases")
    document_ids = [document.id for document in documents]
    case_ids = [case.id for case in cases]
    if len(document_ids) != len(set(document_ids)):
        raise FixtureError("fixture document ids must be unique")
    if len(case_ids) != len(set(case_ids)):
        raise FixtureError("fixture case ids must be unique")
    known_documents = set(document_ids)
    known_subjects = {document.subject_id for document in documents}
    for case in cases:
        if case.subject_id not in known_subjects:
            raise FixtureError(f"fixture case {case.id} has an unknown subject")
        missing = set(case.expected_document_ids) - known_documents
        if missing:
            raise FixtureError(f"fixture case {case.id} references unknown documents: {missing}")
    try:
        return RetrievalFixture(
            documents=documents,
            cases=cases,
            corpus_size=int(payload.get("corpus_size", 1000)),
        )
    except (TypeError, ValueError) as error:
        raise FixtureError(str(error)) from error


def _fixture_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise FixtureError(f"fixture suite {key} must be an array")
    return value


def _fixture_document(value: object) -> RetrievalDocument:
    if not isinstance(value, dict):
        raise FixtureError("fixture document must be an object")
    try:
        aliases = value.get("aliases", [])
        if not isinstance(aliases, list):
            raise FixtureError("fixture document aliases must be an array")
        return RetrievalDocument(
            id=_required_string(value, "id"),
            subject_id=_required_string(value, "subject_id"),
            text=_required_string(value, "text"),
            aliases=tuple(str(alias).strip() for alias in aliases if str(alias).strip()),
        )
    except ValueError as error:
        raise FixtureError(str(error)) from error


def _fixture_case(value: object) -> RetrievalFixtureCase:
    if not isinstance(value, dict):
        raise FixtureError("fixture case must be an object")
    expected = value.get("expected_document_ids", [])
    tags = value.get("tags", [])
    if not isinstance(expected, list) or not isinstance(tags, list):
        raise FixtureError("fixture case expected_document_ids and tags must be arrays")
    try:
        return RetrievalFixtureCase(
            id=_required_string(value, "id"),
            subject_id=_required_string(value, "subject_id"),
            query=_required_string(value, "query"),
            expected_document_ids=tuple(
                str(item).strip() for item in expected if str(item).strip()
            ),
            tags=tuple(str(item).strip() for item in tags if str(item).strip()),
            hard_negative=bool(value.get("hard_negative", False)),
            split=str(value.get("split", "held_out")).strip(),
        )
    except ValueError as error:
        raise FixtureError(str(error)) from error


def _required_string(value: Mapping[str, Any], key: str) -> str:
    parsed = str(value.get(key) or "").strip()
    if not parsed:
        raise FixtureError(f"fixture {key} is required")
    return parsed


def expand_corpus(
    documents: Sequence[RetrievalDocument], target_size: int = 1000
) -> tuple[RetrievalDocument, ...]:
    """Pad a fixture corpus with deterministic, unrelated subject-bound noise."""

    source = tuple(documents)
    if target_size < len(source):
        raise ValueError("target_size cannot be smaller than source corpus")
    if target_size == len(source):
        return source
    subjects = tuple(sorted({document.subject_id for document in source}))
    if not subjects:
        raise ValueError("cannot expand an empty corpus")
    padded = list(source)
    for index in range(len(source), target_size):
        padded.append(
            RetrievalDocument(
                id=f"semantic_retrieval_noise_{index:04d}",
                subject_id=subjects[index % len(subjects)],
                text=f"Archived unrelated maintenance ledger entry {index}.",
            )
        )
    return tuple(padded)


@dataclass(frozen=True, slots=True)
class EvaluationRow:
    case_id: str
    expected_document_ids: tuple[str, ...]
    ranked_document_ids: tuple[str, ...]
    hit: bool
    latency_ms: float


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    cross_lingual_recall_at_3: float
    overall_recall: float
    hard_negative_false_positive_rate: float
    p95_latency_ms: float
    evaluated_case_count: int
    positive_case_count: int
    cross_lingual_case_count: int
    hard_negative_case_count: int
    rows: tuple[EvaluationRow, ...]


def percentile_95(latencies_ms: Sequence[float]) -> float:
    """Compute p95 by the nearest-rank convention used by the study metrics."""

    if not latencies_ms:
        return 0.0
    ordered = sorted(float(value) for value in latencies_ms)
    return ordered[math.ceil(len(ordered) * 0.95) - 1]


def evaluate_cases(
    retriever: SemanticRetriever,
    cases: Sequence[RetrievalFixtureCase],
    *,
    strategy: RetrievalStrategy | str | None = None,
    threshold: float | None = None,
    query_instruction: str | None | object = ...,
    clock: Callable[[], float] = time.perf_counter,
) -> RetrievalMetrics:
    """Measure recall@3, hard-negative FPR, and p95 query latency."""

    rows: list[EvaluationRow] = []
    positive_hits = 0
    positive_count = 0
    cross_lingual_hits = 0
    cross_lingual_count = 0
    false_positives = 0
    hard_negative_count = 0
    for case in cases:
        started = clock()
        results = retriever.search(
            case.subject_id,
            case.query,
            strategy=strategy,
            limit=3,
            minimum_score=threshold,
            query_instruction=query_instruction,
        )
        latency_ms = (clock() - started) * 1000
        ranked_ids = tuple(result.document.id for result in results)
        hit = bool(set(case.expected_document_ids) & set(ranked_ids))
        if case.expected_document_ids:
            positive_count += 1
            positive_hits += int(hit)
        if case.is_cross_lingual:
            cross_lingual_count += 1
            cross_lingual_hits += int(hit)
        if case.hard_negative:
            hard_negative_count += 1
            false_positives += int(bool(results))
        rows.append(
            EvaluationRow(
                case_id=case.id,
                expected_document_ids=case.expected_document_ids,
                ranked_document_ids=ranked_ids,
                hit=hit,
                latency_ms=latency_ms,
            )
        )
    return RetrievalMetrics(
        cross_lingual_recall_at_3=(
            cross_lingual_hits / cross_lingual_count if cross_lingual_count else 0.0
        ),
        overall_recall=positive_hits / positive_count if positive_count else 0.0,
        hard_negative_false_positive_rate=(
            false_positives / hard_negative_count if hard_negative_count else 0.0
        ),
        p95_latency_ms=percentile_95([row.latency_ms for row in rows]),
        evaluated_case_count=len(rows),
        positive_case_count=positive_count,
        cross_lingual_case_count=cross_lingual_count,
        hard_negative_case_count=hard_negative_count,
        rows=tuple(rows),
    )


@dataclass(frozen=True, slots=True)
class ThresholdObservation:
    score: float
    is_relevant: bool


@dataclass(frozen=True, slots=True)
class ThresholdCalibration:
    threshold: float
    precision: float
    recall: float
    false_positive_rate: float
    balanced_accuracy: float
    observation_count: int


def calibrate_threshold(
    observations: Sequence[ThresholdObservation],
) -> ThresholdCalibration:
    """Select a deterministic threshold from calibration-only observations."""

    if not observations:
        raise ValueError("at least one threshold observation is required")
    values = tuple(observations)
    if any(not math.isfinite(observation.score) for observation in values):
        raise ValueError("threshold observations must have finite scores")
    candidates = sorted(
        {observation.score for observation in values}
        | {math.nextafter(max(observation.score for observation in values), math.inf)}
    )
    choices: list[ThresholdCalibration] = []
    for threshold in candidates:
        true_positive = sum(
            observation.is_relevant and observation.score >= threshold
            for observation in values
        )
        false_positive = sum(
            not observation.is_relevant and observation.score >= threshold
            for observation in values
        )
        positive_count = sum(observation.is_relevant for observation in values)
        negative_count = len(values) - positive_count
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 1.0
        )
        recall = true_positive / positive_count if positive_count else 1.0
        false_positive_rate = false_positive / negative_count if negative_count else 0.0
        true_negative_rate = 1.0 - false_positive_rate
        balanced_accuracy = (recall + true_negative_rate) / 2
        choices.append(
            ThresholdCalibration(
                threshold=threshold,
                precision=precision,
                recall=recall,
                false_positive_rate=false_positive_rate,
                balanced_accuracy=balanced_accuracy,
                observation_count=len(values),
            )
        )
    # Higher threshold wins exact ties, making false-positive avoidance explicit.
    return max(
        choices,
        key=lambda choice: (
            choice.balanced_accuracy,
            choice.precision,
            choice.recall,
            choice.threshold,
        ),
    )


def calibration_observations(
    retriever: SemanticRetriever,
    cases: Sequence[RetrievalFixtureCase],
    *,
    strategy: RetrievalStrategy | str | None = None,
    query_instruction: str | None | object = ...,
) -> tuple[ThresholdObservation, ...]:
    """Convert labelled fixture queries into threshold calibration observations."""

    observations: list[ThresholdObservation] = []
    for case in cases:
        results = retriever.search(
            case.subject_id,
            case.query,
            strategy=strategy,
            limit=None,
            minimum_score=None,
            query_instruction=query_instruction,
        )
        scores = {result.document.id: result.score for result in results}
        if case.expected_document_ids:
            matched = [scores[document_id] for document_id in case.expected_document_ids if document_id in scores]
            observations.append(
                ThresholdObservation(
                    score=max(matched) if matched else -1.0,
                    is_relevant=True,
                )
            )
        elif case.hard_negative:
            observations.append(
                ThresholdObservation(
                    score=max(scores.values(), default=-1.0),
                    is_relevant=False,
                )
            )
    return tuple(observations)


def calibrate_fixture_threshold(
    retriever: SemanticRetriever,
    fixture: RetrievalFixture,
    *,
    strategy: RetrievalStrategy | str | None = None,
    query_instruction: str | None | object = ...,
) -> ThresholdCalibration:
    """Calibrate strictly on fixture cases tagged ``calibration``."""

    observations = calibration_observations(
        retriever,
        tuple(case for case in fixture.cases if case.split == "calibration"),
        strategy=strategy,
        query_instruction=query_instruction,
    )
    return calibrate_threshold(observations)


def evaluate_held_out(
    retriever: SemanticRetriever,
    fixture: RetrievalFixture,
    *,
    strategy: RetrievalStrategy | str | None = None,
    threshold: float | None = None,
    query_instruction: str | None | object = ...,
    clock: Callable[[], float] = time.perf_counter,
) -> RetrievalMetrics:
    """Evaluate only fixture cases reserved as ``held_out``."""

    return evaluate_cases(
        retriever,
        tuple(case for case in fixture.cases if case.split == "held_out"),
        strategy=strategy,
        threshold=threshold,
        query_instruction=query_instruction,
        clock=clock,
    )


def evaluate_fixture(
    fixture: RetrievalFixture,
    embeddings: EmbeddingProvider,
    *,
    config: RetrievalConfig | None = None,
    corpus_size: int | None = None,
    calibrate: bool = True,
    clock: Callable[[], float] = time.perf_counter,
) -> tuple[ThresholdCalibration | None, RetrievalMetrics]:
    """Build the configured corpus, calibrate, then score held-out fixture data."""

    target_size = fixture.corpus_size if corpus_size is None else corpus_size
    retriever = SemanticRetriever(
        expand_corpus(fixture.documents, target_size), embeddings, config=config
    )
    calibration = calibrate_fixture_threshold(retriever, fixture) if calibrate else None
    metrics = evaluate_held_out(
        retriever,
        fixture,
        threshold=calibration.threshold if calibration is not None else None,
        clock=clock,
    )
    return calibration, metrics
