from ade_api.features.agent_runtime.request_counts import dispatch_counts


def _event(kind: str, request_id: str, **extra):
    return {
        "event_type": kind,
        "payload": {
            "request_id": request_id,
            "operation": "embeddings",
            "model_key": "qwen",
            "stage": "memory_embeddings",
            **extra,
        },
    }


def test_copied_events_deduplicate_by_local_id_and_failures_count() -> None:
    start = _event("model.request.started", "local-1")
    completed = _event("model.response.completed", "local-1")
    failed_start = _event("model.request.started", "local-2")
    failed = _event("model.request.failed", "local-2")
    summary = dispatch_counts(
        [start, completed, start, completed, failed_start, failed]
    )
    assert summary == {
        "complete": True,
        "groups": [
            {
                "operation": "embeddings",
                "model": "qwen",
                "stage": "memory_embeddings",
                "attempted": 2,
                "completed": 1,
                "failed": 1,
                "unresolved": 0,
            }
        ],
    }


def test_missing_start_is_incomplete_and_known_start_can_be_unresolved() -> None:
    summary = dispatch_counts(
        [
            _event("model.request.started", "known"),
            _event("model.response.completed", "lost-start"),
        ]
    )
    assert summary["complete"] is False
    assert summary["groups"][0]["unresolved"] == 1


def test_failed_observation_marks_even_empty_retained_trace_incomplete() -> None:
    assert dispatch_counts([], observation_incomplete=True) == {
        "complete": False,
        "groups": [],
    }
