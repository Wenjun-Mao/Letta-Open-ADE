"""Validate M2's fixed test inputs; this neither runs nor scores a candidate."""

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
    """Validate the fixed, unexecuted M2 candidate-test specification."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "shared_budget",
        "subjects",
        "conversations",
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
    subjects = payload["subjects"]
    if not isinstance(subjects, list) or len(subjects) < 2:
        raise ValueError("M2 comparison fixture requires at least two subjects")
    subject_ids: set[str] = set()
    for subject in subjects:
        if not isinstance(subject, dict) or set(subject) != {"id", "label"}:
            raise ValueError("M2 comparison subjects have an invalid shape")
        subject_id = subject["id"]
        if (
            not isinstance(subject_id, str)
            or not subject_id
            or subject_id in subject_ids
            or not isinstance(subject["label"], str)
            or not subject["label"].strip()
        ):
            raise ValueError("M2 comparison subject IDs and labels must be unique")
        subject_ids.add(subject_id)
    conversations = payload["conversations"]
    if not isinstance(conversations, list) or not conversations:
        raise ValueError("M2 comparison fixture requires conversations")
    conversation_ids: set[str] = set()
    turn_ids: set[str] = set()
    turn_conversation_ids: dict[str, str] = {}
    for conversation in conversations:
        if not isinstance(conversation, dict) or set(conversation) != {
            "id",
            "subject_id",
            "turns",
        }:
            raise ValueError("M2 comparison conversations have an invalid shape")
        conversation_id = conversation["id"]
        if (
            not isinstance(conversation_id, str)
            or not conversation_id
            or conversation_id in conversation_ids
            or conversation["subject_id"] not in subject_ids
            or not isinstance(conversation["turns"], list)
            or not conversation["turns"]
        ):
            raise ValueError(
                "M2 comparison conversations require known subjects and turns"
            )
        conversation_ids.add(conversation_id)
        for turn in conversation["turns"]:
            if not isinstance(turn, dict) or set(turn) != {
                "id",
                "role",
                "timestamp",
                "content",
            }:
                raise ValueError("M2 comparison turns have an invalid shape")
            turn_id = turn["id"]
            if (
                not isinstance(turn_id, str)
                or not turn_id
                or turn_id in turn_ids
                or turn["role"] not in {"user", "assistant"}
                or not isinstance(turn["timestamp"], str)
                or not turn["timestamp"].endswith("Z")
                or not isinstance(turn["content"], str)
                or not turn["content"].strip()
            ):
                raise ValueError(
                    "M2 comparison turns require unique, timestamped content"
                )
            turn_ids.add(turn_id)
            turn_conversation_ids[turn_id] = conversation_id
    cases = payload["cases"]
    if not isinstance(cases, list):
        raise ValueError("M2 comparison fixture cases must be a list")
    ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {
            "id",
            "m1_fixture_refs",
            "conversation_ids",
            "memory_shape",
            "expected_semantic_state",
            "negative_probes",
            "ade_contract",
            "hindsight_trial",
            "live_requirement",
        }:
            raise ValueError("M2 comparison case has an invalid shape")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise ValueError("M2 comparison case IDs must be unique nonempty strings")
        ids.add(case_id)
        if (
            not isinstance(case["m1_fixture_refs"], list)
            or not case["m1_fixture_refs"]
            or any(
                not isinstance(reference, str) or not (ROOT / reference).is_file()
                for reference in case["m1_fixture_refs"]
            )
            or not isinstance(case["conversation_ids"], list)
            or not case["conversation_ids"]
            or any(
                conversation_id not in conversation_ids
                for conversation_id in case["conversation_ids"]
            )
        ):
            raise ValueError(
                "M2 comparison cases require existing M1 references and inputs"
            )
        states = case["expected_semantic_state"]
        if not isinstance(states, list) or not states:
            raise ValueError("M2 comparison cases require expected semantic state")
        for state in states:
            if not isinstance(state, dict) or set(state) != {
                "subject_id",
                "kind",
                "key",
                "value",
                "state",
                "source_turn_ids",
            }:
                raise ValueError("M2 comparison expected state has an invalid shape")
            if (
                state["subject_id"] not in subject_ids
                or any(
                    not isinstance(state[name], str) or not state[name].strip()
                    for name in ("kind", "key", "value", "state")
                )
                or not isinstance(state["source_turn_ids"], list)
                or not state["source_turn_ids"]
                or any(turn_id not in turn_ids for turn_id in state["source_turn_ids"])
                or any(
                    turn_conversation_ids[turn_id] not in case["conversation_ids"]
                    for turn_id in state["source_turn_ids"]
                )
            ):
                raise ValueError("M2 comparison expected state requires known sources")
        probes = case["negative_probes"]
        if not isinstance(probes, list) or not probes:
            raise ValueError("M2 comparison cases require negative probes")
        for probe in probes:
            if not isinstance(probe, dict) or set(probe) != {
                "conversation_id",
                "turn_id",
                "must_not_recall",
                "must_not_claim",
            }:
                raise ValueError("M2 comparison negative probes have an invalid shape")
            if (
                probe["conversation_id"] not in conversation_ids
                or probe["conversation_id"] not in case["conversation_ids"]
                or probe["turn_id"] not in turn_ids
                or turn_conversation_ids[probe["turn_id"]] != probe["conversation_id"]
                or any(
                    not isinstance(probe[name], list)
                    or not probe[name]
                    or any(
                        not isinstance(value, str) or not value.strip()
                        for value in probe[name]
                    )
                    for name in ("must_not_recall", "must_not_claim")
                )
            ):
                raise ValueError(
                    "M2 comparison negative probes require concrete claims"
                )
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
