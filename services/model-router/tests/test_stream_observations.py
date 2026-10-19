"""Visible SSE observations must preserve chunks without retaining private reasoning."""

import json

from model_router.request_observations import RequestObservation
from model_router.stream_observations import StreamObservation


def test_stream_observation_preserves_visible_events_across_utf8_chunk_boundaries(
    tmp_path,
):
    observer = StreamObservation(RequestObservation(tmp_path, "stream-a"))
    event = {
        "id": "provider-stream",
        "model": "actual-model",
        "choices": [
            {
                "index": 0,
                "delta": {"content": "乌龙", "reasoning_content": "private"},
                "finish_reason": None,
            }
        ],
    }
    raw = (
        "data: " + json.dumps(event, ensure_ascii=False) + "\n\ndata: [DONE]\n\n"
    ).encode()
    for byte in raw:
        observer.feed(bytes([byte]))
    assert observer.finish(200)
    result = json.loads((tmp_path / "stream-a.outcome.json").read_bytes())
    assert result["response_capture_complete"] is True
    assert result["visible_events"][0]["choices"][0]["delta"] == {"content": "乌龙"}
    assert "private" not in (tmp_path / "stream-a.outcome.json").read_text()


def test_cancelled_or_malformed_stream_cannot_be_called_complete(tmp_path):
    cancelled = StreamObservation(RequestObservation(tmp_path, "cancelled"))
    cancelled.feed(b'data: {"id":"provider"}\n\n')
    cancelled.finish(200, error_type="CancelledError")
    malformed = StreamObservation(RequestObservation(tmp_path, "malformed"))
    malformed.feed(b"data: invalid-json\n\ndata: [DONE]\n\n")
    malformed.finish(200)
    for name in ("cancelled", "malformed"):
        assert (
            json.loads((tmp_path / f"{name}.outcome.json").read_bytes())[
                "response_capture_complete"
            ]
            is False
        )


def test_done_marker_does_not_hide_incomplete_utf8_tail(tmp_path):
    observer = StreamObservation(RequestObservation(tmp_path, "partial-utf8"))
    observer.feed(b"data: [DONE]\n\n\xe4\xb8")
    assert observer.finish(200)
    assert (
        json.loads((tmp_path / "partial-utf8.outcome.json").read_bytes())[
            "response_capture_complete"
        ]
        is False
    )
