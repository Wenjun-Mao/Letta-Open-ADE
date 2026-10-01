"""Pre-outcome freeze checks: no runtime, scorer or selector imports."""

from __future__ import annotations

import copy
import shutil

import pytest

from workflows.evals.character_memory_dev.story_continuity.correction_dependencies.assessment import (
    assess_packet,
    reference_sets,
)
from workflows.evals.character_memory_dev.story_continuity.correction_dependencies.inputs import (
    DIRECTORY,
    expand_cases,
    load_inputs,
    load_judgments,
    validate_judgments,
)


def test_exact_six_case_ceiling_and_only_correction_text_changes():
    context, cases = load_inputs()
    assert [case["id"] for case in cases] == [f"D{i:02d}" for i in range(1, 7)]
    assert (
        context["local_suffix"]
        == context["saved_facts"]
        == context["related_entities"]
        == []
    )
    for first, second in zip(cases[::2], cases[1::2], strict=True):
        assert first["conversation_id"] == second["conversation_id"]
        assert first["query"] == second["query"]
        assert len(first["exchanges"]) == len(second["exchanges"]) == 8
        for index, (left, right) in enumerate(
            zip(first["exchanges"], second["exchanges"], strict=True)
        ):
            if index == 6:
                assert left["assistant"] != right["assistant"]
                assert {
                    key: value for key, value in left.items() if key != "assistant"
                } == {key: value for key, value in right.items() if key != "assistant"}
            else:
                assert left == right
        assert [
            (row["user_sequence"], row["assistant_sequence"])
            for row in first["exchanges"]
        ] == [(i * 2 - 1, i * 2) for i in range(1, 9)]


def test_labels_quote_all_episode_sources_and_do_not_leak_restored_value():
    _, cases = load_inputs()
    judgments = load_judgments()
    assert (
        judgments["annotation_kind"] == "nonblind_author_agent_before_new_case_scoring"
    )
    assert len(judgments["cases"]) == 6
    for case, judgment in zip(cases, judgments["cases"], strict=True):
        applicable = [
            quote
            for quote in judgment["quotes"]
            if quote.get("variant", judgment["variant"]) == judgment["variant"]
        ]
        assert {quote["source"] for quote in applicable} == {
            f"E{i:02d}" for i in range(1, 8)
        }
        assert all(quote["role"] == "assistant" for quote in applicable)
        value = judgment["restored_value"]
        assert value not in case["query"]
        assert all(value not in row["user"] for row in case["exchanges"])
        assert all(
            judgment["mistaken_value"] in case["exchanges"][i]["assistant"]
            for i in range(1, 5)
        )


@pytest.mark.parametrize(
    "name", ["freeze.json", "cases.json", "context.json", "judgments.json"]
)
def test_tampered_freeze_or_input_fails_closed(tmp_path, name):
    for source in DIRECTORY.glob("*.json"):
        shutil.copyfile(source, tmp_path / source.name)
    with (tmp_path / name).open("ab") as handle:
        handle.write(b" ")
    with pytest.raises(ValueError, match="Frozen correction-dependency input differs"):
        load_inputs(tmp_path)


def test_invalid_source_quote_or_label_reference_is_rejected():
    _, cases = load_inputs()
    data = load_judgments()
    broken = copy.deepcopy(data)
    broken["families"][0]["quotes"][0]["text"] += "wrong"
    with pytest.raises(ValueError, match="quote differs"):
        validate_judgments(broken, cases)
    broken = copy.deepcopy(data)
    broken["families"][0]["answer_routes"]["self_contained"] = [["E99"]]
    with pytest.raises(ValueError, match="bounded complete sources"):
        validate_judgments(broken, cases)


def test_named_answer_and_correction_dependency_are_distinct_before_outcomes():
    self_contained, dependent = load_judgments()["cases"][:2]
    assert assess_packet(self_contained, ["E07"])["named_answer_supported"]
    dangling = assess_packet(dependent, ["E07"])
    assert not dangling["named_answer_supported"]
    assert dangling["correction_admitted"]
    assert dangling["dependency_status"] == "missing"
    original = assess_packet(dependent, ["E01"])
    assert original["named_answer_supported"]
    assert original["dependency_status"] == "correction_absent"
    assert not original["correction_explanation_supported"]
    resolved = assess_packet(dependent, ["E01", "E07"])
    assert resolved["named_answer_supported"]
    assert resolved["dependency_status"] == "resolved"
    assert resolved["correction_explanation_supported"]


def test_every_labeled_reference_is_bounded_and_supports_its_declared_use():
    count = 0
    for judgment in load_judgments()["cases"]:
        for sources, uses in reference_sets(judgment).items():
            count += 1
            assert 1 <= len(sources) <= 4
            assessment = assess_packet(judgment, list(sources))
            for field in uses:
                key = {
                    "answer_routes": "named_answer_supported",
                    "correction_explanation": "correction_explanation_supported",
                    "correction_intent": "correction_intent_visible",
                    "mistaken_retelling": "mistaken_retelling_visible",
                    "optional_detail": "optional_detail_supported",
                }[field]
                assert assessment[key]
    assert count == 45


def test_saved_context_cannot_be_used_as_an_answer_leak():
    context, _ = load_inputs()
    context["saved_facts"] = [{"value": "answer"}]
    with pytest.raises(ValueError, match="empty saved/local context"):
        expand_cases(context, {"contract": context["contract"], "families": []})
