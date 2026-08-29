from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from agent_runtime_eval_contracts import (
    Deployment,
    DeploymentFingerprint,
    DeploymentLifecycle,
    DeploymentRole,
    EventObservation,
    FactObservation,
    QualificationRound,
    ReleaseTarget,
    ToolObservation,
    TurnObservation,
    apply_qualification,
    assess_qualification,
    load_cases,
    policy_bundle_hash,
    release_gate,
    replace_fingerprint,
    score_case,
    select_cases,
    semantic_retrieval_cases_path,
    study_cases_path,
)


def _fingerprint(**changes: object) -> DeploymentFingerprint:
    values: dict[str, object] = {
        "provider": "test-provider",
        "endpoint_role": "openai-compatible-chat",
        "endpoint_identity": "test-provider-chat:8000",
        "served_model": "actual-served-model",
        "artifact_reference": "org/model",
        "artifact_revision": "a" * 40,
        "runtime_implementation": "vllm",
        "runtime_version": "0.12.0",
        "runtime_image_digest": "b" * 64,
        "prompt_policy_sha256": "c" * 64,
        "tool_policy_sha256": "d" * 64,
        "schema_policy_sha256": "e" * 64,
        "retrieval_policy_sha256": "f" * 64,
        "sampling_settings": {"temperature": 0.2, "top_p": 0.95},
        "context_settings": {"total_tokens": 8192, "output_tokens": 1024},
        "hardware_metadata": {"accelerator": "test-gpu", "count": 1},
    }
    values.update(changes)
    return DeploymentFingerprint(**values)  # type: ignore[arg-type]


def _deployment(*roles: DeploymentRole) -> Deployment:
    return Deployment(
        deployment_id="deployment-a",
        route_aliases=("router::friendly-alias",),
        roles=roles,
        fingerprint=_fingerprint(),
    )


def _round(
    deployment: Deployment,
    *,
    role: DeploymentRole,
    sequence: int,
    passed: bool,
    fingerprint_sha256: str | None = None,
) -> QualificationRound:
    return QualificationRound(
        deployment_id=deployment.deployment_id,
        role=role,
        fingerprint_sha256=fingerprint_sha256 or deployment.fingerprint.sha256,
        sequence=sequence,
        scenario_key=f"{role.value}-{sequence}",
        passed=passed,
    )


def test_package_data_exposes_the_canonical_fixture_suites() -> None:
    cases = load_cases(study_cases_path())

    assert study_cases_path().is_file()
    assert semantic_retrieval_cases_path().is_file()
    assert {case.key for case in cases} == {
        "chat_memory_baseline",
        "correction_chain",
        "explicit_forgetting",
        "cross_agent_subject_sharing",
        "cross_subject_isolation",
        "old_memory_deep_search",
        "long_history_compaction",
        "false_memory_prevention",
        "weather_tool_selection",
        "weather_tool_failure",
    }
    assert select_cases(cases, ("correction_chain",))[0].key == "correction_chain"


def test_score_case_uses_normalized_observations_without_runtime_dependencies() -> None:
    case = select_cases(load_cases(study_cases_path()), ("weather_tool_failure",))[0]

    score = score_case(
        case=case,
        facts_by_subject={
            "primary": (FactObservation(key="location", value="Toronto"),),
        },
        results_by_conversation={
            "primary": (
                TurnObservation(
                    status="succeeded",
                    assistant_text="I could not retrieve the weather right now.",
                    candidate_assistant_text="I could not retrieve the weather right now.",
                    events=(
                        EventObservation(type="model.request"),
                        EventObservation(type="model.response"),
                        EventObservation(type="memory.review.request"),
                    ),
                    tools=(ToolObservation(name="get_weather", succeeded=False),),
                    usage={"input_tokens": 11, "output_tokens": 7},
                    elapsed_seconds=0.1234567,
                ),
            ),
        },
    )

    assert score == {
        "case_key": "weather_tool_failure",
        "pass": True,
        "checks": [
            {
                "kind": "private_reasoning_not_exposed",
                "visible_markers": [],
                "pass": True,
            },
            {"kind": "required_tool", "tool_name": "get_weather", "pass": True},
            {"kind": "failed_tool_was_observed", "pass": True},
            {"kind": "all_runs_succeeded", "pass": True},
            {"kind": "normalized_trace_preserved", "pass": True},
        ],
        "failed_checks": [],
        "turn_count": 1,
        "used_tools": ["get_weather"],
        "latency_seconds": 0.123457,
        "input_tokens": 11,
        "output_tokens": 7,
        "role_scores": {
            "conversation": {
                "observed": True,
                "pass": True,
                "checks": [
                    {
                        "kind": "private_reasoning_not_exposed",
                        "visible_markers": [],
                        "pass": True,
                    },
                    {
                        "kind": "required_tool",
                        "tool_name": "get_weather",
                        "pass": True,
                    },
                    {"kind": "failed_tool_was_observed", "pass": True},
                    {"kind": "normalized_trace_preserved", "pass": True},
                ],
                "failed_checks": [],
            },
            "reviewer": {
                "observed": True,
                "pass": True,
                "checks": [
                    {"kind": "reviewed_turns_committed", "pass": True},
                ],
                "failed_checks": [],
            },
        },
    }


def test_fingerprint_and_qualification_sequence_are_deterministic() -> None:
    deployment = _deployment(DeploymentRole.CONVERSATION, DeploymentRole.REVIEWER)
    renamed = replace(
        deployment,
        route_aliases=("router::renamed-convenience-alias",),
    )
    changed = replace(
        deployment.fingerprint,
        endpoint_identity="test-provider-chat:8001",
    )
    rounds = tuple(
        _round(deployment, role=role, sequence=sequence, passed=True)
        for sequence in range(1, 4)
        for role in deployment.roles
    )

    assert deployment.fingerprint.sha256 == renamed.fingerprint.sha256
    assert deployment.fingerprint.sha256 != changed.sha256
    assert assess_qualification(deployment, rounds).qualified is True
    assert apply_qualification(deployment, rounds).lifecycle is DeploymentLifecycle.QUALIFIED

    reset = replace_fingerprint(
        apply_qualification(deployment, rounds),
        changed,
    )
    assert reset.lifecycle is DeploymentLifecycle.DISCOVERED
    assert assess_qualification(reset, rounds).stale_round_count == 6
    assert release_gate(
        reset,
        target=ReleaseTarget.PRODUCTION,
        assessment=assess_qualification(reset, rounds),
    ).allowed is False


def test_policy_bundle_hash_binds_relative_paths_and_contents(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("same", encoding="utf-8")
    (tmp_path / "b.txt").write_text("same", encoding="utf-8")

    original = policy_bundle_hash(tmp_path, ("a.txt",))
    renamed = policy_bundle_hash(tmp_path, ("b.txt",))
    (tmp_path / "a.txt").write_text("changed", encoding="utf-8")

    assert original != renamed
    assert original != policy_bundle_hash(tmp_path, ("a.txt",))
    with pytest.raises(ValueError, match="policy input does not exist"):
        policy_bundle_hash(tmp_path, ("missing.txt",))
