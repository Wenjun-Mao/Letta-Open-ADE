from __future__ import annotations

from typing import Any

from ade_api.integrations.model_router.client import ModelRouterClient

from .catalog import router_catalog_items


def resolve_comment_model_selection(
    *,
    model_key: str | None = None,
    model_router_client: ModelRouterClient,
    force_refresh: bool = False,
) -> dict[str, Any]:
    items = [
        item
        for item in router_catalog_items(
            model_router_client=model_router_client,
            force_refresh=force_refresh,
        )
        if item["comment_lab_available"]
    ]
    router_api_key = model_router_client.api_key()
    requested_key = str(model_key or "").strip()
    if requested_key:
        matched = next(
            (item for item in items if item["model_key"] == requested_key), None
        )
        if matched:
            return {**matched, "api_key": router_api_key}
        raise ValueError(f"Invalid model_key: {requested_key}")

    raise ValueError("model_key is required")


def resolve_label_model_selection(
    *,
    model_key: str,
    model_router_client: ModelRouterClient,
    force_refresh: bool = False,
) -> dict[str, Any]:
    items = [
        item
        for item in router_catalog_items(
            model_router_client=model_router_client,
            force_refresh=force_refresh,
        )
        if item["label_lab_available"]
    ]
    requested_key = str(model_key or "").strip()
    if not requested_key:
        raise ValueError("model_key is required")

    matched = next((item for item in items if item["model_key"] == requested_key), None)
    if matched is None:
        raise ValueError(f"Invalid model_key: {requested_key}")
    return {**matched, "api_key": model_router_client.api_key()}
