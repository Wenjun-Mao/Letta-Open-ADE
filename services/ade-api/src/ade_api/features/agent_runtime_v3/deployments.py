from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any, Literal

from .contracts import QualificationState
from .errors import RuntimeValidationError, UnqualifiedDeployment
from .release_policy import fingerprint_policy_hashes


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
    expected_policy_hashes: Mapping[str, str] | None = None,
    source_clean: bool | None = None,
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
    if mode == "release":
        _validate_release_qualification(
            deployment,
            qualification=qualification,
            fingerprint=fingerprint,
            role=role,
            role_result=role_result,
            expected_policy_hashes=expected_policy_hashes,
            source_clean=source_clean,
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


def validate_definition_execution(
    definition: dict[str, Any],
    catalog: dict[str, Any],
    *,
    mode: Literal["release", "development"],
    expected_policy_hashes: Mapping[str, str] | None = None,
    expected_route_aliases: Mapping[str, str] | None = None,
    source_clean: bool | None = None,
) -> None:
    if mode == "release":
        if definition.get("qualification_state") != "qualified":
            raise UnqualifiedDeployment(
                "Release mode cannot execute an unqualified agent definition"
            )
        if "get_weather" in definition.get("tool_names", []):
            raise RuntimeValidationError(
                "get_weather is unavailable when the runtime is in release mode"
            )
    snapshots = definition.get("deployment_snapshot")
    if not isinstance(snapshots, list):
        raise RuntimeValidationError("Agent definition deployment snapshot is invalid")
    by_role = {
        str(snapshot.get("role")): snapshot
        for snapshot in snapshots
        if isinstance(snapshot, dict)
    }
    expected_roles = {"conversation", "reviewer", "retriever"}
    if set(by_role) != expected_roles:
        raise RuntimeValidationError(
            "Agent definition must bind conversation, reviewer, and retriever deployments"
        )
    roles: tuple[DeploymentRole, ...] = (
        "conversation",
        "reviewer",
        "retriever",
    )
    for role in roles:
        stored = by_role[role]
        if mode == "release" and (
            expected_route_aliases is None
            or str(stored.get("route_alias") or "") != expected_route_aliases.get(role)
        ):
            raise UnqualifiedDeployment(
                f"Agent definition {role} route is outside the qualified Agent Studio contract"
            )
        current = resolve_deployment(
            catalog,
            route_alias=str(stored.get("route_alias") or ""),
            role=role,
            mode=mode,
            expected_policy_hashes=expected_policy_hashes,
            source_clean=source_clean,
        )
        if (
            current.deployment_id != str(stored.get("deployment_id") or "")
            or current.fingerprint != str(stored.get("fingerprint") or "")
            or current.fingerprint_payload != stored.get("fingerprint_payload")
        ):
            raise UnqualifiedDeployment(
                f"Agent definition {role} deployment fingerprint is stale"
            )


def _validate_release_qualification(
    deployment: dict[str, Any],
    *,
    qualification: dict[str, Any],
    fingerprint: dict[str, Any],
    role: DeploymentRole,
    role_result: dict[str, Any] | None,
    expected_policy_hashes: Mapping[str, str] | None,
    source_clean: bool | None,
) -> None:
    if source_clean is not True:
        raise UnqualifiedDeployment("Release mode requires a clean source tree")
    if (
        deployment.get("lifecycle") != "qualified"
        or qualification.get("qualified") is not True
        or qualification.get("stale_round_count") != 0
        or role_result is None
        or role_result.get("qualified") is not True
        or int(role_result.get("observed_rounds") or 0) < 3
        or int(role_result.get("consecutive_passing_rounds") or 0) < 3
    ):
        raise UnqualifiedDeployment(
            f"Deployment '{deployment.get('deployment_id')}' is not qualified for {role}"
        )
    if expected_policy_hashes is None or fingerprint_policy_hashes(fingerprint) != dict(
        expected_policy_hashes
    ):
        raise UnqualifiedDeployment(
            f"Deployment '{deployment.get('deployment_id')}' uses stale runtime policy"
        )


def definition_deployment(
    definition: dict[str, Any], role: DeploymentRole
) -> dict[str, Any]:
    for snapshot in definition.get("deployment_snapshot", []):
        if isinstance(snapshot, dict) and snapshot.get("role") == role:
            return snapshot
    raise RuntimeValidationError(f"Agent definition has no {role} deployment snapshot")
