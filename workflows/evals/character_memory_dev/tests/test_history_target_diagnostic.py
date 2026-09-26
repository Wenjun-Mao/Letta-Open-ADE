"""Fail-closed source and terminal guards for the seven-turn diagnostic."""

from __future__ import annotations

import json

import pytest

from workflows.evals.character_memory_dev.history_target_diagnostic import (
    OLD_MANIFESTS,
    SCHEDULE,
    frozen_schedule,
    validate_catalog,
)
from workflows.evals.character_memory_dev.history_target_diagnostic_run import (
    admission_comparison,
    verified_turn_disposition,
)


def test_schedule_binds_seven_turns_to_immutable_h4_material() -> None:
    if not all(path.is_file() for path, _ in OLD_MANIFESTS):
        pytest.skip("ignored historical H4 manifests are unavailable")
    schedule, _, _ = frozen_schedule()
    assert sum(len(item["turns"]) for item in schedule["trajectories"]) == 7


def test_provider_identity_is_exact_and_rejects_drift() -> None:
    schedule = json.loads(SCHEDULE.read_text())
    chat = schedule["routes"]["conversation_and_reviewer"]
    embedding = schedule["routes"]["history_and_fact_embeddings"]
    catalog = {
        "items": [
            {
                "model_key": chat["model"],
                "deployment": {
                    "fingerprint": {
                        "sha256": chat["fingerprint"],
                        "context_settings": {
                            "total_tokens": 16384,
                            "max_output_tokens": 4096,
                            "reviewer_repair_count": 0,
                        },
                    }
                },
            },
            {
                "model_key": embedding["model"],
                "deployment": {
                    "fingerprint": {
                        "sha256": embedding["fingerprint"],
                        "artifact_reference": "Qwen/Qwen3-Embedding-0.6B",
                        "artifact_revision": embedding["artifact_revision"],
                        "sampling_settings": {"dimensions": embedding["dimensions"]},
                    }
                },
            },
        ]
    }
    assert validate_catalog(catalog, schedule)[0]["sha256"] == chat["fingerprint"]
    catalog["items"][1]["deployment"]["fingerprint"]["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="pinned diagnostic routes"):
        validate_catalog(catalog, schedule)


def test_verified_rejection_can_continue_an_independent_trajectory() -> None:
    turn = {
        "terminal_safety": "verified",
        "attempt_sha256": "a" * 64,
        "provider_captures": [{"status": "completed"}],
        "status": "rejected",
        "terminal_outcome": "confirmed_rejection",
        "run": {"status": "failed"},
        "observed_delta": {
            "generation_advance": 0,
            "revision_count": 0,
            "run_revisions": [],
            "other_revision_ids": [],
            "entity_additions": [],
        },
    }
    assert verified_turn_disposition(turn) == "verified_rejection"
    turn["observed_delta"]["revision_count"] = 1
    with pytest.raises(RuntimeError, match="inconsistent"):
        verified_turn_disposition(turn)


def test_admission_comparison_exposes_source_and_capacity_differences() -> None:
    prior = {
        "admitted_history": [{"messages": [{"role": "user", "content": "old"}]}],
        "history_selection": {"omitted_capacity_run_ids": ["prior-omitted"]},
    }
    current = {
        "admitted_history": [{"messages": [{"role": "user", "content": "new"}]}],
        "history_selection": {"omitted_capacity_run_ids": []},
    }
    comparison = admission_comparison(current, prior)
    assert comparison["same_admitted_source_text"] is False
    assert comparison["prior_omitted_capacity_count"] == 1
    assert comparison["current_omitted_capacity_count"] == 0
