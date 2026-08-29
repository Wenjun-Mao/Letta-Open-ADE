from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from agent_runtime_eval_contracts import (
    Deployment,
    DeploymentFingerprint,
    DeploymentLifecycle,
    DeploymentRole,
    QualificationAssessment,
    QualificationRound,
    ReleaseTarget,
    apply_qualification,
    assess_qualification,
    release_gate,
)
from model_catalog_contracts.deployment_manifest import load_deployment_manifest

from .artifacts import json_value
from .config import StudyConfig
from .semantic_retrieval import (
    EmbeddingClientConfig,
    EmbeddingProvider,
    OpenAICompatibleEmbeddingsClient,
    RetrievalConfig,
    evaluate_fixture,
    load_retrieval_fixture,
)


class StudyEvidenceError(RuntimeError):
    pass


def run_semantic_retrieval_evaluation(
    config: StudyConfig,
    *,
    embeddings: EmbeddingProvider | None = None,
    clock: Callable[[], float] | None = None,
) -> dict[str, Any]:
    fixture = load_retrieval_fixture(config.retrieval_fixture_path)
    provider = embeddings or OpenAICompatibleEmbeddingsClient(
        EmbeddingClientConfig(
            base_url=config.embeddings_base_url,
            model=config.embeddings_model,
            dimensions=config.embedding_dimensions,
            timeout_seconds=config.embedding_timeout_seconds,
            api_key=config.embeddings_api_key or None,
            max_retries=0,
        )
    )
    evaluation_kwargs: dict[str, Any] = {}
    if clock is not None:
        evaluation_kwargs["clock"] = clock
    calibration, metrics = evaluate_fixture(
        fixture,
        provider,
        config=RetrievalConfig(
            strategy=config.retrieval_strategy,
            limit=3,
            query_instruction=config.retrieval_query_instruction,
        ),
        **evaluation_kwargs,
    )
    checks = {
        "calibration_precision": (
            calibration is not None and calibration.precision >= 0.95
        ),
        "calibration_recall": (calibration is not None and calibration.recall >= 0.95),
        "cross_lingual_recall_at_3": metrics.cross_lingual_recall_at_3 == 1.0,
        "overall_recall": metrics.overall_recall >= 0.95,
        "hard_negative_false_positive_rate": (
            metrics.hard_negative_false_positive_rate <= 0.05
        ),
        "p95_latency_ms": metrics.p95_latency_ms < 250.0,
        "subject_isolation": all(
            not row.ranked_document_ids
            for row in metrics.rows
            if row.case_id.startswith("subject_isolation")
        ),
    }
    return {
        "embedding_endpoint": config.embeddings_base_url,
        "embedding_model": config.embeddings_model,
        "embedding_dimensions": config.embedding_dimensions,
        "strategy": config.retrieval_strategy.value,
        "query_instruction": config.retrieval_query_instruction,
        "fixture_path": str(config.retrieval_fixture_path),
        "corpus_size": fixture.corpus_size,
        "calibration": json_value(calibration),
        "metrics": json_value(metrics),
        "acceptance": {
            "pass": all(checks.values()),
            "checks": checks,
            "thresholds": {
                "calibration_precision_minimum": 0.95,
                "calibration_recall_minimum": 0.95,
                "cross_lingual_recall_at_3": 1.0,
                "overall_recall_minimum": 0.95,
                "hard_negative_false_positive_rate_maximum": 0.05,
                "p95_latency_ms_maximum": 250.0,
            },
        },
    }


def load_prior_qualification_rounds(
    output_dir: Path,
) -> tuple[QualificationRound, ...]:
    rounds: list[QualificationRound] = []
    if not output_dir.is_dir():
        return ()
    for path in sorted(output_dir.glob("*/qualification.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StudyEvidenceError(f"Invalid qualification artifact: {path}") from exc
        raw_rounds = payload.get("current_rounds", [])
        if not isinstance(raw_rounds, list):
            raise StudyEvidenceError(
                f"qualification current_rounds must be a list: {path}"
            )
        for raw in raw_rounds:
            if not isinstance(raw, dict):
                raise StudyEvidenceError(
                    f"qualification round must be an object: {path}"
                )
            rounds.append(
                QualificationRound(
                    deployment_id=str(raw.get("deployment_id") or ""),
                    role=DeploymentRole(str(raw.get("role") or "")),
                    fingerprint_sha256=str(raw.get("fingerprint_sha256") or ""),
                    sequence=int(raw.get("sequence") or 0),
                    scenario_key=str(raw.get("scenario_key") or ""),
                    passed=raw.get("passed"),
                )
            )
    return tuple(rounds)


def build_qualification_evidence(
    *,
    run_id: str,
    registry_path: Path,
    output_dir: Path,
    models: Sequence[str],
    reviewer_model_key: str,
    rows: Sequence[dict[str, Any]],
    retrieval_evidence: dict[str, Any],
    required_case_keys: Sequence[str],
    qualification_adapter: str,
    allow_unqualified_study_models: bool,
    deployments: Sequence[Deployment] | None = None,
) -> dict[str, Any]:
    registry = tuple(deployments or deployments_from_manifest(registry_path))
    alias_map: dict[str, Deployment] = {}
    for deployment in registry:
        for alias in deployment.route_aliases:
            if alias in alias_map:
                raise StudyEvidenceError(f"Route alias is ambiguous: {alias}")
            alias_map[alias] = deployment
    required_cases = frozenset(
        str(key).strip() for key in required_case_keys if str(key).strip()
    )
    if not required_cases:
        raise StudyEvidenceError("Qualification requires at least one canonical case")
    qualification_rows = [
        row for row in rows if row.get("adapter") in {None, qualification_adapter}
    ]
    selected_roles: dict[tuple[str, DeploymentRole], bool] = {}
    assessed_deployment_ids: set[str] = set()
    role_coverage: list[dict[str, Any]] = []
    for model in models:
        deployment = _deployment_for_alias(alias_map, model)
        assessed_deployment_ids.add(deployment.deployment_id)
        if DeploymentRole.CONVERSATION not in deployment.roles:
            raise StudyEvidenceError(f"{model} is not registered for conversation")
        model_rows = [
            row for row in qualification_rows if row.get("model_key") == model
        ]
        observed_model_rows = [
            row
            for row in model_rows
            if _row_role_score(row, DeploymentRole.CONVERSATION)["observed"]
        ]
        observed_cases = {str(row.get("case_key") or "") for row in observed_model_rows}
        coverage_complete = required_cases <= observed_cases
        role_coverage.append(
            _coverage_payload(
                deployment.deployment_id,
                DeploymentRole.CONVERSATION,
                qualification_adapter,
                required_cases,
                observed_cases,
            )
        )
        if coverage_complete:
            selected_roles[(deployment.deployment_id, DeploymentRole.CONVERSATION)] = (
                all(
                    _row_role_score(row, DeploymentRole.CONVERSATION)["pass"] is True
                    for row in observed_model_rows
                    if row.get("case_key") in required_cases
                )
            )

    reviewer = _deployment_for_alias(alias_map, reviewer_model_key)
    assessed_deployment_ids.add(reviewer.deployment_id)
    if DeploymentRole.REVIEWER not in reviewer.roles:
        raise StudyEvidenceError(
            f"{reviewer_model_key} is not registered for memory review"
        )
    observed_reviewer_rows = [
        row
        for row in qualification_rows
        if _row_role_score(row, DeploymentRole.REVIEWER)["observed"]
    ]
    reviewer_cases = {str(row.get("case_key") or "") for row in observed_reviewer_rows}
    reviewer_coverage_complete = required_cases <= reviewer_cases
    role_coverage.append(
        _coverage_payload(
            reviewer.deployment_id,
            DeploymentRole.REVIEWER,
            qualification_adapter,
            required_cases,
            reviewer_cases,
        )
    )
    if reviewer_coverage_complete:
        selected_roles[(reviewer.deployment_id, DeploymentRole.REVIEWER)] = all(
            _row_role_score(row, DeploymentRole.REVIEWER)["pass"] is True
            for row in observed_reviewer_rows
            if row.get("case_key") in required_cases
        )

    retrievers = [
        deployment
        for deployment in registry
        if DeploymentRole.RETRIEVER in deployment.roles
    ]
    if len(retrievers) != 1:
        raise StudyEvidenceError("Study registry must select exactly one retriever")
    assessed_deployment_ids.add(retrievers[0].deployment_id)
    selected_roles[(retrievers[0].deployment_id, DeploymentRole.RETRIEVER)] = bool(
        (retrieval_evidence.get("acceptance") or {}).get("pass")
    )

    history = load_prior_qualification_rounds(output_dir)
    by_id = {deployment.deployment_id: deployment for deployment in registry}
    current_rounds: list[QualificationRound] = []
    for (deployment_id, role), passed in sorted(
        selected_roles.items(), key=lambda item: (item[0][0], item[0][1].value)
    ):
        deployment = by_id[deployment_id]
        digest = deployment.fingerprint.sha256
        prior_sequences = [
            round_.sequence
            for round_ in history
            if round_.deployment_id == deployment_id
            and round_.role is role
            and round_.fingerprint_sha256 == digest
        ]
        current_rounds.append(
            QualificationRound(
                deployment_id=deployment_id,
                role=role,
                fingerprint_sha256=digest,
                sequence=max(prior_sequences, default=0) + 1,
                scenario_key=f"{run_id}:{role.value}",
                passed=passed,
            )
        )

    all_rounds = (*history, *current_rounds)
    assessments: list[dict[str, Any]] = []
    study_decisions: list[dict[str, Any]] = []
    all_qualified = True
    for deployment_id in sorted(assessed_deployment_ids):
        deployment = by_id[deployment_id]
        promoted = apply_qualification(deployment, all_rounds)
        assessment = assess_qualification(promoted, all_rounds)
        decision = release_gate(
            promoted,
            target=ReleaseTarget.STUDY,
            assessment=assessment,
            allow_study_development_override=allow_unqualified_study_models,
        )
        assessments.append(
            {
                "deployment": json_value(promoted),
                "assessment": _assessment_payload(assessment),
            }
        )
        all_qualified = all_qualified and assessment.qualified
        study_decisions.append(
            {
                "deployment_id": deployment_id,
                "decision": json_value(decision),
            }
        )
    return {
        "registry_path": str(registry_path),
        "reviewer_model_key": reviewer_model_key,
        "historical_round_count": len(history),
        "current_rounds": json_value(tuple(current_rounds)),
        "qualification_adapter": qualification_adapter,
        "role_coverage": role_coverage,
        "assessments": assessments,
        "study_release_decisions": study_decisions,
        "all_qualified": all_qualified,
        "study_gate_pass": all(item["decision"]["allowed"] for item in study_decisions),
        "study_override_enabled": allow_unqualified_study_models,
    }


def deployments_from_manifest(path: Path) -> tuple[Deployment, ...]:
    """Project the canonical catalog manifest into generic qualification records."""

    manifest = load_deployment_manifest(path)
    if not manifest.deployments:
        raise StudyEvidenceError(f"Deployment manifest contains no deployments: {path}")
    return tuple(
        Deployment(
            deployment_id=entry.deployment_id,
            route_aliases=entry.route_aliases,
            roles=tuple(DeploymentRole(role) for role in entry.roles),
            lifecycle=DeploymentLifecycle(entry.lifecycle),
            fingerprint=DeploymentFingerprint(**entry.fingerprint.as_dict()),
        )
        for entry in manifest.deployments
    )


def _coverage_payload(
    deployment_id: str,
    role: DeploymentRole,
    adapter: str,
    required_cases: frozenset[str],
    observed_cases: set[str],
) -> dict[str, Any]:
    return {
        "deployment_id": deployment_id,
        "role": role.value,
        "adapter": adapter,
        "required_case_keys": sorted(required_cases),
        "observed_case_keys": sorted(observed_cases),
        "missing_case_keys": sorted(required_cases - observed_cases),
        "complete": required_cases <= observed_cases,
    }


def _deployment_for_alias(alias_map: dict[str, Deployment], alias: str) -> Deployment:
    try:
        return alias_map[alias]
    except KeyError as exc:
        raise StudyEvidenceError(
            f"No deployment fingerprint for route alias: {alias}"
        ) from exc


def _row_role_score(row: dict[str, Any], role: DeploymentRole) -> dict[str, object]:
    role_scores = row.get("role_scores")
    if not isinstance(role_scores, dict):
        raise StudyEvidenceError("Qualification row is missing role_scores")
    score = role_scores.get(role.value)
    if not isinstance(score, dict):
        raise StudyEvidenceError(
            f"Qualification row is missing the {role.value} role score"
        )
    observed = score.get("observed")
    passed = score.get("pass")
    if not isinstance(observed, bool):
        raise StudyEvidenceError(f"{role.value} role observed must be a boolean")
    if observed and not isinstance(passed, bool):
        raise StudyEvidenceError(
            f"Observed {role.value} role pass result must be a boolean"
        )
    if not observed and passed is not None:
        raise StudyEvidenceError(
            f"Unobserved {role.value} role pass result must be null"
        )
    return score


def _assessment_payload(assessment: QualificationAssessment) -> dict[str, Any]:
    return {
        "deployment_id": assessment.deployment_id,
        "fingerprint_sha256": assessment.fingerprint_sha256,
        "qualified": assessment.qualified,
        "stale_round_count": assessment.stale_round_count,
        "role_results": [
            {
                "role": result.role.value,
                "observed_rounds": result.observed_rounds,
                "consecutive_passing_rounds": result.consecutive_passing_rounds,
                "qualified": result.qualified,
            }
            for result in assessment.role_results
        ],
    }
