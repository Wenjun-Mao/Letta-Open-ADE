from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from model_catalog_contracts.deployment_manifest import DeploymentManifest


REQUIRED_CAPABILITY_EVIDENCE = (
    "memory_correctness",
    "subject_isolation",
    "old_memory_retrieval",
    "long_history_compaction",
    "false_memory_prevention",
    "tool_selection",
    "tool_failure",
    "timeout_retry_ownership",
    "cancellation",
    "trace_preservation",
)
REQUIRED_CONFORMANCE_TESTS = (
    "services/ade-api/tests/agent_runtime_v3/test_retry.py",
    "services/ade-api/tests/agent_runtime_v3/test_provider_tracing.py",
    "services/ade-api/tests/agent_runtime_v3/test_run_service.py",
    "services/ade-api/tests/agent_runtime_v3/test_worker_events.py",
    "services/ade-api/tests/agent_runtime_v3/persistence/test_repository_contracts.py",
    "workflows/evals/agent_runtime_v3_acceptance/tests/test_client.py",
    "workflows/evals/agent_runtime_v3_acceptance/tests/test_rounds.py",
)
ALLOWED_EVIDENCE_KINDS = frozenset(
    {"paired-parity", "native-qualification", "deterministic-contract"}
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40,64}$")


class AgentStudioReleaseEvidenceError(RuntimeError):
    """Raised when the reviewed cutover evidence cannot authorize release."""


@dataclass(frozen=True)
class AgentStudioReleaseEvidence:
    evidence_sha256: str
    qualification_run_id: str
    parity_run_id: str
    evaluated_source_revision: str


def canonical_sha256(payload: object) -> str:
    material = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_agent_studio_release_evidence(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AgentStudioReleaseEvidenceError(
            f"Agent Studio cutover evidence is unavailable: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio cutover evidence must be a JSON object"
        )
    return payload


def validate_agent_studio_release_evidence(
    payload: Mapping[str, Any],
    *,
    manifest: DeploymentManifest,
    manifest_sha256: str,
    policy_hashes: Mapping[str, str],
    release_routes: Mapping[str, str],
) -> AgentStudioReleaseEvidence:
    material = dict(payload)
    evidence_sha256 = _required_digest(
        material.pop("evidence_sha256", None), "evidence_sha256"
    )
    if canonical_sha256(material) != evidence_sha256:
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio cutover evidence digest does not match its content"
        )
    if material.get("schema_version") != 1:
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio cutover evidence schema_version must be 1"
        )
    if material.get("kind") != "ade-agent-studio-cutover-evidence":
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio cutover evidence kind is invalid"
        )
    if material.get("decision") != "approved":
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio cutover evidence is not approved"
        )
    _required_text(material, "reviewed_by")
    _required_text(material, "reviewed_at")

    source = _mapping(material.get("evaluated_source"), "evaluated_source")
    source_revision = _required_revision(source.get("revision"))
    _required_digest(source.get("fingerprint"), "evaluated source fingerprint")
    if source.get("dirty") is not False:
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio cutover evidence must come from a clean source"
        )

    if _required_digest(material.get("manifest_sha256"), "manifest_sha256") != (
        _required_digest(manifest_sha256, "current manifest SHA-256")
    ):
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio cutover evidence does not match the deployment manifest"
        )
    expected_policies = {
        str(key): _required_digest(value, f"{key} policy hash")
        for key, value in policy_hashes.items()
    }
    if _digest_mapping(material.get("policy_hashes"), "policy_hashes") != (
        expected_policies
    ):
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio cutover evidence uses stale runtime policies"
        )

    _validate_routes(
        _mapping(material.get("qualified_routes"), "qualified_routes"),
        manifest=manifest,
        release_routes=release_routes,
    )
    qualification = _mapping(material.get("qualification"), "qualification")
    qualification_run_id = _required_text(qualification, "run_id")
    if qualification.get("passed") is not True:
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio native qualification did not pass"
        )
    _required_digest(qualification.get("proposal_sha256"), "qualification proposal")
    _required_digest(
        qualification.get("canonical_case_keys_sha256"),
        "qualification canonical case matrix",
    )
    round_digests = _digest_list(
        qualification.get("round_artifact_sha256s"),
        "qualification round artifacts",
    )
    if len(round_digests) != 3 or len(set(round_digests)) != 3:
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio qualification requires three distinct passing rounds"
        )
    compatibility = _mapping(
        qualification.get("llama_compatibility"), "llama_compatibility"
    )
    if compatibility.get("passed") is not True:
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio qualification requires passing llama-server compatibility"
        )
    _required_digest(
        compatibility.get("artifact_sha256"), "llama compatibility artifact"
    )

    parity = _mapping(material.get("paired_parity"), "paired_parity")
    parity_run_id = _required_text(parity, "run_id")
    for field in ("passed", "inputs_comparable", "cleanup_complete"):
        if parity.get(field) is not True:
            raise AgentStudioReleaseEvidenceError(
                f"Agent Studio paired parity requires {field}=true"
            )
    for field in ("rounds_requested", "rounds_completed", "rounds_passed"):
        if parity.get(field) != 3:
            raise AgentStudioReleaseEvidenceError(
                "Agent Studio paired parity requires exactly three clean rounds"
            )
    if parity.get("native_product_api") != "/api/v3/agent-studio/sessions":
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio parity did not exercise the released session API"
        )
    digests = _digest_mapping(parity.get("artifact_digests"), "parity artifacts")
    required_artifacts = {
        "parity_spec_sha256",
        "provenance_sha256",
        "normalized_turns_sha256",
        "comparison_sha256",
        "summary_sha256",
        "evidence_sha256",
    }
    if set(digests) != required_artifacts:
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio parity artifact digest set is incomplete"
        )

    conformance = _mapping(material.get("conformance"), "conformance")
    if conformance.get("passed") is not True:
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio deterministic conformance did not pass"
        )
    conformance_digest = _required_digest(
        conformance.get("receipt_sha256"), "conformance receipt"
    )
    if conformance.get("test_paths") != list(REQUIRED_CONFORMANCE_TESTS):
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio deterministic conformance suite is incomplete"
        )

    coverage = _mapping(material.get("capability_evidence"), "capability_evidence")
    if set(coverage) != set(REQUIRED_CAPABILITY_EVIDENCE):
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio cutover capability evidence is incomplete"
        )
    qualification_digest = _required_digest(
        qualification.get("proposal_sha256"), "qualification proposal"
    )
    expected_capability_sources = {
        "memory_correctness": ("paired-parity", digests["evidence_sha256"]),
        "timeout_retry_ownership": ("deterministic-contract", conformance_digest),
        "cancellation": ("deterministic-contract", conformance_digest),
    }
    for capability in REQUIRED_CAPABILITY_EVIDENCE:
        item = _mapping(coverage.get(capability), capability)
        if item.get("status") != "passed":
            raise AgentStudioReleaseEvidenceError(
                f"Agent Studio capability evidence did not pass: {capability}"
            )
        evidence_kind = item.get("evidence_kind")
        if evidence_kind not in ALLOWED_EVIDENCE_KINDS:
            raise AgentStudioReleaseEvidenceError(
                f"Agent Studio capability evidence kind is invalid: {capability}"
            )
        artifact_sha256 = _required_digest(
            item.get("artifact_sha256"), f"{capability} artifact"
        )
        expected_kind, expected_digest = expected_capability_sources.get(
            capability,
            ("native-qualification", qualification_digest),
        )
        if (evidence_kind, artifact_sha256) != (expected_kind, expected_digest):
            raise AgentStudioReleaseEvidenceError(
                "Agent Studio capability evidence is not bound to its reviewed "
                f"artifact: {capability}"
            )
        references = item.get("references")
        if (
            not isinstance(references, list)
            or not references
            or any(
                not isinstance(value, str) or not value.strip() for value in references
            )
        ):
            raise AgentStudioReleaseEvidenceError(
                f"Agent Studio capability evidence has no references: {capability}"
            )

    rollback = _mapping(material.get("rollback_rehearsal"), "rollback_rehearsal")
    for field in (
        "rehearsed",
        "legacy_source_verified",
        "legacy_web_image_built",
        "legacy_web_smoke_passed",
        "legacy_health_passed",
        "native_state_preserved",
    ):
        if rollback.get(field) is not True:
            raise AgentStudioReleaseEvidenceError(
                f"Agent Studio rollback rehearsal requires {field}=true"
            )
    _required_revision(rollback.get("legacy_revision"))
    _required_text(rollback, "rehearsed_at")
    _required_digest(rollback.get("receipt_sha256"), "rollback receipt")

    return AgentStudioReleaseEvidence(
        evidence_sha256=evidence_sha256,
        qualification_run_id=qualification_run_id,
        parity_run_id=parity_run_id,
        evaluated_source_revision=source_revision,
    )


def _validate_routes(
    routes: Mapping[str, Any],
    *,
    manifest: DeploymentManifest,
    release_routes: Mapping[str, str],
) -> None:
    if set(routes) != set(release_routes):
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio cutover evidence does not bind every release role"
        )
    for role, route_alias in release_routes.items():
        item = _mapping(routes.get(role), f"{role} qualified route")
        deployment = manifest.for_route_alias(route_alias)
        if deployment is None or role not in deployment.roles:
            raise AgentStudioReleaseEvidenceError(
                f"Agent Studio release route is absent for {role}"
            )
        expected = {
            "route_alias": route_alias,
            "deployment_id": deployment.deployment_id,
            "fingerprint_sha256": deployment.fingerprint.sha256,
        }
        if dict(item) != expected:
            raise AgentStudioReleaseEvidenceError(
                f"Agent Studio cutover evidence route is stale for {role}"
            )


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AgentStudioReleaseEvidenceError(f"{label} must be an object")
    return value


def _required_text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise AgentStudioReleaseEvidenceError(f"{field} must be a non-empty string")
    return value.strip()


def _required_digest(value: object, label: str) -> str:
    digest = str(value or "").strip().casefold()
    if not _SHA256_RE.fullmatch(digest):
        raise AgentStudioReleaseEvidenceError(f"{label} must be a SHA-256 digest")
    return digest


def _required_revision(value: object) -> str:
    revision = str(value or "").strip().casefold()
    if not _REVISION_RE.fullmatch(revision):
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio evidence source revision is invalid"
        )
    return revision


def _digest_mapping(value: object, label: str) -> dict[str, str]:
    mapping = _mapping(value, label)
    return {
        str(key): _required_digest(item, f"{label}.{key}")
        for key, item in mapping.items()
    }


def _digest_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list):
        raise AgentStudioReleaseEvidenceError(f"{label} must be a list")
    return [_required_digest(item, label) for item in value]
