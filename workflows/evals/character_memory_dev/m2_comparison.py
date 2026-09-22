"""Load the bounded M2 comparison contract; this is not a memory implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = ROOT / "workflows/evals/character_memory_dev/fixtures/m2/comparison.json"
REQUIRED_CASE_IDS = frozenset(
    {
        "preference-correction",
        "forgetting-no-resurface",
        "concern-lifecycle",
        "promise-shared-event",
        "subject-isolation-cross-conversation",
        "relevance-and-repetition",
        "unsupported-physical-experience",
    }
)


def load_comparison_spec(path: Path = FIXTURE_PATH) -> dict[str, Any]:
    """Validate the one compact M2 case contract before candidate-specific runs."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "shared_budget",
        "cases",
    }:
        raise ValueError("M2 comparison fixture has an invalid top-level shape")
    if payload["schema_version"] != 1:
        raise ValueError("M2 comparison fixture must use schema version 1")
    budget = payload["shared_budget"]
    if (
        not isinstance(budget, dict)
        or set(budget)
        != {
            "recent_transcript_tokens",
            "memory_to_dialogue_tokens",
            "source_inspection_tokens",
            "max_reply_tokens",
        }
        or any(not isinstance(value, int) or value <= 0 for value in budget.values())
    ):
        raise ValueError("M2 comparison fixture has an invalid shared budget")
    cases = payload["cases"]
    if not isinstance(cases, list):
        raise ValueError("M2 comparison fixture cases must be a list")
    ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {
            "id",
            "memory_shape",
            "assertions",
            "ade_contract",
            "hindsight_trial",
            "live_requirement",
        }:
            raise ValueError("M2 comparison case has an invalid shape")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise ValueError("M2 comparison case IDs must be unique nonempty strings")
        ids.add(case_id)
        if not isinstance(case["assertions"], list) or not case["assertions"]:
            raise ValueError("M2 comparison cases require assertions")
        if any(
            not isinstance(case[name], str) or not case[name].strip()
            for name in (
                "memory_shape",
                "ade_contract",
                "hindsight_trial",
                "live_requirement",
            )
        ):
            raise ValueError("M2 comparison cases require descriptive fields")
    if ids != REQUIRED_CASE_IDS:
        raise ValueError("M2 comparison fixture does not cover the required cases")
    return payload
