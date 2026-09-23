from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from model_catalog_contracts.deployment_manifest import DeploymentManifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ade_api.features.agent_runtime.release_evidence import (
    REQUIRED_CONFORMANCE_TESTS,
    AgentStudioReleaseEvidenceError,
    canonical_sha256,
    validate_agent_studio_release_evidence,
)
from ade_api.features.agent_runtime.release_policy import production_policy_hashes
from scripts.embedding_space_compatibility import (
    EmbeddingCompatibilityError,
    validate_embedding_compatibility_receipt,
)
from workflows.evals.agent_runtime_acceptance.promotion_review import (
    GitState,
    PromotionReviewError,
    review_promotion,
)


DEFAULT_MANIFEST = PROJECT_ROOT / "config/model-router/deployment-manifest.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "config/agent-studio/release-evidence.json"


class ReleasePromotionError(RuntimeError):
    pass


def prepare_release_promotion(
    *,
    qualification_proposal_path: Path,
    conformance_receipt_path: Path,
    manifest_path: Path,
    project_root: Path,
    reviewer: str,
    embedding_compatibility_receipt_path: Path | None = None,
    reviewed_at: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate one release and return its manifest and evidence payloads."""

    proposal = _load_json(qualification_proposal_path, "qualification proposal")
    source_revision = _required_text(proposal, "source_revision")
    source_fingerprint = _required_text(proposal, "source_fingerprint")
    if proposal.get("source_dirty") is not False:
        raise ReleasePromotionError("qualification proposal must use a clean source")
    try:
        promotion = review_promotion(
            proposal_path=qualification_proposal_path,
            manifest_path=manifest_path,
            project_root=project_root,
            apply=False,
            git_state=GitState(revision=source_revision, dirty=False),
        )
    except PromotionReviewError as exc:
        raise ReleasePromotionError(str(exc)) from exc

    provenance = _load_json(
        qualification_proposal_path.parent / "provenance.json",
        "qualification provenance",
    )
    effective_config = _mapping(provenance.get("effective_config"), "effective config")
    include_compatibility = effective_config.get("include_llama_compatibility")
    if type(include_compatibility) is not bool:
        raise ReleasePromotionError("compatibility selection must be explicit")
    compatibility = provenance.get("llama_compatibility")
    compatibility_checks: list[dict[str, Any]] = []
    if include_compatibility:
        compatibility = _mapping(compatibility, "configured compatibility")
        route_alias = _required_text(effective_config, "llama_compatibility_model_key")
        snapshots = compatibility.get("deployment_snapshots")
        if not isinstance(snapshots, list) or not any(
            isinstance(item, dict)
            and item.get("role") == "conversation"
            and item.get("route_alias") == route_alias
            for item in snapshots
        ):
            raise ReleasePromotionError(
                "configured compatibility artifact does not bind its route"
            )
        compatibility_checks.append(
            {
                "route_alias": route_alias,
                "passed": True,
                "artifact_sha256": _required_text(compatibility, "artifact_sha256"),
            }
        )
    elif compatibility is not None:
        raise ReleasePromotionError(
            "unselected compatibility evidence cannot authorize release"
        )
    agent_bundle = _mapping(proposal.get("agent_bundle"), "agent bundle")
    if include_compatibility and compatibility.get("passed") is not True:
        raise ReleasePromotionError("configured compatibility did not pass")

    conformance = _read_signed_receipt(
        conformance_receipt_path,
        kind="ade-agent-studio-conformance-receipt",
        digest_field="artifact_sha256",
    )
    _require_same_source(
        source_revision=source_revision,
        source_fingerprint=source_fingerprint,
        receipt=conformance,
        label="deterministic conformance",
    )
    if conformance.get("passed") is not True or conformance.get("test_paths") != list(
        REQUIRED_CONFORMANCE_TESTS
    ):
        raise ReleasePromotionError("deterministic conformance receipt is incomplete")

    manifest_payload = promotion.manifest_payload
    manifest = DeploymentManifest.from_payload(manifest_payload)
    manifest_sha256 = hashlib.sha256(_json_bytes(manifest_payload)).hexdigest()
    policies = production_policy_hashes(project_root)
    qualified_routes = _qualified_routes(proposal, manifest)
    embedding_compatibility = _embedding_space_evidence(
        manifest=manifest,
        retriever_alias=qualified_routes["retriever"]["route_alias"],
        source_revision=source_revision,
        source_fingerprint=source_fingerprint,
        receipt_path=embedding_compatibility_receipt_path,
    )
    evidence: dict[str, Any] = {
        "schema_version": 4,
        "kind": "ade-agent-studio-release-evidence",
        "decision": "approved",
        "reviewed_by": reviewer.strip(),
        "reviewed_at": (reviewed_at or datetime.now(UTC)).astimezone(UTC).isoformat(),
        "evaluated_source": {
            "revision": source_revision,
            "dirty": False,
            "fingerprint": source_fingerprint,
        },
        "build_identity": {
            "api": {"revision": source_revision, "fingerprint": source_fingerprint},
            "worker": {
                "revision": source_revision,
                "fingerprint": source_fingerprint,
            },
        },
        "manifest_sha256": manifest_sha256,
        "policy_hashes": policies,
        "qualified_routes": qualified_routes,
        "agent_bundle": dict(agent_bundle),
        "qualification": {
            "run_id": _required_text(proposal, "run_id"),
            "passed": True,
            "proposal_sha256": _required_text(proposal, "proposal_sha256"),
            "canonical_case_keys_sha256": _required_text(
                provenance, "canonical_case_keys_sha256"
            ),
            "round_artifact_sha256s": proposal.get("round_artifact_sha256s"),
            "compatibility_checks": compatibility_checks,
            "embedding_space_compatibility": embedding_compatibility,
        },
        "conformance": {
            "passed": True,
            "receipt_sha256": _required_text(conformance, "artifact_sha256"),
            "test_paths": list(REQUIRED_CONFORMANCE_TESTS),
        },
    }
    evidence["evidence_sha256"] = canonical_sha256(evidence)
    try:
        validate_agent_studio_release_evidence(
            evidence,
            manifest=manifest,
            manifest_sha256=manifest_sha256,
            policy_hashes=policies,
        )
    except AgentStudioReleaseEvidenceError as exc:
        raise ReleasePromotionError(str(exc)) from exc
    return manifest_payload, evidence


def apply_release_promotion(
    *,
    manifest_path: Path,
    evidence_path: Path,
    manifest_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
) -> None:
    """Replace both release files and restore their prior state on failure."""

    replacements = (
        (manifest_path, _json_bytes(manifest_payload)),
        (evidence_path, _json_bytes(evidence_payload)),
    )
    originals = {
        path: path.read_bytes() if path.is_file() else None for path, _ in replacements
    }
    temporaries: dict[Path, Path] = {}
    try:
        for path, content in replacements:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(f"{path.suffix}.tmp-{os.getpid()}")
            _write_bytes(temporary, content)
            temporaries[path] = temporary
        for path, _ in replacements:
            temporaries[path].replace(path)
    except OSError as exc:
        restore_errors: list[str] = []
        for path, _ in replacements:
            try:
                original = originals[path]
                if original is None:
                    path.unlink(missing_ok=True)
                else:
                    restore_path = path.with_suffix(
                        f"{path.suffix}.restore-{os.getpid()}"
                    )
                    _write_bytes(restore_path, original)
                    restore_path.replace(path)
            except OSError as restore_exc:
                restore_errors.append(f"{path}: {restore_exc}")
        detail = (
            f"; restore failed for {', '.join(restore_errors)}"
            if restore_errors
            else ""
        )
        raise ReleasePromotionError(
            f"release promotion write failed: {exc}{detail}"
        ) from exc
    finally:
        for temporary in temporaries.values():
            temporary.unlink(missing_ok=True)


def _qualified_routes(
    proposal: Mapping[str, Any], manifest: DeploymentManifest
) -> dict[str, dict[str, str]]:
    bindings = _mapping(proposal.get("deployment_bindings"), "deployment bindings")
    routes: dict[str, dict[str, str]] = {}
    for role in ("conversation", "reviewer", "retriever"):
        binding = _mapping(bindings.get(role), f"{role} deployment binding")
        route_alias = _required_text(binding, "route_alias")
        deployment = manifest.for_route_alias(route_alias)
        if deployment is None:
            raise ReleasePromotionError(f"qualified route is missing for {role}")
        expected = {
            "route_alias": route_alias,
            "deployment_id": deployment.deployment_id,
            "fingerprint_sha256": deployment.fingerprint.sha256,
        }
        if dict(binding) != expected:
            raise ReleasePromotionError(
                f"qualification binding does not match the manifest for {role}"
            )
        routes[role] = expected
    return routes


def _embedding_space_evidence(
    *,
    manifest: DeploymentManifest,
    retriever_alias: str,
    source_revision: str,
    source_fingerprint: str,
    receipt_path: Path | None,
) -> dict[str, Any]:
    deployment = manifest.for_route_alias(retriever_alias)
    if deployment is None:
        raise ReleasePromotionError("retriever deployment is missing")
    fingerprint = deployment.fingerprint
    space = _mapping(
        fingerprint.sampling_settings.get("vector_space"), "retriever vector space"
    )
    space_id = _required_text(space, "id")
    context = fingerprint.context_settings
    origin_url = _required_text(context, "vector_space_origin_url")
    route_url = _required_text(context, "route_base_url")
    origin_runtime = _mapping(
        context.get("vector_space_origin_runtime"), "vector space origin runtime"
    )
    current_runtime = {
        "implementation": fingerprint.runtime_implementation,
        "version": fingerprint.runtime_version,
        "image_digest": fingerprint.runtime_image_digest,
    }
    common = {
        "space_id": space_id,
        "route_alias": retriever_alias,
        "deployment_fingerprint": fingerprint.sha256,
    }
    if route_url == origin_url and dict(origin_runtime) == current_runtime:
        if receipt_path is not None:
            raise ReleasePromotionError(
                "origin embedding deployment must not substitute a relocation receipt"
            )
        return {**common, "mode": "origin"}
    if receipt_path is None:
        raise ReleasePromotionError(
            "relocated embedding deployment requires a compatibility receipt"
        )
    receipt = _load_json(receipt_path, "embedding compatibility receipt")
    try:
        artifact_sha256 = validate_embedding_compatibility_receipt(
            receipt,
            source_revision=source_revision,
            source_fingerprint=source_fingerprint,
            space_id=space_id,
            route_alias=retriever_alias,
            deployment_fingerprint=fingerprint.sha256,
            origin_url=origin_url,
            candidate_url=route_url,
            dimensions=int(space.get("dimensions") or 0),
        )
    except EmbeddingCompatibilityError as exc:
        raise ReleasePromotionError(str(exc)) from exc
    return {
        **common,
        "mode": "verified",
        "passed": True,
        "artifact_sha256": artifact_sha256,
    }


def _read_signed_receipt(path: Path, *, kind: str, digest_field: str) -> dict[str, Any]:
    payload = _load_json(path, kind)
    digest = _required_text(payload, digest_field)
    material = {key: value for key, value in payload.items() if key != digest_field}
    if canonical_sha256(material) != digest:
        raise ReleasePromotionError(f"{kind} digest does not match")
    if payload.get("schema_version") != 1 or payload.get("kind") != kind:
        raise ReleasePromotionError(f"{kind} identity is invalid")
    return payload


def _require_same_source(
    *,
    source_revision: str,
    source_fingerprint: str,
    receipt: Mapping[str, Any],
    label: str,
) -> None:
    actual = {
        "source_revision": receipt.get("source_revision"),
        "source_dirty": receipt.get("source_dirty"),
        "source_fingerprint": receipt.get("source_fingerprint"),
    }
    expected = {
        "source_revision": source_revision,
        "source_dirty": False,
        "source_fingerprint": source_fingerprint,
    }
    if actual != expected:
        raise ReleasePromotionError(f"{label} used a different source build")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleasePromotionError(f"could not read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise ReleasePromotionError(f"{label} must be a JSON object")
    return payload


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReleasePromotionError(f"{label} must be an object")
    return value


def _required_text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ReleasePromotionError(f"{field} is required")
    return value.strip()


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _write_bytes(path: Path, content: bytes) -> None:
    with path.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate qualification and conformance, then atomically promote the "
            "Agent Studio deployment manifest and release ledger."
        )
    )
    parser.add_argument("--qualification-proposal", type=Path, required=True)
    parser.add_argument("--conformance-receipt", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--embedding-compatibility-receipt", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest_payload, evidence_payload = prepare_release_promotion(
            qualification_proposal_path=args.qualification_proposal,
            conformance_receipt_path=args.conformance_receipt,
            manifest_path=args.manifest,
            project_root=PROJECT_ROOT,
            reviewer=args.reviewer,
            embedding_compatibility_receipt_path=args.embedding_compatibility_receipt,
        )
        if args.apply:
            apply_release_promotion(
                manifest_path=args.manifest,
                evidence_path=args.output,
                manifest_payload=manifest_payload,
                evidence_payload=evidence_payload,
            )
    except (ReleasePromotionError, ValueError) as exc:
        parser.error(str(exc))
    if args.apply:
        print(f"Promoted deployment manifest and release evidence: {args.output}")
    else:
        print("Release promotion passed; rerun with --apply to write both files.")
    print(f"evidence_sha256={evidence_payload['evidence_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
