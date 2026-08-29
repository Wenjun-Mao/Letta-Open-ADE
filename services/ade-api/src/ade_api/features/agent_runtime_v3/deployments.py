from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .contracts import QualificationState
from .errors import RuntimeValidationError, UnqualifiedDeployment


DeploymentRole = Literal["conversation", "reviewer", "retriever"]


@dataclass(frozen=True)
class ResolvedDeployment:
    deployment_id: str
    route_alias: str
    fingerprint: str
    role: DeploymentRole
    lifecycle: str
    qualification_state: QualificationState
    fingerprint_payload: dict[str, Any]

    def as_snapshot(self) -> dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "route_alias": self.route_alias,
            "fingerprint": self.fingerprint,
            "role": self.role,
            "lifecycle": self.lifecycle,
            "qualification_state": self.qualification_state.value,
            "fingerprint_payload": dict(self.fingerprint_payload),
        }


def resolve_deployment(
    catalog: dict[str, Any],
    *,
    route_alias: str,
    role: DeploymentRole,
    mode: Literal["release", "development"],
) -> ResolvedDeployment:
    items = catalog.get("items")
    if not isinstance(items, list):
        raise RuntimeValidationError("Model Router catalog did not contain items")
    raw_item = next(
        (
            item
            for item in items
            if isinstance(item, dict)
            and str(item.get("model_key") or item.get("router_model_id") or "")
            == route_alias
        ),
        None,
    )
    if raw_item is None:
        raise RuntimeValidationError(
            f"Router deployment alias is unavailable: {route_alias}"
        )
    deployment = raw_item.get("deployment")
    if not isinstance(deployment, dict):
        raise RuntimeValidationError(
            f"Router alias has no immutable deployment record: {route_alias}"
        )
    roles = deployment.get("roles")
    if not isinstance(roles, list) or role not in roles:
        raise RuntimeValidationError(
            f"Router deployment '{deployment.get('deployment_id')}' does not support {role}"
        )
    fingerprint = deployment.get("fingerprint")
    qualification = deployment.get("qualification")
    if not isinstance(fingerprint, dict) or not isinstance(qualification, dict):
        raise RuntimeValidationError("Router deployment metadata is incomplete")
    role_results = qualification.get("role_results")
    role_result = next(
        (
            item
            for item in role_results or []
            if isinstance(item, dict) and item.get("role") == role
        ),
        None,
    )
    qualified = bool(role_result and role_result.get("qualified"))
    if mode == "release" and not qualified:
        raise UnqualifiedDeployment(
            f"Deployment '{deployment.get('deployment_id')}' is not qualified for {role}"
        )
    return ResolvedDeployment(
        deployment_id=str(deployment.get("deployment_id", "")),
        route_alias=route_alias,
        fingerprint=str(fingerprint.get("sha256", "")),
        role=role,
        lifecycle=str(deployment.get("lifecycle", "")),
        qualification_state=(
            QualificationState.QUALIFIED
            if qualified
            else QualificationState.UNQUALIFIED
        ),
        fingerprint_payload=dict(fingerprint),
    )
