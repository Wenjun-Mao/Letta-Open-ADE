"""Private accounting leaves reader bounds and selection semantics explicit."""

from types import SimpleNamespace

from ade_api.features.agent_runtime.history_observations import history_observation


def test_omissions_include_reader_top_k_capacity_selector_and_purge():
    reasons = {"long": "content", "links": "annotation", "overflow": "reader_capacity"}
    reasons.update(dict.fromkeys(["a", "b", "c", "d", "e", "p", "s"], "eligible"))
    attempt = SimpleNamespace(
        probe=SimpleNamespace(arm="automatic_history"),
        status="purged",
        purged_run_ids={"p"},
        corpus={
            "inventory": {
                "status": "truncated",
                "universe": "scoped_completed_pairs",
                "limit": 128,
                "candidates": [
                    {"run_id": key, "reason": reason} for key, reason in reasons.items()
                ],
            },
            "omitted": {"capacity_at_least": 1, "content": 1, "annotation": 1},
        },
        admitted_exchanges=[{"run_id": key} for key in ("a", "b", "c")],
        ranked_exchanges=[{"run_id": key} for key in ("a", "b", "c", "d", "e")],
        omitted_capacity=["d"],
    )
    observed = history_observation(attempt)
    assert observed["status"] == "truncated"
    assert observed["reader_omitted"] == attempt.corpus["omitted"]
    assert {row["run_id"]: row["reason"] for row in observed["candidates"]} == {
        "long": "content",
        "links": "annotation",
        "overflow": "reader_capacity",
        "a": "admitted",
        "b": "admitted",
        "c": "admitted",
        "d": "packet_capacity",
        "e": "top_k",
        "p": "purged_before_exposure",
        "s": "selector_not_selected",
    }
    attempt.status = "unavailable"
    assert history_observation(attempt)["status"] == "unavailable"
    attempt.probe.arm = "empty_history"
    assert history_observation(attempt) == {
        "status": "not_read",
        "reason": "empty_history_arm",
        "candidates": [],
    }
