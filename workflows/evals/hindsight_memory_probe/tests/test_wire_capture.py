import base64
import json
import struct

import httpx
import pytest

from workflows.evals.hindsight_memory_probe.receipts import CaptureFailure
from workflows.evals.hindsight_memory_probe.wire_capture import safe_response


def embedding_response(vectors, *, status=200, usage=None):
    return httpx.Response(
        status,
        json={"data": vectors, "usage": usage or {}},
        request=httpx.Request("POST", "https://router.test/v1/embeddings"),
    )


@pytest.mark.parametrize(
    ("inputs", "expected_count"),
    [("one", 1), (["one", "two"], 2), ([11, 12, 13], 1), ([[11, 12], [13]], 2)],
)
def test_embedding_input_count_respects_text_and_token_shapes(inputs, expected_count):
    vectors = [
        {"index": index, "embedding": [0.0, 1.0]} for index in range(expected_count)
    ]
    projection = safe_response(
        embedding_response(vectors), {"input": inputs}, elapsed=0.01
    )
    assert projection["input_count"] == expected_count
    assert projection["embedding_dimensions"] == [2] * expected_count


def test_base64_float32_projection_and_explicit_dimension():
    encoded = base64.b64encode(struct.pack("<2f", 1.0, -2.0)).decode()
    projection = safe_response(
        embedding_response([{"index": 0, "embedding": encoded}]),
        {"input": "one", "dimensions": 2},
        elapsed=0.01,
    )
    assert projection["embedding_dimensions"] == [2]
    assert "embedding" not in projection
    assert encoded not in str(projection)


def test_out_of_order_response_indices_are_accepted_when_complete():
    projection = safe_response(
        embedding_response(
            [
                {"index": 1, "embedding": [0.0, 1.0]},
                {"index": 0, "embedding": [2.0, 3.0]},
            ]
        ),
        {"input": ["one", "two"]},
        elapsed=0.01,
    )
    assert projection["embedding_dimensions"] == [2, 2]


@pytest.mark.parametrize("dimensions", [3, -1])
def test_explicit_dimension_mismatch_fails_projection(dimensions):
    with pytest.raises(CaptureFailure):
        safe_response(
            embedding_response([{"index": 0, "embedding": [0.0, 1.0]}]),
            {"input": "one", "dimensions": dimensions},
            elapsed=0.01,
        )


@pytest.mark.parametrize(
    "encoded",
    [
        "",
        base64.b64encode(b"abc").decode(),
        base64.b64encode(struct.pack("<f", float("nan"))).decode(),
        base64.b64encode(struct.pack("<f", float("inf"))).decode(),
    ],
)
def test_invalid_base64_float32_is_rejected(encoded):
    with pytest.raises(CaptureFailure):
        safe_response(
            embedding_response([{"index": 0, "embedding": encoded}]),
            {"input": "one"},
            elapsed=0.01,
        )


@pytest.mark.parametrize("index", [True, "0", -1, 1, None])
def test_invalid_response_index_is_rejected(index):
    with pytest.raises(CaptureFailure):
        safe_response(
            embedding_response([{"index": index, "embedding": [0.0]}]),
            {"input": "one"},
            elapsed=0.01,
        )


def test_non_json_successful_embedding_response_is_rejected():
    response = httpx.Response(
        200,
        text="private response text",
        request=httpx.Request("POST", "https://router.test/v1/embeddings"),
    )
    with pytest.raises(CaptureFailure):
        safe_response(response, {"input": "one"}, elapsed=0.01)


def test_http_error_body_is_not_parsed_or_projected():
    response = embedding_response(
        [{"index": 0, "embedding": "private-vector"}],
        status=503,
        usage={"total_tokens": 10},
    )
    projection = safe_response(response, {"input": "one"}, elapsed=0.01)
    assert projection == {"status": 503, "latency_seconds": 0.01}
    assert "private-vector" not in str(projection)


def test_usage_projection_keeps_only_finite_nonnegative_numbers():
    response = httpx.Response(
        200,
        content=json.dumps(
            {
                "usage": {
                    "prompt_tokens": 2,
                    "completion_tokens": -1,
                    "total_tokens": float("inf"),
                    "prompt_cache_hit_tokens": True,
                    "private": "discard",
                }
            },
            allow_nan=True,
        ).encode(),
        headers={"Content-Type": "application/json"},
        request=httpx.Request("POST", "https://router.test/v1/chat/completions"),
    )
    assert safe_response(response, {}, 0.01)["usage"] == {"prompt_tokens": 2}
