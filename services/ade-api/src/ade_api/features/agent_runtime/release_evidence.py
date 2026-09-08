from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from model_catalog_contracts.deployment_manifest import DeploymentManifest


REQUIRED_CONFORMANCE_TESTS = (
    "services/ade-api/tests/agent_runtime/test_retry.py",
    "services/ade-api/tests/agent_runtime/test_provider_tracing.py",
    "services/ade-api/tests/agent_runtime/test_run_service.py",
    "services/ade-api/tests/agent_runtime/test_worker_events.py",
    "services/ade-api/tests/agent_runtime/persistence/test_repository_contracts.py",
)
RELEASE_ROLES = ("conversation", "reviewer", "retriever")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40,64}$")


class AgentStudioReleaseEvidenceError(RuntimeError):
    """Raised when reviewed release evidence cannot authorize product traffic."""


@dataclass(frozen=True)
class AgentStudioAgentBundle:
    prompt_key: str
    persona_key: str
    tool_names: tuple[str, ...]


@dataclass(frozen=True)
class AgentStudioReleaseEvidence:
    evidence_sha256: str
    qualification_run_id: str
    evaluated_source_revision: str
    evaluated_source_fingerprint: str
    route_aliases: dict[str, str]
    agent_bundle: AgentStudioAgentBundle


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
            f"Agent Studio release evidence is unavailable: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio release evidence must be a JSON object"
        )
    return payload


def validate_agent_studio_release_evidence(
    payload: Mapping[str, Any],
    *,
    manifest: DeploymentManifest,
    manifest_sha256: str,
    policy_hashes: Mapping[str, str],
) -> AgentStudioReleaseEvidence:
    """Validate the self-contained steady-state release authorization ledger."""

    material = dict(payload)
    evidence_sha256 = _required_digest(
        material.pop("evidence_sha256", None), "evidence_sha256"
    )
    if canonical_sha256(material) != evidence_sha256:
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio release evidence digest does not match its content"
        )
    if material.get("schema_version") != 3:
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio release evidence schema_version must be 3"
        )
    if material.get("kind") != "ade-agent-studio-release-evidence":
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio release evidence kind is invalid"
        )
    if material.get("decision") != "approved":
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio release evidence is not approved"
        )
    _required_text(material, "reviewed_by")
    _required_text(material, "reviewed_at")

    source = _mapping(material.get("evaluated_source"), "evaluated_source")
    source_revision = _required_revision(source.get("revision"))
    source_fingerprint = _required_digest(
        source.get("fingerprint"), "evaluated source fingerprint"
    )
    if source.get("dirty") is not False:
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio release evidence must come from a clean source"
        )
    _validate_build_identity(
        _mapping(material.get("build_identity"), "build_identity"),
        revision=source_revision,
        fingerprint=source_fingerprint,
    )

    if _required_digest(material.get("manifest_sha256"), "manifest_sha256") != (
        _required_digest(manifest_sha256, "current manifest SHA-256")
    ):
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio release evidence does not match the deployment manifest"
        )
    expected_policies = {
        str(key): _required_digest(value, f"{key} policy hash")
        for key, value in policy_hashes.items()
    }
    if (
        _digest_mapping(material.get("policy_hashes"), "policy_hashes")
        != expected_policies
    ):
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio release evidence uses stale runtime policies"
        )

    route_aliases = _validate_qualified_routes(
        _mapping(material.get("qualified_routes"), "qualified_routes"),
        manifest=manifest,
        policy_hashes=expected_policies,
    )
    agent_bundle = _validate_agent_bundle(
        _mapping(material.get("agent_bundle"), "agent_bundle")
    )
    qualification_run_id = _validate_native_qualification(
        _mapping(material.get("qualification"), "qualification")
    )
    _validate_conformance(_mapping(material.get("conformance"), "conformance"))

    return AgentStudioReleaseEvidence(
        evidence_sha256=evidence_sha256,
        qualification_run_id=qualification_run_id,
        evaluated_source_revision=source_revision,
        evaluated_source_fingerprint=source_fingerprint,
        route_aliases=route_aliases,
        agent_bundle=agent_bundle,
    )


def _validate_build_identity(
    build_identity: Mapping[str, Any], *, revision: str, fingerprint: str
) -> None:
    if set(build_identity) != {"api", "worker"}:
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio release evidence must bind API and worker build identities"
        )
    expected = {"revision": revision, "fingerprint": fingerprint}
    for component in ("api", "worker"):
        identity = _mapping(
            build_identity.get(component), f"{component} build identity"
        )
        actual = {
            "revision": _required_revision(identity.get("revision")),
            "fingerprint": _required_digest(
                identity.get("fingerprint"), f"{component} build fingerprint"
            ),
        }
        if dict(identity) != expected or actual != expected:
            raise AgentStudioReleaseEvidenceError(
                f"Agent Studio {component} build identity does not match the evaluated source"
            )


def _validate_qualified_routes(
    routes: Mapping[str, Any],
    *,
    manifest: DeploymentManifest,
    policy_hashes: Mapping[str, str],
) -> dict[str, str]:
    if set(routes) != set(RELEASE_ROLES):
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio release evidence does not bind every release role"
        )
    aliases: dict[str, str] = {}
    for role in RELEASE_ROLES:
        item = _mapping(routes.get(role), f"{role} qualified route")
        route_alias = _required_text(item, "route_alias")
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
                f"Agent Studio release evidence route is stale for {role}"
            )
        _validate_manifest_qualification(deployment, role, policy_hashes)
        aliases[role] = route_alias
    return aliases


def _validate_manifest_qualification(
    deployment: Any, role: str, policy_hashes: Mapping[str, str]
) -> None:
    qualification = deployment.qualification
    role_result = next(
        (item for item in qualification.role_results if item.role == role), None
    )
    if (
        deployment.lifecycle != "qualified"
        or not qualification.qualified
        or qualification.stale_round_count != 0
        or role_result is None
        or not role_result.qualified
        or role_result.observed_rounds < 3
        or role_result.consecutive_passing_rounds < 3
    ):
        raise AgentStudioReleaseEvidenceError(
            f"Deployment {deployment.deployment_id} is not qualified for {role}"
        )
    fingerprint = deployment.fingerprint
    actual_policies = {
        "prompt": fingerprint.prompt_policy_sha256,
        "tool": fingerprint.tool_policy_sha256,
        "schema": fingerprint.schema_policy_sha256,
        "retrieval": fingerprint.retrieval_policy_sha256,
    }
    if actual_policies != dict(policy_hashes):
        raise AgentStudioReleaseEvidenceError(
            f"Deployment {deployment.deployment_id} qualification uses stale policy hashes"
        )


def _validate_agent_bundle(bundle: Mapping[str, Any]) -> AgentStudioAgentBundle:
    if set(bundle) != {"prompt_key", "persona_key", "tool_names"}:
        raise AgentStudioReleaseEvidenceError("Agent Studio agent bundle is invalid")
    tool_names = bundle.get("tool_names")
    if (
        not isinstance(tool_names, list)
        or not tool_names
        or any(not isinstance(name, str) or not name.strip() for name in tool_names)
        or len(tool_names) != len(set(tool_names))
    ):
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio agent bundle tool_names must be unique non-empty strings"
        )
    return AgentStudioAgentBundle(
        prompt_key=_required_text(bundle, "prompt_key"),
        persona_key=_required_text(bundle, "persona_key"),
        tool_names=tuple(name.strip() for name in tool_names),
    )


def _validate_native_qualification(qualification: Mapping[str, Any]) -> str:
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
        qualification.get("round_artifact_sha256s"), "qualification round artifacts"
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
    return qualification_run_id


def _validate_conformance(conformance: Mapping[str, Any]) -> None:
    if conformance.get("passed") is not True:
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio deterministic conformance did not pass"
        )
    _required_digest(conformance.get("receipt_sha256"), "conformance receipt")
    if conformance.get("test_paths") != list(REQUIRED_CONFORMANCE_TESTS):
        raise AgentStudioReleaseEvidenceError(
            "Agent Studio deterministic conformance suite is incomplete"
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
