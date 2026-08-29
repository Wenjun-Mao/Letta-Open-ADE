from __future__ import annotations

import json
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

import pytest

from workflows.evals.agent_runtime_study.semantic_retrieval import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    DEFAULT_EMBEDDINGS_BASE_URL,
    DEFAULT_EMBEDDINGS_MODEL,
    EmbeddingClientConfig,
    EmbeddingRequestError,
    OpenAICompatibleEmbeddingsClient,
    RetrievalConfig,
    RetrievalDocument,
    RetrievalStrategy,
    SemanticRetriever,
    ThresholdObservation,
    calibrate_threshold,
    cosine_similarity,
    evaluate_fixture,
    expand_corpus,
    format_qwen3_query,
    load_retrieval_fixture,
)


FIXTURE_PATH = Path(
    "workflows/evals/agent_runtime_study/fixtures/semantic_retrieval_cases.json"
)


class KeywordEmbeddings:
    """A deterministic local fake; it never opens a network connection."""

    def __init__(self) -> None:
        self.inputs: list[tuple[str, ...]] = []

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        values = tuple(texts)
        self.inputs.append(values)
        return tuple(self._vector(text) for text in values)

    @staticmethod
    def _vector(text: str) -> tuple[float, ...]:
        normalized = text.casefold()
        if any(term in normalized for term in ("museum", "博物馆", "安大略")):
            return (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        if any(
            term in normalized
            for term in ("toronto", "city", "residence", "live", "多伦多", "城市", "住")
        ):
            return (0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        if any(term in normalized for term in ("concert", "massey", "jazz")):
            return (0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        if any(term in normalized for term in ("rocky", "husky", "哈士奇", "狗")):
            return (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0)
        if any(
            term in normalized for term in ("language", "mandarin", "语言", "普通话")
        ):
            return (0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
        if any(term in normalized for term in ("shoe", "eu 38", "38码")):
            return (0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        if any(term in normalized for term in ("sister", "mei", "小美")):
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        if "blue-orchid" in normalized:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


class StepClock:
    def __init__(self, step: float = 0.001) -> None:
        self.value = 0.0
        self.step = step

    def __call__(self) -> float:
        current = self.value
        self.value += self.step
        return current


class _Response:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_openai_client_uses_dgx_defaults_and_one_request_without_retries() -> None:
    config = EmbeddingClientConfig(
        base_url="http://embedding-sidecar:8001/v1",
        model="test-model",
        dimensions=3,
        timeout_seconds=2.5,
        api_key="study-key",
    )
    calls: list[tuple[Any, float]] = []

    def opener(request: Any, *, timeout: float) -> _Response:
        calls.append((request, timeout))
        return _Response(
            json.dumps(
                {
                    "data": [
                        {"index": 1, "embedding": [0, 1, 0]},
                        {"index": 0, "embedding": [1, 0, 0]},
                    ]
                }
            ).encode()
        )

    client = OpenAICompatibleEmbeddingsClient(config, opener=opener)

    assert client.embed(("first", "second")) == ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    assert len(calls) == 1
    request, timeout = calls[0]
    assert request.full_url == "http://embedding-sidecar:8001/v1/embeddings"
    assert timeout == 2.5
    assert request.get_header("Authorization") == "Bearer study-key"
    assert json.loads(request.data) == {
        "model": "test-model",
        "input": ["first", "second"],
    }
    assert EmbeddingClientConfig().base_url == DEFAULT_EMBEDDINGS_BASE_URL
    assert EmbeddingClientConfig().model == DEFAULT_EMBEDDINGS_MODEL
    assert EmbeddingClientConfig().dimensions == DEFAULT_EMBEDDING_DIMENSIONS
    assert EmbeddingClientConfig().max_retries == 0


def test_openai_client_does_not_retry_a_transport_failure() -> None:
    calls = 0

    def opener(*args: Any, **kwargs: Any) -> _Response:
        nonlocal calls
        calls += 1
        raise OSError("sidecar unavailable")

    client = OpenAICompatibleEmbeddingsClient(
        EmbeddingClientConfig(dimensions=3), opener=opener
    )

    with pytest.raises(EmbeddingRequestError) as captured:
        client.embed(("one request",))
    assert captured.value.retryable is True
    assert calls == 1
    with pytest.raises(ValueError, match="zero retries"):
        EmbeddingClientConfig(max_retries=1)


@pytest.mark.parametrize(
    ("status_code", "retryable"),
    ((400, False), (429, True), (503, True)),
)
def test_openai_client_classifies_http_failures_for_ade_owned_retries(
    status_code: int, retryable: bool
) -> None:
    def opener(*args: Any, **kwargs: Any) -> _Response:
        raise HTTPError(
            "http://embedding-sidecar:8001/v1/embeddings",
            status_code,
            "failed",
            hdrs=None,
            fp=BytesIO(b'{"error":"failed"}'),
        )

    client = OpenAICompatibleEmbeddingsClient(
        EmbeddingClientConfig(dimensions=3), opener=opener
    )

    with pytest.raises(EmbeddingRequestError) as captured:
        client.embed(("one request",))
    assert captured.value.retryable is retryable


def test_qwen_formatting_and_cosine_similarity_are_explicit_and_stable() -> None:
    assert format_qwen3_query("where is it?", "retrieve memories") == (
        "Instruct: retrieve memories\nQuery: where is it?"
    )
    assert format_qwen3_query("where is it?", "") == "where is it?"
    assert format_qwen3_query("where is it?", None) == "where is it?"
    assert cosine_similarity((1, 0), (2, 0)) == 1.0
    assert cosine_similarity((0, 0), (2, 0)) == 0.0
    with pytest.raises(ValueError, match="equal dimensions"):
        cosine_similarity((1,), (1, 0))


def test_retrieval_strategies_rank_deterministically_and_preserve_subject_isolation() -> (
    None
):
    documents = (
        RetrievalDocument(
            id="b_museum",
            subject_id="alice",
            text="Alice likes the Royal Ontario Museum.",
            aliases=("ROM", "安大略皇家博物馆"),
        ),
        RetrievalDocument(
            id="a_museum_tie",
            subject_id="alice",
            text="Alice's museum memory is the Royal Ontario Museum.",
            aliases=("ROM",),
        ),
        RetrievalDocument(
            id="bob_secret",
            subject_id="bob",
            text="Bob's archive identifier is blue-orchid-17.",
            aliases=("blue-orchid-17",),
        ),
    )
    retriever = SemanticRetriever(documents, KeywordEmbeddings())

    alias_result = retriever.search(
        "alice", "ROM", strategy=RetrievalStrategy.ALIAS, limit=2
    )
    assert [result.document.id for result in alias_result] == [
        "a_museum_tie",
        "b_museum",
    ]
    assert all(result.alias_score == 1.0 for result in alias_result)

    semantic_result = retriever.search(
        "alice", "Which museum is preferred?", strategy=RetrievalStrategy.SEMANTIC
    )
    assert [result.document.id for result in semantic_result] == [
        "a_museum_tie",
        "b_museum",
    ]
    assert all(result.semantic_score == 1.0 for result in semantic_result)

    isolated = retriever.search(
        "alice",
        "What is the blue-orchid-17 archive identifier?",
        minimum_score=0.6,
    )
    assert isolated == ()

    all_candidates = retriever.search(
        "alice",
        "museum",
        strategy=RetrievalStrategy.LEXICAL,
        limit=None,
    )
    assert len(all_candidates) == 2


def test_fixture_evaluation_calibrates_then_scores_held_out_thousand_item_corpus() -> (
    None
):
    fixture = load_retrieval_fixture(FIXTURE_PATH)
    embeddings = KeywordEmbeddings()

    calibration, metrics = evaluate_fixture(
        fixture,
        embeddings,
        config=RetrievalConfig(query_instruction="retrieve matching memories"),
        clock=StepClock(),
    )

    assert len(expand_corpus(fixture.documents, fixture.corpus_size)) == 1000
    assert calibration is not None
    assert calibration.observation_count == 6
    assert calibration.precision == 1.0
    assert calibration.recall == 1.0
    assert calibration.false_positive_rate == 0.0
    assert metrics.evaluated_case_count == 12
    assert metrics.cross_lingual_recall_at_3 == 1.0
    assert metrics.overall_recall == 1.0
    assert metrics.hard_negative_false_positive_rate == 0.0
    assert metrics.p95_latency_ms == pytest.approx(1.0)
    assert [row.case_id for row in metrics.rows] == [
        "cross_lingual_museum",
        "held_out_concert",
        "cross_lingual_city",
        "cross_lingual_pet_name",
        "cross_lingual_pet_breed",
        "cross_lingual_language",
        "held_out_shoe_size",
        "held_out_sister",
        "hard_negative_food",
        "hard_negative_phone",
        "subject_isolation_secret",
        "subject_isolation_pet",
    ]
    assert any(
        text.startswith("Instruct: retrieve matching memories\nQuery:")
        for batch in embeddings.inputs
        for text in batch
    )


def test_threshold_calibration_prefers_a_deterministic_high_score_boundary() -> None:
    calibration = calibrate_threshold(
        (
            ThresholdObservation(score=0.91, is_relevant=True),
            ThresholdObservation(score=0.82, is_relevant=True),
            ThresholdObservation(score=0.41, is_relevant=False),
            ThresholdObservation(score=0.15, is_relevant=False),
        )
    )

    assert calibration.threshold == pytest.approx(0.615)
    assert calibration.balanced_accuracy == 1.0
    assert calibration.precision == 1.0
