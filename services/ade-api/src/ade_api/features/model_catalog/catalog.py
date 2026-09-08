from __future__ import annotations

from typing import Any

from ade_api.integrations.model_router.client import ModelRouterClient


def router_catalog_items(
    *,
    model_router_client: ModelRouterClient,
    force_refresh: bool = False,
) -> list[dict[str, Any]]:
    payload = model_router_client.catalog(force_refresh=force_refresh)
    return _catalog_items_from_payload(
        payload,
        router_base_url=model_router_client.v1_base_url(),
    )


def _catalog_items_from_payload(
    payload: dict[str, Any], *, router_base_url: str
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw_item in payload.get("items", []):
        if not isinstance(raw_item, dict):
            continue
        model_key = str(
            raw_item.get("model_key") or raw_item.get("router_model_id") or ""
        ).strip()
        provider_model_id = str(raw_item.get("provider_model_id", "") or "").strip()
        if not model_key:
            continue
        is_embedding = str(raw_item.get("model_type", "") or "").strip() == "embedding"
        module_visibility = [
            str(item or "").strip()
            for item in raw_item.get("module_visibility", [])
            if str(item or "").strip()
        ]
        items.append(
            {
                "model_key": model_key,
                "source_id": str(raw_item.get("source_id", "") or ""),
                "source_label": str(raw_item.get("source_label", "") or ""),
                "source_kind": str(
                    raw_item.get("source_kind", "") or "openai-compatible"
                ),
                "source_adapter": str(
                    raw_item.get("source_adapter", "") or "generic_openai"
                ),
                "base_url": router_base_url,
                "source_base_url": str(raw_item.get("source_base_url", "") or ""),
                "enabled_for": module_visibility,
                "module_visibility": module_visibility,
                "provider_model_id": provider_model_id,
                "model_type": str(raw_item.get("model_type", "") or "unknown"),
                "agent_studio_available": (not is_embedding)
                and bool(raw_item.get("agent_studio_available", False)),
                "comment_lab_available": (not is_embedding)
                and bool(raw_item.get("comment_lab_available", False)),
                "label_lab_available": (not is_embedding)
                and bool(raw_item.get("label_lab_available", False)),
                "structured_output_mode": raw_item.get("structured_output_mode"),
                "sampling_defaults": raw_item.get("sampling_defaults")
                if isinstance(raw_item.get("sampling_defaults"), dict)
                else {},
                "scenario_sampling_defaults": (
                    raw_item.get("scenario_sampling_defaults")
                    if isinstance(raw_item.get("scenario_sampling_defaults"), dict)
                    else {}
                ),
                "supports_top_k": bool(raw_item.get("supports_top_k", False)),
                "supports_thinking": bool(raw_item.get("supports_thinking", False)),
                "thinking_default_enabled": bool(
                    raw_item.get("thinking_default_enabled", False)
                ),
                "tool_call_thinking_default_enabled": (
                    raw_item.get("tool_call_thinking_default_enabled")
                    if isinstance(
                        raw_item.get("tool_call_thinking_default_enabled"), bool
                    )
                    else None
                ),
                "profile_applied": bool(raw_item.get("profile_applied", False)),
                "profile_source": str(raw_item.get("profile_source", "") or ""),
                "agent_studio_candidate": bool(
                    raw_item.get("agent_studio_candidate", False)
                ),
                "agent_studio_compatible": bool(
                    raw_item.get("agent_studio_compatible", True)
                ),
                "deployment": (
                    dict(raw_item["deployment"])
                    if isinstance(raw_item.get("deployment"), dict)
                    else None
                ),
            }
        )
    return items


def model_catalog(
    *,
    model_router_client: ModelRouterClient,
    force_refresh: bool = False,
) -> dict[str, Any]:
    payload = model_router_client.catalog(force_refresh=force_refresh)
    sources: list[dict[str, Any]] = []
    for raw_source in payload.get("sources", []):
        if not isinstance(raw_source, dict):
            continue
        normalized_source = dict(raw_source)
        module_visibility = normalized_source.get("module_visibility", [])
        normalized_source["enabled_for"] = (
            list(module_visibility) if isinstance(module_visibility, list) else []
        )
        sources.append(normalized_source)
    return {
        "generated_at": payload.get("generated_at"),
        "sources": sources,
        "items": _catalog_items_from_payload(
            payload,
            router_base_url=model_router_client.v1_base_url(),
        ),
        "router": {
            "enabled": True,
            "base_url": model_router_client.v1_base_url(),
        },
    }
