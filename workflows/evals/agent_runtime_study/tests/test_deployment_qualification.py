from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from workflows.evals.agent_runtime_study.deployment_qualification import (
    Deployment,
    DeploymentFingerprint,
    DeploymentLifecycle,
    DeploymentRole,
    QualificationRound,
    ReleaseTarget,
    apply_qualification,
    assess_qualification,
    current_policy_hashes,
    load_deployments,
    policy_bundle_hash,
    release_gate,
    replace_fingerprint,
    validate_policy_hashes,
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


def test_fingerprint_is_immutable_and_does_not_include_route_aliases() -> None:
    deployment = _deployment(DeploymentRole.CONVERSATION)
    other_alias = replace(
        deployment,
        route_aliases=("router::renamed-convenience-alias",),
    )
    changed_prompt = replace(
        deployment.fingerprint,
        prompt_policy_sha256="a" * 64,
    )
    changed_endpoint = replace(
        deployment.fingerprint,
        endpoint_identity="test-provider-chat:8001",
    )

    assert deployment.fingerprint.sha256 == other_alias.fingerprint.sha256
    assert deployment.fingerprint.sha256 != changed_prompt.sha256
    assert deployment.fingerprint.sha256 != changed_endpoint.sha256
    assert deployment.fingerprint.sampling_settings == (
        ("temperature", 0.2),
        ("top_p", 0.95),
    )


def test_qualification_requires_three_consecutive_passes_for_each_role() -> None:
    deployment = _deployment(DeploymentRole.CONVERSATION, DeploymentRole.REVIEWER)
    rounds = (
        _round(
            deployment,
            role=DeploymentRole.CONVERSATION,
            sequence=1,
            passed=True,
        ),
        _round(
            deployment,
            role=DeploymentRole.CONVERSATION,
            sequence=2,
            passed=True,
        ),
        _round(
            deployment,
            role=DeploymentRole.CONVERSATION,
            sequence=3,
            passed=True,
        ),
        _round(
            deployment,
            role=DeploymentRole.REVIEWER,
            sequence=4,
            passed=True,
        ),
        _round(
            deployment,
            role=DeploymentRole.REVIEWER,
            sequence=5,
            passed=False,
        ),
        _round(
            deployment,
            role=DeploymentRole.REVIEWER,
            sequence=6,
            passed=True,
        ),
        _round(
            deployment,
            role=DeploymentRole.REVIEWER,
            sequence=7,
            passed=True,
        ),
    )

    assessment = assess_qualification(deployment, rounds)

    assert assessment.qualified is False
    assert [
        (item.role, item.consecutive_passing_rounds) for item in assessment.role_results
    ] == [
        (DeploymentRole.CONVERSATION, 3),
        (DeploymentRole.REVIEWER, 2),
    ]
    assert (
        apply_qualification(deployment, rounds).lifecycle
        is DeploymentLifecycle.CANDIDATE
    )

    qualified_rounds = (
        *rounds,
        _round(
            deployment,
            role=DeploymentRole.REVIEWER,
            sequence=8,
            passed=True,
        ),
    )
    qualified = apply_qualification(deployment, qualified_rounds)

    assert assess_qualification(deployment, qualified_rounds).qualified is True
    assert qualified.lifecycle is DeploymentLifecycle.QUALIFIED


def test_role_specific_rounds_can_share_a_global_round_number() -> None:
    deployment = _deployment(DeploymentRole.CONVERSATION, DeploymentRole.REVIEWER)
    rounds = tuple(
        _round(deployment, role=role, sequence=sequence, passed=True)
        for sequence in range(1, 4)
        for role in (DeploymentRole.CONVERSATION, DeploymentRole.REVIEWER)
    )

    assessment = assess_qualification(deployment, rounds)

    assert assessment.qualified is True


def test_changed_fingerprint_invalidates_prior_rounds_deterministically() -> None:
    deployment = _deployment(DeploymentRole.RETRIEVER)
    rounds = tuple(
        _round(
            deployment,
            role=DeploymentRole.RETRIEVER,
            sequence=sequence,
            passed=True,
        )
        for sequence in range(1, 4)
    )
    qualified = apply_qualification(deployment, rounds)
    new_fingerprint = replace(
        qualified.fingerprint,
        context_settings={"total_tokens": 16384, "output_tokens": 1024},
    )

    invalidated = replace_fingerprint(qualified, new_fingerprint)
    assessment = assess_qualification(invalidated, rounds)

    assert qualified.lifecycle is DeploymentLifecycle.QUALIFIED
    assert invalidated.lifecycle is DeploymentLifecycle.DISCOVERED
    assert assessment.stale_round_count == 3
    assert assessment.qualified is False
    assert assessment.role_results[0].consecutive_passing_rounds == 0


def test_fingerprint_change_does_not_reactivate_a_deprecated_deployment() -> None:
    deployment = replace(
        _deployment(DeploymentRole.CONVERSATION),
        lifecycle=DeploymentLifecycle.DEPRECATED,
    )

    updated = replace_fingerprint(
        deployment,
        replace(deployment.fingerprint, endpoint_identity="replacement-host:8000"),
    )

    assert updated.lifecycle is DeploymentLifecycle.DEPRECATED
    assert updated.fingerprint.endpoint_identity == "replacement-host:8000"


def test_production_release_is_strict_but_study_override_is_explicit() -> None:
    deployment = _deployment(DeploymentRole.CONVERSATION)
    rounds = tuple(
        _round(
            deployment,
            role=DeploymentRole.CONVERSATION,
            sequence=sequence,
            passed=True,
        )
        for sequence in range(1, 4)
    )
    qualified = apply_qualification(deployment, rounds)
    assessment = assess_qualification(qualified, rounds)

    production = release_gate(
        qualified,
        target=ReleaseTarget.PRODUCTION,
        assessment=assessment,
    )
    unqualified = replace(qualified, lifecycle=DeploymentLifecycle.CANDIDATE)
    blocked_study = release_gate(unqualified, target=ReleaseTarget.STUDY)
    allowed_study = release_gate(
        unqualified,
        target=ReleaseTarget.STUDY,
        allow_study_development_override=True,
    )
    blocked_production = release_gate(
        unqualified,
        target=ReleaseTarget.PRODUCTION,
        allow_study_development_override=True,
    )

    assert production.allowed is True
    assert blocked_study.allowed is False
    assert allowed_study.allowed is True
    assert allowed_study.override_used is True
    assert blocked_production.allowed is False


def test_complete_rounds_cannot_release_a_fingerprint_missing_provenance() -> None:
    deployment = replace(
        _deployment(DeploymentRole.RETRIEVER),
        fingerprint=_fingerprint(
            artifact_revision=None,
            runtime_version=None,
            runtime_image_digest=None,
        ),
    )
    rounds = tuple(
        _round(
            deployment,
            role=DeploymentRole.RETRIEVER,
            sequence=sequence,
            passed=True,
        )
        for sequence in range(1, 4)
    )
    candidate = apply_qualification(deployment, rounds)
    assessment = assess_qualification(candidate, rounds)

    decision = release_gate(
        candidate,
        target=ReleaseTarget.PRODUCTION,
        assessment=assessment,
    )

    assert assessment.qualified is True
    assert candidate.lifecycle is DeploymentLifecycle.CANDIDATE
    assert decision.allowed is False


def test_checked_in_registry_tracks_actual_identity_separately_from_aliases() -> None:
    registry_path = Path(__file__).resolve().parents[1] / "deployments.toml"

    deployments = load_deployments(registry_path)

    assert [item.deployment_id for item in deployments] == [
        "dgx-qwen3_6-chat",
        "dgx-qwen3-embedding-0_6b",
        "llama-server-qwen3_5-27b",
    ]
    llama = deployments[2]
    retriever = deployments[1]
    assert llama.route_aliases == ("local_llama_server::gemma4",)
    assert llama.fingerprint.served_model == "Qwen3.5-27B-UD-Q4_K_XL.gguf"
    assert retriever.roles == (DeploymentRole.RETRIEVER,)
    assert retriever.fingerprint.context_settings == (
        ("endpoint_port", 8001),
        ("request_timeout_seconds", 15),
    )
    assert all(item.lifecycle is DeploymentLifecycle.DISCOVERED for item in deployments)
    assert deployments[0].fingerprint.provenance_complete is True
    assert retriever.fingerprint.provenance_complete is True
    assert llama.fingerprint.provenance_complete is False
    validate_policy_hashes(deployments, registry_path.parent)


def test_policy_bundle_hash_binds_paths_and_contents(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("same", encoding="utf-8")
    (tmp_path / "b.txt").write_text("same", encoding="utf-8")

    original = policy_bundle_hash(tmp_path, ("a.txt",))
    renamed = policy_bundle_hash(tmp_path, ("b.txt",))
    (tmp_path / "a.txt").write_text("changed", encoding="utf-8")

    assert original != renamed
    assert original != policy_bundle_hash(tmp_path, ("a.txt",))
    assert set(current_policy_hashes(Path(__file__).resolve().parents[1])) == {
        "prompt_policy_sha256",
        "tool_policy_sha256",
        "schema_policy_sha256",
        "retrieval_policy_sha256",
    }
