"""Frozen offline lexical comparison, not native retrieval or semantic acceptance."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from ade_api.features.agent_runtime.context import BuiltContext
from ade_api.features.agent_runtime.history_admission import (
    MAX_ADMITTED_WINDOWS,
    admit_history,
)
from ade_api.features.agent_runtime.history_ranking import (
    TOP_K,
    document_text,
    literal_score,
    query_text,
    rank_windows,
)
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    natural_review_request,
)
from workflows.evals.character_memory_dev.story_continuity.retrieval_diversity.selector import (
    LIMIT,
    Window,
    select_diverse,
)


DIRECTORY = (
    Path(__file__).resolve().parents[4]
    / "workflows/evals/character_memory_dev/story_continuity/retrieval_diversity"
)
FIXTURE_SHA256 = "37bdb1405a2373174915f43335b775a7b2f85a0d43666ee6b9e4b11b027e8e5b"


def _cases():
    raw = (DIRECTORY / "cases.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    fixture = json.loads(raw)
    assert fixture["status"] == "synthetic_agent_labeled_before_observation"
    assert len({case["id"] for case in fixture["cases"]}) == len(fixture["cases"])
    for case in fixture["cases"]:
        ids = {row[0] for row in case["exchanges"]}
        assert len(ids) == len(case["exchanges"]) > LIMIT
        assert set(case["irrelevant_ids"]) <= ids
        for group in case["evidence_groups"]:
            assert group and set(group) <= ids
            assert not set(group) & set(case["irrelevant_ids"])
    return fixture["cases"]


def _inputs(case):
    windows = [
        Window(
            source_id,
            f"2026-09-{index:02d}T12:00:00+00:00",
            document_text({"user": user, "assistant": assistant}),
        )
        for index, (source_id, user, assistant) in enumerate(case["exchanges"], 1)
    ]
    query = query_text(case["query"], [])
    scores = {window.id: literal_score(query, window.text) for window in windows}
    return windows, scores


def _assess(case, selected):
    groups = case["evidence_groups"]
    return {
        "selected": selected,
        "covered_groups": sum(bool(set(group) & set(selected)) for group in groups),
        "required_groups": len(groups),
        "all_evidence": all(set(group) & set(selected) for group in groups)
        if groups
        else None,
        "irrelevant_admitted": len(set(selected) & set(case["irrelevant_ids"])),
    }


def _assert_packets(case, selected):
    current = {"id": "current", "role": "user", "content": case["query"], "sequence": 1}
    exchanges = {}
    for index, (source_id, user, assistant) in enumerate(case["exchanges"], 1):
        messages = []
        for sequence, (role, text) in enumerate(
            [("user", user), ("assistant", assistant)], 1
        ):
            messages.append(
                {
                    "id": f"{source_id}-{role}",
                    "role": role,
                    "content": text,
                    "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "created_at": f"2026-09-{index:02d}T12:00:00+00:00",
                    "sequence": sequence,
                }
            )
        exchanges[source_id] = {
            "run_id": source_id,
            "conversation_id": f"chat-{source_id}",
            "definition_version_id": "prior-version",
            "archived": True,
            "messages": messages,
            "annotations": {
                "links": [],
                "facts": [],
                "revisions": [],
                "predecessor_edges": [],
            },
        }
    chosen = [exchanges[source_id] for source_id in selected]
    base = BuiltContext(
        messages=[
            {"role": "system", "content": "Stay in character."},
            {"role": "user", "content": case["query"]},
        ],
        section_tokens={},
        omitted_message_ids=[],
        retrieved_fact_ids=[],
        estimated_input_tokens=0,
    )
    admission = admit_history(
        base=base,
        ranked_exchanges=chosen,
        current_user=current,
        source_messages=[current],
        facts=[],
        entities=[],
        generation_model_key="deepseek::deepseek-flash",
        generation_adapter="deepseek_openai",
        generation_tools={},
        generation_input_limit=100_000,
        generation_max_output_tokens=512,
        reviewer_model_key="deepseek::deepseek-flash",
        reviewer_adapter="deepseek_openai",
        reviewer_input_limit=100_000,
        reviewer_max_output_tokens=4096,
    )
    assert not admission.omitted_capacity
    assert list(admission.exchanges) == chosen
    review = natural_review_request(
        model_key="deepseek::deepseek-flash",
        provider_adapter="deepseek_openai",
        current_user_message=current,
        source_messages=[current],
        facts=[],
        entities=[],
        candidate_reply="Synthetic packet check only.",
        history_exchanges=chosen,
        history_capable=True,
    )
    history = json.loads(review["messages"][1]["content"])["history"]
    assert (
        json.dumps(history, ensure_ascii=False, separators=(",", ":"))
        in admission.context.messages[0]["content"]
    )


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["id"])
def test_frozen_lexical_comparison_and_packet_integrity(case):
    assert LIMIT == TOP_K == MAX_ADMITTED_WINDOWS == 4
    windows, scores = _inputs(case)
    original = copy.deepcopy((windows, scores))
    baseline = [
        item["id"]
        for item in rank_windows(
            [
                {"id": window.id, "assistant_at": window.assistant_at}
                for window in windows
            ],
            scores,
        )
    ]
    candidate = select_diverse(windows, scores)
    observed = json.loads((DIRECTORY / "observed.json").read_text())
    assert {"baseline": baseline, "candidate": candidate} == observed["cases"][
        case["id"]
    ]
    assert len(candidate) == len(set(candidate)) == LIMIT
    assert set(candidate) <= set(scores)
    assert (windows, scores) == original
    assert select_diverse(list(reversed(windows)), scores) == candidate
    for selected in (baseline, candidate):
        _assert_packets(case, selected)
    print(
        json.dumps(
            {
                "case": case["id"],
                "baseline": _assess(case, baseline),
                "candidate": _assess(case, candidate),
            },
            ensure_ascii=False,
        )
    )


def test_scorer_labels_and_opaque_ids_do_not_drive_selection():
    for case in _cases():
        windows, scores = _inputs(case)
        original = select_diverse(windows, scores)
        changed = copy.deepcopy(case)
        changed.update(
            id="different",
            evidence_groups=[["DO_NOT_USE"]],
            irrelevant_ids=["DO_NOT_USE"],
            rationale="DO_NOT_USE",
        )
        other_windows, other_scores = _inputs(changed)
        assert (other_windows, other_scores) == (windows, scores)
        assert select_diverse(other_windows, other_scores) == original
        renames = {
            window.id: f"opaque-{len(windows) - index}"
            for index, window in enumerate(windows)
        }
        renamed = [Window(renames[w.id], w.assistant_at, w.text) for w in windows]
        assert select_diverse(renamed, {renames[k]: v for k, v in scores.items()}) == [
            renames[k] for k in original
        ]


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_scores_fail_closed(score):
    windows = [Window("a", "2026-09-01T00:00:00+00:00", "Some content")]
    with pytest.raises(ValueError, match="finite relevance"):
        select_diverse(windows, {"a": score})


def test_ids_dates_and_empty_corpus():
    window = Window("a", "2026-09-01T00:00:00+00:00", "Some content")
    assert select_diverse([], {}) == []
    assert select_diverse([window], {"a": 0}) == ["a"]
    with pytest.raises(ValueError, match="unique source"):
        select_diverse([window, window], {"a": 0.5})
    with pytest.raises(ValueError, match="unique source"):
        select_diverse([window], {"wrong": 0.5})
    with pytest.raises(ValueError, match="timezone-aware"):
        select_diverse([Window("a", "2026-09-01", "Text")], {"a": 0.5})


def test_novelty_recovers_nonduplicate_without_origin_label():
    windows = [
        Window(str(i), f"2026-09-0{i}T00:00:00+00:00", text)
        for i, text in enumerate(["original detail", "same echo", "same echo"], 1)
    ]
    assert select_diverse(windows, {"1": 0.5, "2": 0.9, "3": 0.9}) == ["3", "1", "2"]


def test_equal_utility_uses_source_time_then_stable_id():
    windows = [
        Window("b", "2026-09-02T00:00:00+00:00", "identical text"),
        Window("c", "2026-09-01T00:00:00+00:00", "identical text"),
        Window("a", "2026-09-02T00:00:00+00:00", "identical text"),
    ]
    assert select_diverse(windows, {"a": 0.5, "b": 0.5, "c": 0.5}) == ["a", "b", "c"]


def test_no_match_is_not_scored_as_evidence_success():
    case = next(case for case in _cases() if case["id"] == "unrelated_topic")
    assessment = _assess(case, ["a", "b", "c", "d"])
    assert assessment["all_evidence"] is None
    assert assessment["irrelevant_admitted"] == LIMIT


def test_observed_scorecard_and_source_binding():
    observed = json.loads((DIRECTORY / "observed.json").read_text())
    assert observed["status"] == "observed_lexical_mechanics_not_qualification"
    for field, filename in [
        ("fixture", "cases.json"),
        ("recipe", "README.md"),
        ("selector", "selector.py"),
    ]:
        assert (
            hashlib.sha256((DIRECTORY / filename).read_bytes()).hexdigest()
            == observed[f"{field}_sha256"]
        )
    cases = _cases()
    assert set(observed["cases"]) == {case["id"] for case in cases}
    summary = {"positive_cases": sum(bool(case["evidence_groups"]) for case in cases)}
    for arm in ("baseline", "candidate"):
        positive = [
            _assess(case, observed["cases"][case["id"]][arm])
            for case in cases
            if case["evidence_groups"]
        ]
        negative = [
            _assess(case, observed["cases"][case["id"]][arm])
            for case in cases
            if not case["evidence_groups"]
        ]
        summary[f"{arm}_complete_evidence"] = sum(
            item["all_evidence"] for item in positive
        )
        summary[f"{arm}_positive_irrelevant_admissions"] = sum(
            item["irrelevant_admitted"] for item in positive
        )
        summary[f"{arm}_no_match_irrelevant_admissions"] = sum(
            item["irrelevant_admitted"] for item in negative
        )
    assert summary == observed["summary"]


def test_improved_cases_do_not_distinguish_novelty_from_duplicate_handling():
    observed = json.loads((DIRECTORY / "observed.json").read_text())
    improved = []
    for case in _cases():
        arms = observed["cases"][case["id"]]
        if not (
            _assess(case, arms["candidate"])["all_evidence"]
            and _assess(case, arms["baseline"])["all_evidence"] is False
        ):
            continue
        improved.append(case["id"])
        classes = {}
        for source_id, user, assistant in case["exchanges"]:
            classes.setdefault((user, assistant), set()).add(source_id)
        assert len(case["exchanges"]) == 7
        assert len(classes) == LIMIT
        # Every representative of at least one full text class satisfies each
        # required group. This proves a fixture confound, not a deduplication rule.
        for group in case["evidence_groups"]:
            assert any(ids <= set(group) for ids in classes.values())
        selected = set(arms["candidate"])
        assert all(ids & selected for ids in classes.values())
    assert improved == [
        "wrong_repeated_echoes",
        "supported_error_correction",
        "unsupported_rewrite",
        "compatible_new_detail",
        "anaphoric_correction",
    ]


def test_positive_irrelevant_breakdown_separates_other_episode_and_chatter():
    observed = json.loads((DIRECTORY / "observed.json").read_text())
    totals = {}
    for arm in ("baseline", "candidate"):
        other_episode = unrelated = 0
        for case in _cases():
            if not case["evidence_groups"]:
                continue
            selected = set(observed["cases"][case["id"]][arm])
            irrelevant = selected & set(case["irrelevant_ids"])
            # Scorer-only classification of this frozen fixture. In the similar
            # episode case, g is food chatter, not another cat encounter.
            contrast = (
                {"b", "d", "e", "f"}
                if case["id"] == "distinct_similar_episodes"
                else set()
            )
            other_episode += len(irrelevant & contrast)
            unrelated += len(irrelevant - contrast)
        totals[arm] = (other_episode, unrelated)
        assert (
            other_episode + unrelated
            == observed["summary"][f"{arm}_positive_irrelevant_admissions"]
        )
    assert totals == {"baseline": (3, 0), "candidate": (1, 7)}
