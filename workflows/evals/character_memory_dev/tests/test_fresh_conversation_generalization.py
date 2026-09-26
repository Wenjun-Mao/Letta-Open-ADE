"""Guard the small frozen chronological fixture before any live dispatch."""

from __future__ import annotations

import json
from pathlib import Path

from ade_api.features.agent_runtime.fact_registry import fact_type_spec
from workflows.evals.character_memory_dev.natural_live_results import sha256_file


FIXTURES = Path(__file__).parents[1] / "fixtures/history_recall"


def test_fresh_fixture_is_finite_chronological_and_source_bound() -> None:
    fixture = json.loads(
        (FIXTURES / "fresh_conversation_generalization.json").read_text()
    )
    binding = json.loads((FIXTURES / "generation_contract_diagnostic.json").read_text())
    assert fixture["schema_version"] == 1
    assert fixture["status"] == "revised-offline-frozen-pending-director-review"
    assert fixture["generation_binding_sha256"] == sha256_file(
        FIXTURES / "generation_contract_diagnostic.json"
    )
    assert (fixture["prompt_key"], fixture["persona_key"]) == (
        binding["prompt_key"],
        binding["persona_key"],
    )
    assert fixture["policy"] == "natural-user-assertions-v4-b-history-probe"
    assert fixture["arm"] == "automatic_history"
    assert fixture["per_turn"] == binding["per_turn"]

    trajectories = fixture["trajectories"]
    assert [item["id"] for item in trajectories] == [
        "location_correction_cross_chat",
        "two_exhibits_ambiguous_then_clear",
        "archived_pottery_outcome",
        "unrelated_turn_and_subject_boundary",
    ]
    assert [len(item["turns"]) for item in trajectories] == [3, 4, 2, 3]
    assert sum(len(item["turns"]) for item in trajectories) == 12
    assert all(item["subject"] == "primary" for item in trajectories)
    assert trajectories[2]["archive_after"] == "source"
    assert trajectories[3]["turns"][2]["subject"] == "isolated"
    assert trajectories[1]["turns"][1]["user"] == "那个展我下周想再去一次。"
    assert "full actual preceding exchange" in " ".join(
        trajectories[1]["turns"][1]["must"]
    )
    assert any(
        "ambiguity challenge was not exercised" in rule
        for rule in fixture["execution_rules"]
    )
    assert all(
        turn["user"] and turn["chat"] and turn["must"] and turn["must_not"]
        for trajectory in trajectories
        for turn in trajectory["turns"]
    )
    assert all(
        not any(key in turn for key in ("assistant", "seed_fact", "preseed"))
        for trajectory in trajectories
        for turn in trajectory["turns"]
    )
    assert fact_type_spec("person.current_location").name == "person.current_location"
    assert "music" in fact_type_spec("person.preference").allowed_qualifiers
    assert "visit" not in fact_type_spec("person.preference").allowed_qualifiers
