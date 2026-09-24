"""Resolve immutable deployment snapshots and their request limits."""

from __future__ import annotations

from typing import Any

from .errors import RuntimeValidationError


def required_deployment(
    deployments: dict[str, dict[str, Any]], role: str
) -> dict[str, Any]:
    try:
        return deployments[role]
    except KeyError as exc:
        raise RuntimeValidationError(
            f"Agent definition has no {role} deployment snapshot"
        ) from exc


def deployment_adapter(catalog: dict[str, Any], deployment: dict[str, Any]) -> str:
    route_alias = str(deployment.get("route_alias") or "")
    items = catalog.get("items")
    if not isinstance(items, list):
        raise RuntimeValidationError("Model Router catalog did not contain items")
    matches = [
        item
        for item in items
        if isinstance(item, dict)
        and (
            route_alias
            == str(item.get("model_key") or item.get("router_model_id") or "")
            or (
                isinstance(item.get("route_aliases"), list)
                and route_alias in item["route_aliases"]
            )
        )
    ]
    if len(matches) != 1 or not str(matches[0].get("source_adapter") or ""):
        raise RuntimeValidationError("Bound deployment has no unique provider adapter")
    return str(matches[0]["source_adapter"])


def max_model_requests(deployment: dict[str, Any]) -> int:
    context = dict(deployment.get("fingerprint_payload", {})).get(
        "context_settings", {}
    )
    if not isinstance(context, dict):
        return 6
    return max(1, min(8, int(context.get("max_model_requests") or 6)))


def reviewer_max_model_requests(deployment: dict[str, Any]) -> int:
    fingerprint = deployment.get("fingerprint_payload")
    context = (
        fingerprint.get("context_settings") if isinstance(fingerprint, dict) else None
    )
    repair_count = (
        context.get("reviewer_repair_count", 1) if isinstance(context, dict) else 1
    )
    if type(repair_count) is not int or repair_count not in {0, 1}:
        raise RuntimeValidationError("Reviewer repair budget must be zero or one")
    return 1 + repair_count


def embedding_dimensions(deployment: dict[str, Any]) -> int:
    sampling = dict(deployment.get("fingerprint_payload", {})).get(
        "sampling_settings", {}
    )
    if not isinstance(sampling, dict):
        return 0
    return max(0, int(sampling.get("dimensions") or 0))
