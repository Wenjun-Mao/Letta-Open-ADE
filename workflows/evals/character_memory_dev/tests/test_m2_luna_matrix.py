from __future__ import annotations

import json
from pathlib import Path

from workflows.evals.character_memory_dev.tasks import TASKS, build_prompt


ROOT = Path(__file__).resolve().parents[4]
MATRIX_PATH = ROOT / "workflows/evals/character_memory_dev/fixtures/m2/luna_matrix.json"


def test_m2_luna_matrix_is_bounded_and_uses_existing_task_contracts() -> None:
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))

    assert matrix["schema_version"] == 1
    assert matrix["maximum_generation_sessions"] == 14
    assert matrix["planned_generation_sessions"] == 14
    assert (
        matrix["planned_generation_sessions"] <= matrix["maximum_generation_sessions"]
    )
    assert matrix["lane"] == {
        "runtime": "luna-subscription",
        "model": "gpt-5.6-luna",
        "reasoning_effort": "medium",
        "service_tier": "default",
        "timeout_seconds": 180,
        "adapter_retries": 0,
        "fallbacks": 0,
    }
    assert matrix["preference_intent_contrast_rubric"] == {
        "same_supplied_context": "All four exploratory prompts receive the identical source-derived broad flower-tea statement.",
        "factual_recall": "A factual-recall answer must not attribute jasmine specificity to the user's remembered preference without source evidence.",
        "recommendation": "A recommendation may suggest jasmine or another subtype when phrased as advice; lexical subtype presence alone is not a false-memory claim.",
        "classification": "Review the reply's assertion and source attribution, preserve every output, and treat four samples as exploratory rather than a score.",
    }

    calls = matrix["calls"]
    assert [call["id"] for call in calls] == [
        "preference-correction-extraction",
        "concern-resolution-extraction",
        "photo-event-extraction",
        "preference-correction-dialogue",
        "forgetting-dialogue",
        "concern-resolution-dialogue",
        "photo-event-dialogue",
        "subject-isolation-dialogue",
        "relevance-dialogue",
        "repetition-dialogue",
        "preference-factual-broad-recall",
        "preference-factual-jasmine-attribution",
        "preference-recommendation-jasmine",
        "preference-recommendation-open",
    ]
    assert all(call["task"] in TASKS for call in calls)
    assert all(call["chronological_cutoff"].strip() for call in calls)
    assert all(call["data_lineage"].strip() for call in calls)
    assert all(call["independent_review_focus"].strip() for call in calls)


def test_m2_luna_dialogue_inputs_keep_review_answers_out_of_prompts() -> None:
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    expected_message_ids = {
        "preference-correction-extraction": [
            "preference-origin-u1",
            "preference-origin-a1",
            "preference-correction-u1",
        ],
        "concern-resolution-extraction": [
            "concern-origin-u1",
            "concern-origin-a1",
            "concern-follow-up-u1",
            "concern-resolution-u1",
        ],
        "photo-event-extraction": [
            "photo-promise-u1",
            "photo-promise-a1",
            "photo-event-u2",
        ],
        "preference-correction-dialogue": ["preference-recall-u1"],
        "forgetting-dialogue": ["forget-follow-up-u1"],
        "concern-resolution-dialogue": ["concern-after-resolution-u1"],
        "photo-event-dialogue": [
            "photo-promise-u1",
            "photo-promise-a1",
            "photo-event-u2",
        ],
        "subject-isolation-dialogue": ["lin-music-follow-up-u1"],
        "relevance-dialogue": ["relevance-stress-u1"],
        "repetition-dialogue": [
            "repetition-origin-u1",
            "repetition-callback-a1",
            "repetition-follow-up-u1",
        ],
        "preference-factual-broad-recall": ["preference-factual-broad-u1"],
        "preference-factual-jasmine-attribution": ["preference-factual-jasmine-u1"],
        "preference-recommendation-jasmine": ["preference-recommendation-jasmine-u1"],
        "preference-recommendation-open": ["preference-recommendation-open-u1"],
    }

    for call in matrix["calls"]:
        input_path = ROOT / call["input"]
        assert input_path.is_file()
        data = json.loads(input_path.read_text(encoding="utf-8"))
        build_prompt(call["task"], data)
        assert [message["id"] for message in data["messages"]] == expected_message_ids[
            call["id"]
        ]
        if call["task"] != "dialogue":
            continue
        assert "expectations" not in data
        if call["context_mode"] == "source-derived-supplied-context-not-retrieval":
            assert data["memories"]
            assert all(
                memory.startswith("[source-derived supplied context; not retrieval]")
                for memory in data["memories"]
            )
        else:
            assert call["context_mode"] in {
                "no-supplied-memory-oracle",
                "source-transcript-only",
            }
            assert "memories" not in data

    contrast_inputs = [
        ROOT / call["input"]
        for call in matrix["calls"]
        if call["id"].startswith("preference-")
        and call["id"]
        in {
            "preference-factual-broad-recall",
            "preference-factual-jasmine-attribution",
            "preference-recommendation-jasmine",
            "preference-recommendation-open",
        }
    ]
    assert len(contrast_inputs) == 4
    assert {
        tuple(json.loads(path.read_text(encoding="utf-8"))["memories"])
        for path in contrast_inputs
    } == {
        (
            "[source-derived supplied context; not retrieval] 用户当前饮品偏好为花茶。来源：preference-correction-u1。",
        )
    }
