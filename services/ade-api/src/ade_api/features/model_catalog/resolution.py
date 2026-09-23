from __future__ import annotations

from typing import Any

from ade_api.integrations.model_router.client import ModelRouterClient
from ade_api.platform.contracts import ScenarioType

from .catalog import router_catalog_items
from .defaults import (
    PROVIDER_MODEL_OPTION_OVERRIDES,
    PROVIDER_MODEL_OPTION_PRIORITY,
)
from .identity import attach_model_option_identity
from .utils import dedupe_options


def model_option_metadata(item: dict[str, Any]) -> tuple[str, str]:
    provider_model_id = str(item.get("provider_model_id", "") or "").strip()
    override = PROVIDER_MODEL_OPTION_OVERRIDES.get(provider_model_id)
    if override:
        return override["label"], override["description"]
    source_label = str(item.get("source_label", "") or "").strip()
    display_model_id = provider_model_id or str(item.get("model_key", "") or "").strip()
    return display_model_id, f"Discovered from {source_label}."


def embedding_options(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for item in items:
        if item.get("model_type") != "embedding":
            continue
        key = str(item.get("model_key", "") or "").strip()
        if not key:
            continue
        label, description = model_option_metadata(item)
        options.append(
            attach_model_option_identity(
                {
                    "key": key,
                    "label": label,
                    "description": description,
                    "available": True,
                    "source_id": item["source_id"],
                    "source_label": item["source_label"],
                    "source_adapter": item.get("source_adapter", "generic_openai"),
                    "provider_model_id": item["provider_model_id"],
                }
            )
        )
    return dedupe_options(options)


def model_option_sort_key(option: dict[str, Any]) -> tuple[int, int, str, str]:
    key = str(option.get("key", "") or "").strip()
    provider_model_id = str(option.get("provider_model_id", "") or "").strip()
    preferred_rank = PROVIDER_MODEL_OPTION_PRIORITY.get(provider_model_id)
    if preferred_rank is not None:
        return (0, int(preferred_rank), key.lower(), provider_model_id.lower())
    return (1, 0, key.lower(), provider_model_id.lower())


def runtime_options(
    scenario: ScenarioType = "chat",
    *,
    model_router_client: ModelRouterClient,
    force_refresh: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items = router_catalog_items(
        model_router_client=model_router_client,
        force_refresh=force_refresh,
    )
    model_options: list[dict[str, Any]] = []
    seen_model_keys: set[str] = set()

    availability_key = {
        "chat": "agent_studio_available",
        "comment": "comment_lab_available",
        "label": "label_lab_available",
    }[scenario]

    for item in items:
        if not item[availability_key]:
            continue
        key = str(item.get("model_key", "") or "").strip()
        if not key or key in seen_model_keys:
            continue
        seen_model_keys.add(key)
        label, description = model_option_metadata(item)
        model_options.append(
            attach_model_option_identity(
                {
                    "key": key,
                    "label": label,
                    "description": description,
                    "available": True,
                    "source_id": item["source_id"],
                    "source_label": item["source_label"],
                    "provider_model_id": item["provider_model_id"],
                    "label_lab_available": item["label_lab_available"],
                    "structured_output_mode": item["structured_output_mode"],
                    "sampling_defaults": item.get("sampling_defaults", {}),
                    "scenario_sampling_defaults": item.get(
                        "scenario_sampling_defaults", {}
                    ),
                    "supports_top_k": item.get("supports_top_k", False),
                    "supports_thinking": item.get("supports_thinking", False),
                    "thinking_default_enabled": item.get(
                        "thinking_default_enabled", False
                    ),
                    "tool_call_thinking_default_enabled": item.get(
                        "tool_call_thinking_default_enabled"
                    ),
                    "profile_applied": item.get("profile_applied", False),
                    "profile_source": item.get("profile_source", ""),
                    "agent_studio_candidate": item.get("agent_studio_candidate", False),
                    "agent_studio_compatible": item.get(
                        "agent_studio_compatible", True
                    ),
                    "deployment": item.get("deployment"),
                }
            )
        )

    if scenario == "chat":
        model_options.sort(key=model_option_sort_key)
    return model_options, embedding_options(items)
