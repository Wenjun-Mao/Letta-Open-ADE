from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Mapping, TypeAlias


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FROZEN_VALUE_TYPES = (str, int, float, bool)


class DeploymentLifecycle(StrEnum):
    DISCOVERED = "discovered"
    CANDIDATE = "candidate"
    QUALIFIED = "qualified"
    DEPRECATED = "deprecated"


class DeploymentRole(StrEnum):
    CONVERSATION = "conversation"
    REVIEWER = "reviewer"
    RETRIEVER = "retriever"


class ReleaseTarget(StrEnum):
    PRODUCTION = "production"
    STUDY = "study"
    DEVELOPMENT = "development"


class DeploymentQualificationError(ValueError):
    pass


FrozenValue: TypeAlias = str | int | float | bool | None | tuple["FrozenValue", ...]
FrozenMetadata: TypeAlias = tuple[tuple[str, FrozenValue], ...]


def policy_bundle_hash(workflow_root: Path, relative_paths: Iterable[str]) -> str:
    """Hash path-bound policy inputs so renamed files cannot preserve a digest."""

    digest = hashlib.sha256()
    for relative_path in sorted(relative_paths):
        normalized = Path(relative_path).as_posix()
        path = workflow_root / normalized
        if not path.is_file():
            raise DeploymentQualificationError(
                f"policy input does not exist: {normalized}"
            )
        encoded_path = normalized.encode("utf-8")
        content = path.read_bytes()
        digest.update(len(encoded_path).to_bytes(8, "big"))
        digest.update(encoded_path)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return f"sha256:{digest.hexdigest()}"


def _non_empty(value: str | None, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise DeploymentQualificationError(f"{label} is required")
    return normalized


def _optional_text(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _normalize_sha256(value: str | None, label: str) -> str | None:
    normalized = _optional_text(value)
    if normalized is None:
        return None
    digest = normalized.removeprefix("sha256:")
    if not _SHA256_RE.fullmatch(digest):
        raise DeploymentQualificationError(f"{label} must be a SHA-256 digest")
    return f"sha256:{digest}"


def _required_sha256(value: str | None, label: str) -> str:
    normalized = _normalize_sha256(value, label)
    if normalized is None:
        raise DeploymentQualificationError(f"{label} is required")
    return normalized


def _freeze_value(value: object) -> FrozenValue:
    if value is None or isinstance(value, _FROZEN_VALUE_TYPES):
        return value
    if isinstance(value, Mapping):
        return freeze_metadata(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    raise DeploymentQualificationError(
        f"metadata values must be JSON-compatible, not {type(value).__name__}"
    )


def freeze_metadata(value: Mapping[str, object] | FrozenMetadata) -> FrozenMetadata:
    """Make metadata deeply immutable and order-independent for hashing."""

    items = value.items() if isinstance(value, Mapping) else value
    frozen: list[tuple[str, FrozenValue]] = []
    seen: set[str] = set()
    for raw_key, raw_value in items:
        key = _non_empty(str(raw_key), "metadata key")
        if key in seen:
            raise DeploymentQualificationError(f"duplicate metadata key: {key}")
        seen.add(key)
        frozen.append((key, _freeze_value(raw_value)))
    return tuple(sorted(frozen))


def _metadata_payload(value: FrozenMetadata) -> dict[str, object]:
    def thaw(item: FrozenValue) -> object:
        if isinstance(item, tuple):
            if all(
                isinstance(part, tuple) and len(part) == 2 and isinstance(part[0], str)
                for part in item
            ):
                return {str(key): thaw(nested) for key, nested in item}
            return [thaw(nested) for nested in item]
        return item

    return {key: thaw(item) for key, item in value}


@dataclass(frozen=True)
class DeploymentFingerprint:
    """The actual deployment contract; intentionally contains no route aliases."""

    provider: str
    endpoint_role: str
    endpoint_identity: str
    served_model: str
    artifact_reference: str
    artifact_revision: str | None = None
    artifact_sha256: str | None = None
    runtime_implementation: str = ""
    runtime_version: str | None = None
    runtime_image_digest: str | None = None
    prompt_policy_sha256: str = ""
    tool_policy_sha256: str = ""
    schema_policy_sha256: str = ""
    retrieval_policy_sha256: str = ""
    sampling_settings: Mapping[str, object] | FrozenMetadata = ()
    context_settings: Mapping[str, object] | FrozenMetadata = ()
    hardware_metadata: Mapping[str, object] | FrozenMetadata = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", _non_empty(self.provider, "provider"))
        object.__setattr__(
            self, "endpoint_role", _non_empty(self.endpoint_role, "endpoint_role")
        )
        object.__setattr__(
            self,
            "endpoint_identity",
            _non_empty(self.endpoint_identity, "endpoint_identity"),
        )
        object.__setattr__(
            self, "served_model", _non_empty(self.served_model, "served_model")
        )
        object.__setattr__(
            self,
            "artifact_reference",
            _non_empty(self.artifact_reference, "artifact_reference"),
        )
        object.__setattr__(
            self,
            "runtime_implementation",
            _non_empty(self.runtime_implementation, "runtime_implementation"),
        )
        object.__setattr__(
            self, "artifact_revision", _optional_text(self.artifact_revision)
        )
        object.__setattr__(
            self,
            "artifact_sha256",
            _normalize_sha256(self.artifact_sha256, "artifact_sha256"),
        )
        object.__setattr__(
            self, "runtime_version", _optional_text(self.runtime_version)
        )
        object.__setattr__(
            self,
            "runtime_image_digest",
            _normalize_sha256(self.runtime_image_digest, "runtime_image_digest"),
        )
        for field_name in (
            "prompt_policy_sha256",
            "tool_policy_sha256",
            "schema_policy_sha256",
            "retrieval_policy_sha256",
        ):
            object.__setattr__(
                self,
                field_name,
                _required_sha256(getattr(self, field_name), field_name),
            )
        for field_name in (
            "sampling_settings",
            "context_settings",
            "hardware_metadata",
        ):
            object.__setattr__(
                self, field_name, freeze_metadata(getattr(self, field_name))
            )

    def payload(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "endpoint_role": self.endpoint_role,
            "endpoint_identity": self.endpoint_identity,
            "served_model": self.served_model,
            "artifact_reference": self.artifact_reference,
            "artifact_revision": self.artifact_revision,
            "artifact_sha256": self.artifact_sha256,
            "runtime_implementation": self.runtime_implementation,
            "runtime_version": self.runtime_version,
            "runtime_image_digest": self.runtime_image_digest,
            "prompt_policy_sha256": self.prompt_policy_sha256,
            "tool_policy_sha256": self.tool_policy_sha256,
            "schema_policy_sha256": self.schema_policy_sha256,
            "retrieval_policy_sha256": self.retrieval_policy_sha256,
            "sampling_settings": _metadata_payload(self.sampling_settings),
            "context_settings": _metadata_payload(self.context_settings),
            "hardware_metadata": _metadata_payload(self.hardware_metadata),
        }

    @property
    def sha256(self) -> str:
        encoded = json.dumps(
            self.payload(), ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @property
    def provenance_complete(self) -> bool:
        """Whether this fingerprint is detailed enough for a production release."""

        return bool(
            (self.artifact_revision or self.artifact_sha256)
            and self.runtime_version
            and self.runtime_image_digest
            and self.sampling_settings
            and self.context_settings
            and self.hardware_metadata
        )


@dataclass(frozen=True)
class Deployment:
    deployment_id: str
    route_aliases: tuple[str, ...]
    roles: tuple[DeploymentRole, ...]
    fingerprint: DeploymentFingerprint
    lifecycle: DeploymentLifecycle = DeploymentLifecycle.DISCOVERED

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "deployment_id", _non_empty(self.deployment_id, "deployment_id")
        )
        aliases = tuple(
            _non_empty(alias, "route alias") for alias in self.route_aliases
        )
        if not aliases:
            raise DeploymentQualificationError("at least one route alias is required")
        if len(set(aliases)) != len(aliases):
            raise DeploymentQualificationError("route aliases must be unique")
        object.__setattr__(self, "route_aliases", aliases)
        roles = tuple(DeploymentRole(role) for role in self.roles)
        if not roles:
            raise DeploymentQualificationError(
                "at least one deployment role is required"
            )
        if len(set(roles)) != len(roles):
            raise DeploymentQualificationError("deployment roles must be unique")
        object.__setattr__(self, "roles", roles)
        object.__setattr__(self, "lifecycle", DeploymentLifecycle(self.lifecycle))


@dataclass(frozen=True)
class QualificationRound:
    deployment_id: str
    role: DeploymentRole
    fingerprint_sha256: str
    sequence: int
    scenario_key: str
    passed: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "deployment_id", _non_empty(self.deployment_id, "deployment_id")
        )
        object.__setattr__(self, "role", DeploymentRole(self.role))
        digest = _required_sha256(self.fingerprint_sha256, "fingerprint_sha256")
        object.__setattr__(self, "fingerprint_sha256", digest.removeprefix("sha256:"))
        if isinstance(self.sequence, bool) or self.sequence < 1:
            raise DeploymentQualificationError("round sequence must be positive")
        if not isinstance(self.passed, bool):
            raise DeploymentQualificationError("round passed must be a boolean")
        object.__setattr__(
            self, "scenario_key", _non_empty(self.scenario_key, "scenario_key")
        )


@dataclass(frozen=True)
class RoleQualification:
    role: DeploymentRole
    observed_rounds: int
    consecutive_passing_rounds: int

    @property
    def qualified(self) -> bool:
        return self.consecutive_passing_rounds >= 3


@dataclass(frozen=True)
class QualificationAssessment:
    deployment_id: str
    fingerprint_sha256: str
    role_results: tuple[RoleQualification, ...]
    stale_round_count: int

    @property
    def qualified(self) -> bool:
        return all(result.qualified for result in self.role_results)


def assess_qualification(
    deployment: Deployment, rounds: Iterable[QualificationRound]
) -> QualificationAssessment:
    """Assess exactly three trailing passes per declared role for this fingerprint."""

    current_digest = deployment.fingerprint.sha256
    relevant = [
        round_ for round_ in rounds if round_.deployment_id == deployment.deployment_id
    ]
    current = [
        round_ for round_ in relevant if round_.fingerprint_sha256 == current_digest
    ]
    stale_round_count = len(relevant) - len(current)
    role_sequences = [(round_.role, round_.sequence) for round_ in current]
    if len(role_sequences) != len(set(role_sequences)):
        raise DeploymentQualificationError(
            "qualification round sequences must be unique per role and fingerprint"
        )
    role_results: list[RoleQualification] = []
    for role in deployment.roles:
        role_rounds = sorted(
            (round_ for round_ in current if round_.role is role),
            key=lambda round_: round_.sequence,
        )
        consecutive = 0
        for round_ in reversed(role_rounds):
            if not round_.passed:
                break
            consecutive += 1
        role_results.append(
            RoleQualification(
                role=role,
                observed_rounds=len(role_rounds),
                consecutive_passing_rounds=consecutive,
            )
        )
    return QualificationAssessment(
        deployment_id=deployment.deployment_id,
        fingerprint_sha256=current_digest,
        role_results=tuple(role_results),
        stale_round_count=stale_round_count,
    )


def apply_qualification(
    deployment: Deployment, rounds: Iterable[QualificationRound]
) -> Deployment:
    """Promote only complete, non-deprecated deployments with three passes/role."""

    if deployment.lifecycle is DeploymentLifecycle.DEPRECATED:
        return deployment
    assessment = assess_qualification(deployment, rounds)
    lifecycle = (
        DeploymentLifecycle.QUALIFIED
        if assessment.qualified and deployment.fingerprint.provenance_complete
        else DeploymentLifecycle.CANDIDATE
    )
    return replace(deployment, lifecycle=lifecycle)


def replace_fingerprint(
    deployment: Deployment, fingerprint: DeploymentFingerprint
) -> Deployment:
    """Reset lifecycle deterministically whenever any fingerprint input changes."""

    if deployment.fingerprint.sha256 == fingerprint.sha256:
        return deployment
    if deployment.lifecycle is DeploymentLifecycle.DEPRECATED:
        return replace(deployment, fingerprint=fingerprint)
    return replace(
        deployment,
        fingerprint=fingerprint,
        lifecycle=DeploymentLifecycle.DISCOVERED,
    )


@dataclass(frozen=True)
class ReleaseDecision:
    allowed: bool
    reason: str
    override_used: bool = False


def release_gate(
    deployment: Deployment,
    *,
    target: ReleaseTarget,
    assessment: QualificationAssessment | None = None,
    allow_study_development_override: bool = False,
) -> ReleaseDecision:
    """Fail closed for release; study/development bypasses require explicit intent."""

    target = ReleaseTarget(target)
    if deployment.lifecycle is DeploymentLifecycle.DEPRECATED:
        return ReleaseDecision(False, "deprecated deployments cannot be released")
    if (
        assessment is not None
        and assessment.deployment_id == deployment.deployment_id
        and assessment.fingerprint_sha256 == deployment.fingerprint.sha256
        and assessment.qualified
        and deployment.lifecycle is DeploymentLifecycle.QUALIFIED
        and deployment.fingerprint.provenance_complete
    ):
        return ReleaseDecision(True, "qualified deployment fingerprint")
    if (
        target in {ReleaseTarget.STUDY, ReleaseTarget.DEVELOPMENT}
        and allow_study_development_override
    ):
        return ReleaseDecision(
            True,
            "explicit study/development override for an unqualified fingerprint",
            override_used=True,
        )
    return ReleaseDecision(
        False,
        "release requires current qualification, complete provenance, and three passing rounds per role",
    )
