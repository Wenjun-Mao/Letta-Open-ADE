"""Versioned, alias-safe deployment metadata for routed model catalogs."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ROLES = frozenset({"conversation", "reviewer", "retriever"})
_LIFECYCLES = frozenset({"discovered", "candidate", "qualified", "deprecated"})
_FINGERPRINT_TEXT_FIELDS = (
    "provider",
    "endpoint_role",
    "endpoint_identity",
    "served_model",
    "artifact_reference",
    "runtime_implementation",
)
_FINGERPRINT_OPTIONAL_TEXT_FIELDS = (
    "artifact_revision",
    "artifact_sha256",
    "runtime_version",
    "runtime_image_digest",
)
_FINGERPRINT_DIGEST_FIELDS = (
    "prompt_policy_sha256",
    "tool_policy_sha256",
    "schema_policy_sha256",
    "retrieval_policy_sha256",
)
_FINGERPRINT_MAPPING_FIELDS = (
    "sampling_settings",
    "context_settings",
    "hardware_metadata",
)
_FINGERPRINT_FIELDS = frozenset(
    (
        *_FINGERPRINT_TEXT_FIELDS,
        *_FINGERPRINT_OPTIONAL_TEXT_FIELDS,
        *_FINGERPRINT_DIGEST_FIELDS,
        *_FINGERPRINT_MAPPING_FIELDS,
    )
)


class DeploymentManifestError(ValueError):
    """Raised when checked-in deployment metadata cannot be trusted."""


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DeploymentManifestError(f"{label} must be an object")
    return value


def _required_text(value: object, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise DeploymentManifestError(f"{label} is required")
    return normalized


def _optional_text(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _normalized_digest(value: object, label: str) -> str:
    normalized = _required_text(value, label).removeprefix("sha256:")
    if not _SHA256_RE.fullmatch(normalized):
        raise DeploymentManifestError(f"{label} must be a SHA-256 digest")
    return normalized


def _normalized_json(value: object, label: str) -> Any:
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise DeploymentManifestError(f"{label} must contain finite JSON values")
        return value
    if isinstance(value, list):
        return [
            _normalized_json(item, f"{label}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for raw_key, nested in value.items():
            key = _required_text(raw_key, f"{label} key")
            if key in normalized:
                raise DeploymentManifestError(f"duplicate {label} key: {key}")
            normalized[key] = _normalized_json(nested, f"{label}.{key}")
        return normalized
    raise DeploymentManifestError(
        f"{label} must contain JSON-compatible values, not {type(value).__name__}"
    )


def _normalized_object(value: object, label: str) -> dict[str, Any]:
    normalized = _normalized_json(value, label)
    if not isinstance(normalized, dict):
        raise DeploymentManifestError(f"{label} must be an object")
    return normalized


def _validate_known_fields(
    payload: Mapping[str, object], *, label: str, expected: frozenset[str]
) -> None:
    unexpected = sorted(set(payload) - expected)
    missing = sorted(expected - set(payload))
    if unexpected:
        raise DeploymentManifestError(
            f"{label} includes unsupported fields: {', '.join(unexpected)}"
        )
    if missing:
        raise DeploymentManifestError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )


@dataclass(frozen=True)
class DeploymentFingerprint:
    provider: str
    endpoint_role: str
    endpoint_identity: str
    served_model: str
    artifact_reference: str
    artifact_revision: str | None
    artifact_sha256: str | None
    runtime_implementation: str
    runtime_version: str | None
    runtime_image_digest: str | None
    prompt_policy_sha256: str
    tool_policy_sha256: str
    schema_policy_sha256: str
    retrieval_policy_sha256: str
    sampling_settings: dict[str, Any]
    context_settings: dict[str, Any]
    hardware_metadata: dict[str, Any]

    @classmethod
    def from_payload(cls, value: object) -> "DeploymentFingerprint":
        payload = _require_mapping(value, "deployment fingerprint")
        _validate_known_fields(
            payload,
            label="deployment fingerprint",
            expected=_FINGERPRINT_FIELDS,
        )
        optional_digests = {
            "artifact_sha256",
            "runtime_image_digest",
        }
        optional_values = {
            field: _optional_text(payload[field])
            for field in _FINGERPRINT_OPTIONAL_TEXT_FIELDS
        }
        for field in optional_digests:
            value = optional_values[field]
            optional_values[field] = (
                _normalized_digest(value, field) if value is not None else None
            )
        return cls(
            **{
                field: _required_text(payload[field], field)
                for field in _FINGERPRINT_TEXT_FIELDS
            },
            artifact_revision=optional_values["artifact_revision"],
            artifact_sha256=optional_values["artifact_sha256"],
            runtime_version=optional_values["runtime_version"],
            runtime_image_digest=optional_values["runtime_image_digest"],
            **{
                field: _normalized_digest(payload[field], field)
                for field in _FINGERPRINT_DIGEST_FIELDS
            },
            **{
                field: _normalized_object(payload[field], field)
                for field in _FINGERPRINT_MAPPING_FIELDS
            },
        )

    def as_dict(self) -> dict[str, Any]:
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
            "sampling_settings": self.sampling_settings,
            "context_settings": self.context_settings,
            "hardware_metadata": self.hardware_metadata,
        }

    @property
    def sha256(self) -> str:
        encoded = json.dumps(
            self.as_dict(), ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class DeploymentRoleQualification:
    role: str
    observed_rounds: int
    consecutive_passing_rounds: int
    qualified: bool

    @classmethod
    def from_payload(cls, value: object) -> "DeploymentRoleQualification":
        payload = _require_mapping(value, "qualification role result")
        _validate_known_fields(
            payload,
            label="qualification role result",
            expected=frozenset(
                {
                    "role",
                    "observed_rounds",
                    "consecutive_passing_rounds",
                    "qualified",
                }
            ),
        )
        role = _required_text(payload["role"], "qualification role")
        if role not in _ROLES:
            raise DeploymentManifestError(f"unsupported deployment role: {role}")
        observed_rounds = payload["observed_rounds"]
        consecutive = payload["consecutive_passing_rounds"]
        qualified = payload["qualified"]
        if (
            isinstance(observed_rounds, bool)
            or not isinstance(observed_rounds, int)
            or observed_rounds < 0
        ):
            raise DeploymentManifestError(
                "observed_rounds must be a non-negative integer"
            )
        if (
            isinstance(consecutive, bool)
            or not isinstance(consecutive, int)
            or consecutive < 0
            or consecutive > observed_rounds
        ):
            raise DeploymentManifestError(
                "consecutive_passing_rounds must be between zero and observed_rounds"
            )
        if not isinstance(qualified, bool) or qualified != (consecutive >= 3):
            raise DeploymentManifestError(
                "qualification role result must reflect three consecutive passing rounds"
            )
        return cls(
            role=role,
            observed_rounds=observed_rounds,
            consecutive_passing_rounds=consecutive,
            qualified=qualified,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "observed_rounds": self.observed_rounds,
            "consecutive_passing_rounds": self.consecutive_passing_rounds,
            "qualified": self.qualified,
        }


@dataclass(frozen=True)
class DeploymentQualificationSummary:
    fingerprint_sha256: str
    qualified: bool
    stale_round_count: int
    role_results: tuple[DeploymentRoleQualification, ...]

    @classmethod
    def from_payload(cls, value: object) -> "DeploymentQualificationSummary":
        payload = _require_mapping(value, "deployment qualification")
        _validate_known_fields(
            payload,
            label="deployment qualification",
            expected=frozenset(
                {
                    "fingerprint_sha256",
                    "qualified",
                    "stale_round_count",
                    "role_results",
                }
            ),
        )
        stale_round_count = payload["stale_round_count"]
        raw_results = payload["role_results"]
        if (
            isinstance(stale_round_count, bool)
            or not isinstance(stale_round_count, int)
            or stale_round_count < 0
        ):
            raise DeploymentManifestError(
                "stale_round_count must be a non-negative integer"
            )
        if not isinstance(raw_results, list) or not raw_results:
            raise DeploymentManifestError("role_results must be a non-empty list")
        role_results = tuple(
            DeploymentRoleQualification.from_payload(item) for item in raw_results
        )
        roles = [item.role for item in role_results]
        if len(roles) != len(set(roles)):
            raise DeploymentManifestError("qualification role results must be unique")
        qualified = payload["qualified"]
        if not isinstance(qualified, bool) or qualified != all(
            item.qualified for item in role_results
        ):
            raise DeploymentManifestError(
                "qualification summary must agree with its role results"
            )
        return cls(
            fingerprint_sha256=_normalized_digest(
                payload["fingerprint_sha256"], "qualification fingerprint_sha256"
            ),
            qualified=qualified,
            stale_round_count=stale_round_count,
            role_results=role_results,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "fingerprint_sha256": self.fingerprint_sha256,
            "qualified": self.qualified,
            "stale_round_count": self.stale_round_count,
            "role_results": [item.as_dict() for item in self.role_results],
        }


@dataclass(frozen=True)
class DeploymentManifestEntry:
    deployment_id: str
    route_aliases: tuple[str, ...]
    roles: tuple[str, ...]
    lifecycle: str
    fingerprint: DeploymentFingerprint
    qualification: DeploymentQualificationSummary

    @classmethod
    def from_payload(cls, value: object) -> "DeploymentManifestEntry":
        payload = _require_mapping(value, "deployment")
        _validate_known_fields(
            payload,
            label="deployment",
            expected=frozenset(
                {
                    "id",
                    "route_aliases",
                    "roles",
                    "lifecycle",
                    "fingerprint",
                    "qualification",
                }
            ),
        )
        raw_aliases = payload["route_aliases"]
        raw_roles = payload["roles"]
        if not isinstance(raw_aliases, list) or not raw_aliases:
            raise DeploymentManifestError("route_aliases must be a non-empty list")
        if not isinstance(raw_roles, list) or not raw_roles:
            raise DeploymentManifestError("roles must be a non-empty list")
        aliases = tuple(_required_text(item, "route alias") for item in raw_aliases)
        roles = tuple(_required_text(item, "deployment role") for item in raw_roles)
        if len(aliases) != len(set(aliases)):
            raise DeploymentManifestError("route aliases must be unique")
        if len(roles) != len(set(roles)) or any(role not in _ROLES for role in roles):
            raise DeploymentManifestError(
                "deployment roles must be unique supported roles"
            )
        lifecycle = _required_text(payload["lifecycle"], "deployment lifecycle")
        if lifecycle not in _LIFECYCLES:
            raise DeploymentManifestError(
                f"unsupported deployment lifecycle: {lifecycle}"
            )
        fingerprint = DeploymentFingerprint.from_payload(payload["fingerprint"])
        qualification = DeploymentQualificationSummary.from_payload(
            payload["qualification"]
        )
        if qualification.fingerprint_sha256 != fingerprint.sha256:
            raise DeploymentManifestError(
                "qualification fingerprint_sha256 must match the exact fingerprint"
            )
        summary_roles = tuple(item.role for item in qualification.role_results)
        if set(summary_roles) != set(roles):
            raise DeploymentManifestError(
                "qualification role results must match declared deployment roles"
            )
        if lifecycle == "qualified" and not qualification.qualified:
            raise DeploymentManifestError(
                "qualified lifecycle requires a qualified role summary"
            )
        return cls(
            deployment_id=_required_text(payload["id"], "deployment id"),
            route_aliases=aliases,
            roles=roles,
            lifecycle=lifecycle,
            fingerprint=fingerprint,
            qualification=qualification,
        )

    def as_catalog_dict(self) -> dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "roles": list(self.roles),
            "lifecycle": self.lifecycle,
            "fingerprint": {
                **self.fingerprint.as_dict(),
                "sha256": self.fingerprint.sha256,
            },
            "qualification": self.qualification.as_dict(),
        }


@dataclass(frozen=True)
class DeploymentManifest:
    schema_version: int
    deployments: tuple[DeploymentManifestEntry, ...]

    @classmethod
    def empty(cls) -> "DeploymentManifest":
        return cls(schema_version=1, deployments=())

    @classmethod
    def from_payload(cls, value: object) -> "DeploymentManifest":
        payload = _require_mapping(value, "deployment manifest")
        _validate_known_fields(
            payload,
            label="deployment manifest",
            expected=frozenset({"schema_version", "deployments"}),
        )
        if payload["schema_version"] != 1:
            raise DeploymentManifestError(
                "unsupported deployment manifest schema_version"
            )
        raw_deployments = payload["deployments"]
        if not isinstance(raw_deployments, list) or not raw_deployments:
            raise DeploymentManifestError("deployments must be a non-empty list")
        deployments = tuple(
            DeploymentManifestEntry.from_payload(item) for item in raw_deployments
        )
        deployment_ids = [deployment.deployment_id for deployment in deployments]
        aliases = [
            alias for deployment in deployments for alias in deployment.route_aliases
        ]
        if len(deployment_ids) != len(set(deployment_ids)):
            raise DeploymentManifestError("deployment ids must be unique")
        if len(aliases) != len(set(aliases)):
            raise DeploymentManifestError(
                "route aliases must be unique across deployments"
            )
        return cls(schema_version=1, deployments=deployments)

    def for_route_alias(self, router_model_id: str) -> DeploymentManifestEntry | None:
        return next(
            (
                deployment
                for deployment in self.deployments
                if router_model_id in deployment.route_aliases
            ),
            None,
        )


def load_deployment_manifest(
    path_value: str | Path,
    *,
    project_root: Path | None = None,
) -> DeploymentManifest:
    path = Path(path_value)
    if not path.is_absolute():
        root = Path(project_root or os.getenv("ADE_REPOSITORY_ROOT") or Path.cwd())
        path = root / path
    if not path.is_file():
        return DeploymentManifest.empty()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeploymentManifestError(
            f"deployment manifest could not be read: {path}"
        ) from exc
    return DeploymentManifest.from_payload(payload)
