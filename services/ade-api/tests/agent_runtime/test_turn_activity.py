from ade_api.features.agent_runtime.turn_activity import conversation_activity


def event(run_id, kind, payload, attempt=1):
    return {
        "run_id": run_id,
        "event_type": kind,
        "payload": payload,
        "attempt": attempt,
    }


def start(run_id, request_id, stage, operation="chat_completion", attempt=1):
    return event(
        run_id,
        "model.request.started",
        {
            "request_id": request_id,
            "stage": stage,
            "operation": operation,
        },
        attempt,
    )


def test_success_counts_dispatches_tools_and_admitted_sources() -> None:
    run = {"id": "run", "status": "succeeded", "attempt_count": 1}
    events = [
        start("run", "catalog", "catalog", "catalog"),
        start("run", "a", "conversation"),
        event("run", "model.response.completed", {"request_id": "a"}),
        start("run", "b", "reviewer"),
        event("run", "model.response.completed", {"request_id": "b"}),
        start("run", "c", "history_ranking", "embeddings"),
        start("run", "c", "history_ranking", "embeddings"),
        event("run", "model.response.completed", {"request_id": "c"}),
        event(
            "run", "tool.call.requested", {"call_id": "tool", "name": "search_memory"}
        ),
        event(
            "run",
            "tool.call.completed",
            {"call_id": "tool", "name": "search_memory", "succeeded": True},
        ),
        event(
            "run",
            "context.built",
            {"section_tokens": {"recent_messages": 0}, "retrieved_fact_ids": ["fact"]},
        ),
        event(
            "run",
            "run.completed",
            {
                "dispatch_counts": {
                    "complete": True,
                    "groups": [{"attempted": 1}, {"attempted": 1}, {"attempted": 1}],
                }
            },
        ),
    ]
    attempts = [
        {
            "run_id": "run",
            "attempt_number": 1,
            "status": "succeeded",
            "provider_outcome": {"admitted_history_run_ids": ["older"]},
        }
    ]
    summary = conversation_activity([run], events, attempts, {"older": "source-chat"})[
        0
    ]
    assert summary["provider"] == {
        "generation": 1,
        "reviewer": 1,
        "embedding": 1,
        "other": 0,
    }
    assert summary["provider_complete"] is True
    assert summary["tools"] == [
        {"name": "search_memory", "succeeded": 1, "failed": 0, "unresolved": 0}
    ]
    assert summary["context"] == {
        "current_chat": False,
        "profile_fact_ids": ["fact"],
        "history_run_ids": ["older"],
        "history_sources": [{"run_id": "older", "conversation_id": "source-chat"}],
    }


def test_failed_retry_is_lower_bound_and_missing_is_unavailable() -> None:
    runs = [
        {"id": "retry", "status": "failed", "attempt_count": 2},
        {"id": "old", "status": "failed", "attempt_count": 1},
    ]
    events = [
        start("retry", "a", "conversation", attempt=1),
        event("retry", "model.request.failed", {"request_id": "a"}, attempt=1),
        start("retry", "b", "conversation", attempt=2),
        event(
            "retry",
            "tool.call.requested",
            {"call_id": "t", "name": "search_memory"},
            attempt=2,
        ),
        event("retry", "run.failed", {}, attempt=2),
        event("old", "run.failed", {}, attempt=1),
    ]
    summaries = {
        item["run_id"]: item for item in conversation_activity(runs, events, [])
    }
    assert summaries["retry"]["provider"]["generation"] == 2
    assert summaries["retry"]["provider_complete"] is False
    assert summaries["retry"]["tools"] == [
        {"name": "search_memory", "succeeded": 0, "failed": 0, "unresolved": 1}
    ]
    assert summaries["old"]["provider_observed"] is False
    assert summaries["old"]["provider_complete"] is False


def test_complete_zero_requires_terminal_receipt() -> None:
    run = {"id": "zero", "status": "succeeded", "attempt_count": 1}
    terminal = event(
        "zero", "run.completed", {"dispatch_counts": {"complete": True, "groups": []}}
    )
    attempt = {
        "run_id": "zero",
        "attempt_number": 1,
        "status": "succeeded",
        "provider_outcome": {},
    }
    summary = conversation_activity([run], [terminal], [attempt])[0]
    assert summary["provider_observed"] is True
    assert summary["provider_complete"] is True
    assert summary["provider"]["generation"] == 0
