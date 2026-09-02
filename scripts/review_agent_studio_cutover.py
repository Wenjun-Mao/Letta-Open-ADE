from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model_catalog_contracts.deployment_manifest import load_deployment_manifest

from ade_api.features.agent_runtime_v3.release_evidence import (
    REQUIRED_CONFORMANCE_TESTS,
    AgentStudioReleaseEvidenceError,
    canonical_sha256,
    file_sha256,
    validate_agent_studio_release_evidence,
)
from ade_api.features.agent_runtime_v3.release_policy import (
    AGENT_STUDIO_RELEASE_ROUTES,
)
from ade_api.features.test_center.agent_runtime_parity_evaluations import (
    AgentRuntimeParityEvaluationReader,
)
from workflows.evals.agent_runtime_v3_acceptance.policy import (
    production_policy_hashes,
)
from workflows.evals.agent_runtime_v3_acceptance.promotion_review import (
    GitState,
    review_promotion,
)


DEFAULT_MANIFEST = PROJECT_ROOT / "config/model-router/deployment-manifest.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "config/agent-studio/release-evidence.json"


class CutoverReviewError(RuntimeError):
    pass


def review_cutover(
    *,
    qualification_proposal_path: Path,
    parity_root: Path,
    conformance_receipt_path: Path,
    rollback_receipt_path: Path,
    manifest_path: Path,
    project_root: Path,
    reviewer: str,
    reviewed_at: datetime | None = None,
) -> dict[str, Any]:
    proposal = _load_json(qualification_proposal_path, "qualification proposal")
    source_revision = _required_text(proposal, "source_revision")
    qualification_source = {
        "source_revision": source_revision,
        "source_dirty": proposal.get("source_dirty"),
        "source_fingerprint": _required_text(proposal, "source_fingerprint"),
    }
    review_promotion(
        proposal_path=qualification_proposal_path,
        manifest_path=manifest_path,
        project_root=project_root,
        apply=False,
        git_state=GitState(revision=source_revision, dirty=False),
    )
    qualification_provenance = _load_json(
        qualification_proposal_path.parent / "provenance.json",
        "qualification provenance",
    )
    compatibility = _mapping(
        qualification_provenance.get("llama_compatibility"),
        "llama compatibility",
    )
    if compatibility.get("passed") is not True:
        raise CutoverReviewError("llama-server compatibility did not pass")

    parity_detail, parity_spec = _read_parity(parity_root)
    if parity_spec.get("schema_version") != 2:
        raise CutoverReviewError(
            "paired Agent Studio evidence must use schema_version 2"
        )
    rounds_requested = _required_round_count(parity_detail, "rounds_requested")
    rounds_completed = _required_round_count(parity_detail, "rounds_completed")
    rounds_passed = _required_round_count(parity_detail, "rounds_passed")
    native_rounds_passed = _required_round_count(parity_detail, "native_rounds_passed")
    legacy_rounds_passed = _required_round_count(parity_detail, "legacy_rounds_passed")
    if not (
        parity_detail.get("passed") is True
        and parity_detail.get("inputs_comparable") is True
        and parity_detail.get("cleanup_complete") is True
        and rounds_requested == 3
        and rounds_completed == 3
        and rounds_passed == native_rounds_passed
        and native_rounds_passed == 3
        and parity_detail.get("native_not_worse_than_legacy") is True
    ):
        raise CutoverReviewError("paired Agent Studio parity is incomplete")
    product_api = _mapping(
        parity_spec.get("shared_product_contract"), "shared product contract"
    ).get("native_product_api")
    if product_api != "/api/v3/agent-studio/sessions":
        raise CutoverReviewError("paired parity did not exercise Agent Studio sessions")

    conformance = _read_signed_receipt(
        conformance_receipt_path,
        kind="ade-agent-studio-conformance-receipt",
        digest_field="artifact_sha256",
    )
    rollback = _read_signed_receipt(
        rollback_receipt_path,
        kind="ade-agent-studio-rollback-rehearsal",
        digest_field="receipt_sha256",
    )
    parity_source = _mapping(
        parity_detail.get("provenance"), "parity source provenance"
    )
    _require_same_source(parity_source, qualification_source, "qualification")
    _require_same_source(parity_source, conformance, "conformance")
    _require_same_source(parity_source, rollback, "rollback rehearsal")
    if conformance.get("passed") is not True or conformance.get("test_paths") != list(
        REQUIRED_CONFORMANCE_TESTS
    ):
        raise CutoverReviewError("deterministic conformance receipt is incomplete")
    if not all(
        rollback.get(field) is True
        for field in (
            "rehearsed",
            "legacy_source_verified",
            "legacy_web_image_built",
            "legacy_web_smoke_passed",
            "legacy_web_api_read_passed",
            "legacy_web_api_write_passed",
            "legacy_web_api_cleanup_passed",
            "legacy_health_passed",
            "native_state_preserved",
        )
    ):
        raise CutoverReviewError("rollback rehearsal is incomplete")

    manifest = load_deployment_manifest(manifest_path, project_root=project_root)
    policies = production_policy_hashes(project_root)
    routes = _qualified_routes(manifest)
    qualification_digest = _required_text(proposal, "proposal_sha256")
    parity_digests = _mapping(
        parity_detail.get("artifact_digests"), "parity artifact digests"
    )
    parity_evidence_digest = _required_text(parity_digests, "evidence_sha256")
    conformance_digest = _required_text(conformance, "artifact_sha256")
    payload: dict[str, Any] = {
        "schema_version": 2,
        "kind": "ade-agent-studio-cutover-evidence",
        "decision": "approved",
        "reviewed_by": reviewer.strip(),
        "reviewed_at": (reviewed_at or datetime.now(UTC)).astimezone(UTC).isoformat(),
        "evaluated_source": {
            "revision": _required_text(parity_source, "source_revision"),
            "dirty": parity_source.get("source_dirty"),
            "fingerprint": _required_text(parity_source, "source_fingerprint"),
        },
        "manifest_sha256": file_sha256(manifest_path),
        "policy_hashes": policies,
        "qualified_routes": routes,
        "qualification": {
            "run_id": _required_text(proposal, "run_id"),
            "passed": True,
            "proposal_sha256": qualification_digest,
            "canonical_case_keys_sha256": _required_text(
                qualification_provenance, "canonical_case_keys_sha256"
            ),
            "round_artifact_sha256s": proposal.get("round_artifact_sha256s"),
            "llama_compatibility": {
                "passed": True,
                "artifact_sha256": _required_text(compatibility, "artifact_sha256"),
            },
        },
        "paired_parity": {
            "run_id": _required_text(parity_detail, "run_id"),
            "passed": True,
            "inputs_comparable": True,
            "cleanup_complete": True,
            "rounds_requested": 3,
            "rounds_completed": 3,
            # Retain rounds_passed as the candidate alias in the signed ledger.
            "rounds_passed": native_rounds_passed,
            "native_rounds_passed": native_rounds_passed,
            "legacy_rounds_passed": legacy_rounds_passed,
            "native_not_worse_than_legacy": parity_detail[
                "native_not_worse_than_legacy"
            ],
            "native_product_api": product_api,
            "artifact_digests": dict(parity_digests),
        },
        "conformance": {
            "passed": True,
            "receipt_sha256": conformance_digest,
            "test_paths": list(REQUIRED_CONFORMANCE_TESTS),
        },
        "capability_evidence": _capability_evidence(
            qualification_digest=qualification_digest,
            parity_evidence_digest=parity_evidence_digest,
            conformance_digest=conformance_digest,
        ),
        "rollback_rehearsal": {
            "rehearsed": True,
            "legacy_source_verified": True,
            "legacy_web_image_built": True,
            "legacy_web_smoke_passed": True,
            "legacy_web_api_read_passed": True,
            "legacy_web_api_write_passed": True,
            "legacy_web_api_cleanup_passed": True,
            "legacy_health_passed": True,
            "native_state_preserved": True,
            "legacy_revision": _required_text(rollback, "legacy_revision"),
            "rehearsed_at": _required_text(rollback, "rehearsed_at"),
            "receipt_sha256": _required_text(rollback, "receipt_sha256"),
        },
    }
    payload["evidence_sha256"] = canonical_sha256(payload)
    try:
        validate_agent_studio_release_evidence(
            payload,
            manifest=manifest,
            manifest_sha256=file_sha256(manifest_path),
            policy_hashes=policies,
            release_routes=AGENT_STUDIO_RELEASE_ROUTES,
        )
    except AgentStudioReleaseEvidenceError as exc:
        raise CutoverReviewError(str(exc)) from exc
    return payload


def _read_parity(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved = root.resolve()
    if not resolved.name.startswith("parity-"):
        raise CutoverReviewError("parity artifact directory must start with parity-")
    run_id = resolved.name.removeprefix("parity-")
    reader = AgentRuntimeParityEvaluationReader(resolved.parent)
    detail = reader.detail(
        {
            "run_id": run_id,
            "status": "passed",
            "output_dir": str(resolved.parent),
            "options": {},
            "created_at": "",
            "finished_at": "",
        }
    )
    spec = _load_json(resolved / "parity-spec.json", "parity spec")
    return detail, spec


def _read_signed_receipt(path: Path, *, kind: str, digest_field: str) -> dict[str, Any]:
    payload = _load_json(path, kind)
    digest = _required_text(payload, digest_field)
    material = {key: value for key, value in payload.items() if key != digest_field}
    if canonical_sha256(material) != digest:
        raise CutoverReviewError(f"{kind} digest does not match")
    if payload.get("schema_version") != 1 or payload.get("kind") != kind:
        raise CutoverReviewError(f"{kind} identity is invalid")
    return payload


def _require_same_source(
    parity_source: Mapping[str, Any], receipt: Mapping[str, Any], label: str
) -> None:
    expected = {
        "source_revision": parity_source.get("source_revision"),
        "source_dirty": parity_source.get("source_dirty"),
        "source_fingerprint": parity_source.get("source_fingerprint"),
    }
    actual = {key: receipt.get(key) for key in expected}
    if actual != expected or actual["source_dirty"] is not False:
        raise CutoverReviewError(f"{label} used a different source build")


def _qualified_routes(manifest: Any) -> dict[str, dict[str, str]]:
    routes: dict[str, dict[str, str]] = {}
    for role, route_alias in AGENT_STUDIO_RELEASE_ROUTES.items():
        deployment = manifest.for_route_alias(route_alias)
        if deployment is None:
            raise CutoverReviewError(f"qualified route is missing for {role}")
        routes[role] = {
            "route_alias": route_alias,
            "deployment_id": deployment.deployment_id,
            "fingerprint_sha256": deployment.fingerprint.sha256,
        }
    return routes


def _capability_evidence(
    *,
    qualification_digest: str,
    parity_evidence_digest: str,
    conformance_digest: str,
) -> dict[str, dict[str, Any]]:
    qualification_cases = {
        "subject_isolation": [
            "cross_agent_subject_sharing",
            "cross_subject_isolation",
        ],
        "old_memory_retrieval": ["old_memory_deep_search"],
        "long_history_compaction": ["long_history_compaction"],
        "false_memory_prevention": ["false_memory_prevention"],
        "tool_selection": ["weather_tool_selection"],
        "tool_failure": ["weather_tool_failure"],
        "trace_preservation": ["all canonical qualification cases"],
    }
    evidence = {
        "memory_correctness": {
            "status": "passed",
            "evidence_kind": "paired-parity",
            "artifact_sha256": parity_evidence_digest,
            "references": ["chat_memory_baseline"],
        },
        **{
            capability: {
                "status": "passed",
                "evidence_kind": "native-qualification",
                "artifact_sha256": qualification_digest,
                "references": references,
            }
            for capability, references in qualification_cases.items()
        },
        "timeout_retry_ownership": {
            "status": "passed",
            "evidence_kind": "deterministic-contract",
            "artifact_sha256": conformance_digest,
            "references": ["test_retry.py", "test_provider_tracing.py"],
        },
        "cancellation": {
            "status": "passed",
            "evidence_kind": "deterministic-contract",
            "artifact_sha256": conformance_digest,
            "references": ["test_client.py", "test_rounds.py"],
        },
    }
    return dict(sorted(evidence.items()))


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CutoverReviewError(f"could not read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise CutoverReviewError(f"{label} must be a JSON object")
    return payload


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CutoverReviewError(f"{label} must be an object")
    return value


def _required_text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CutoverReviewError(f"{field} is required")
    return value.strip()


def _required_round_count(payload: Mapping[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 3:
        raise CutoverReviewError(f"{field} must be an integer from 0 to 3")
    return value


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Review qualification, paired baseline evidence, deterministic conformance, "
            "and rollback evidence into the single Agent Studio activation ledger."
        )
    )
    parser.add_argument("--qualification-proposal", type=Path, required=True)
    parser.add_argument("--parity-root", type=Path, required=True)
    parser.add_argument("--conformance-receipt", type=Path, required=True)
    parser.add_argument("--rollback-receipt", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = review_cutover(
            qualification_proposal_path=args.qualification_proposal,
            parity_root=args.parity_root,
            conformance_receipt_path=args.conformance_receipt,
            rollback_receipt_path=args.rollback_receipt,
            manifest_path=args.manifest,
            project_root=PROJECT_ROOT,
            reviewer=args.reviewer,
        )
    except (CutoverReviewError, ValueError) as exc:
        parser.error(str(exc))
    if args.apply:
        _atomic_write(args.output, payload)
        print(f"Wrote reviewed cutover evidence: {args.output}")
    else:
        print("Cutover evidence review passed; rerun with --apply to write the ledger.")
    print(f"evidence_sha256={payload['evidence_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
