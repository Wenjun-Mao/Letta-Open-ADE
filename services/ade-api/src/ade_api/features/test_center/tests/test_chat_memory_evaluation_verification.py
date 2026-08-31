from __future__ import annotations

from ade_api.features.test_center.chat_memory_evaluation_verification import (
    recompute_deterministic_score,
)


def test_recomputes_memory_fact_and_disclosure_signals_from_raw_evidence() -> None:
    score = recompute_deterministic_score(
        assistant_texts=["Rocky is lovely.", "我是AI，但我记住了。"],
        initial_human_memory="",
        final_human_memory="The user's dog is Rocky.",
        expected_facts=[
            {"key": "dog_name", "label": "Dog name", "aliases": ["Rocky"]},
            {"key": "dog_breed", "label": "Dog breed", "aliases": ["Husky"]},
        ],
        forbidden_reply_substrings=["我是AI"],
    )

    assert score["pass"] is False
    assert score["human_memory_changed"] is True
    assert score["forbidden_hit_count"] == 1
    assert score["missing_expected_facts"] == ["dog_breed"]
    assert score["expected_fact_scores"][0]["matched_aliases"] == ["Rocky"]


def test_recomputed_pass_requires_change_all_facts_and_no_disclosure() -> None:
    score = recompute_deterministic_score(
        assistant_texts=["Rocky sounds wonderful."],
        initial_human_memory="",
        final_human_memory="The user's dog Rocky is a Husky.",
        expected_facts=[
            {"key": "dog_name", "label": "Dog name", "aliases": ["Rocky"]},
            {"key": "dog_breed", "label": "Dog breed", "aliases": ["Husky"]},
        ],
        forbidden_reply_substrings=["我是AI"],
    )

    assert score["pass"] is True
