"""Runtime parity, exact fixed intervention and existing reviewer contracts."""

import copy
import json

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from workflows.evals.character_memory_dev.story_continuity.evidence_selection.behavioral.contracts import (
    ARMS,
    DIRECTORY,
    PINNED,
    estimate,
    load_prepared,
    review_request,
)
from .story_behavioral_comparison import construct, validate_observation
from .story_offline_capacity import measure


def test_reproduce_exact_freeze():
    preparation, packets = construct()
    assert preparation == json.loads((DIRECTORY / "preparation.json").read_bytes())
    assert packets == json.loads((DIRECTORY / "requests.json").read_bytes())
    assert load_prepared()["packets"] == packets
    old = {p["key"]: p for p in measure()[1]}
    for packet in packets:
        if packet["arm"] == "repaired-four":
            continue
        before = copy.deepcopy(packet["generation"])
        for field in ("thinking", "reasoning_effort"):
            before.pop(field)
        assert before == old[f"D04/{packet['arm']}"]["generation"]
        assert packet["reviewer"] == old[f"D04/{packet['arm']}"]["reviewer"]


def test_fixed_arms_source_integrity_h_and_isolation():
    preparation, packets = construct()
    histories = []
    for packet, (arm, ids), size in zip(
        packets, ARMS, preparation["sizes"], strict=True
    ):
        assert packet["arm"] == arm and packet["included"] == list(ids)
        review = json.loads(packet["reviewer"]["messages"][1]["content"])
        full = json.loads(packet["reviewer_full_reserve"]["messages"][1]["content"])
        generation = packet["generation"]
        history = json.loads(
            generation["messages"][0]["content"].split(
                "Historical evidence (read-only):\n"
            )[1]
        )
        assert history == review["history"] == full["history"]
        histories.append(history)
        assert full == {**review, "candidate_visible_reply": "x" * 16384}
        assert (
            review["targets"]
            == review["related_identities"]
            == review["eligible_support"]
            == review["context"]
            == []
        )
        assert len(history) == len(ids)
        assert size["generation_input_estimate"] == estimate(generation) <= 11213
        assert (
            size["reviewer_full_reserve_estimate"]
            == estimate(packet["reviewer_full_reserve"])
            <= 11469
        )
        for request in (generation, packet["reviewer"]):
            assert all(request[k] == v for k, v in PINNED.items())
            assert request["max_tokens"] == 4096 and "tools" not in request
        for source, expected in zip(history, ids, strict=True):
            assert source["run_id"].endswith(expected)
        actual = review_request(packet, 'An actual visible answer, with quotes: "好".')
        substituted = json.loads(actual["messages"][1]["content"])
        assert substituted == {
            **review,
            "candidate_visible_reply": 'An actual visible answer, with quotes: "好".',
        }
    assert histories[0][:3] == histories[1][:3]
    assert histories[0][3] != histories[1][3]
    packets[0]["generation"]["messages"][0]["content"] = "mutation"
    assert packets[1]["generation"]["messages"][0]["content"] != "mutation"


@pytest.mark.parametrize("arm", [a for a, _ in ARMS])
def test_actual_reply_capacity_and_no_mutation(arm):
    packet = next(p for p in construct()[1] if p["arm"] == arm)
    original = copy.deepcopy(packet)
    review_request(packet, "x" * 16384)
    with pytest.raises(ValueError, match="never truncate"):
        review_request(packet, "木" * 16384)
    assert packet == original


def test_runtime_schema_and_binding_without_shadow_semantics():
    assert (
        validate_observation("literal-four", "Unsure.", {"decisions": []}).operations
        == ()
    )
    with pytest.raises(RuntimeValidationError) as malformed:
        validate_observation(
            "literal-four", "Unsure.", {"decisions": [], "extra": True}
        )
    assert malformed.value.detail_code == "natural_review_schema"
    decision = {
        "decisions": [
            {
                "kind": "conflict",
                "current_quote": "木制风铃",
                "candidate_reply_quote": "茶馆里",
                "history": {"handle": "H2", "quote": "不是茶馆里"},
            }
        ]
    }
    with pytest.raises(RuntimeValidationError) as conflict:
        validate_observation("literal-four", "是在茶馆里。", decision)
    assert conflict.value.detail_code == "natural_memory_reply_conflict"
    decision["decisions"][0]["history"]["handle"] = "H99"
    with pytest.raises(RuntimeValidationError) as binding:
        validate_observation("literal-four", "是在茶馆里。", decision)
    assert binding.value.detail_code == "natural_review_binding"


def test_explicit_pinning_matches_router_default_application():
    from model_router.app import _apply_sampling_defaults, _normalize_adapter_payload
    from model_router.catalog import RoutedModel
    from model_router.settings import RouterSourceConfig

    source = RouterSourceConfig(
        id="deepseek",
        label="synthetic",
        base_url="https://api.deepseek.com",
        adapter="deepseek_openai",
    )
    route = RoutedModel(
        router_model_id="deepseek::deepseek-flash",
        source_id="deepseek",
        source_label="synthetic",
        source_kind="openai-compatible",
        source_adapter="deepseek_openai",
        source_base_url="https://api.deepseek.com",
        module_visibility=("agent_studio",),
        provider_model_id="deepseek-flash",
        model_type="llm",
        agent_studio_available=True,
        comment_lab_available=False,
        label_lab_available=False,
        structured_output_mode=None,
        thinking_default_enabled=True,
        reasoning_effort_default="high",
    )
    for packet in construct()[1]:
        pinned = packet["generation"]
        historical = {
            k: v for k, v in pinned.items() if k not in {"thinking", "reasoning_effort"}
        }
        assert (
            _apply_sampling_defaults(
                route, source, _normalize_adapter_payload(source, historical)
            )
            == pinned
        )
        assert (
            _apply_sampling_defaults(
                route, source, _normalize_adapter_payload(source, pinned)
            )
            == pinned
        )
