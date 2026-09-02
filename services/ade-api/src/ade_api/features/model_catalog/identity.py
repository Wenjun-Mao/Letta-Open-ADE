from __future__ import annotations

import hashlib
import json
from typing import Any


_IDENTITY_FIELDS = (
    "key",
    "source_id",
    "provider_model_id",
    "upstream_provider_model_id",
    "sampling_defaults",
    "scenario_sampling_defaults",
    "supports_top_k",
    "supports_thinking",
    "thinking_default_enabled",
    "tool_call_thinking_default_enabled",
    "profile_applied",
    "profile_source",
    "agent_studio_candidate",
    "agent_studio_compatible",
    "deployment",
)

_IDENTITY_MAPPING_FIELDS = (
    "sampling_defaults",
    "scenario_sampling_defaults",
)


def model_option_identity_payload(option: dict[str, Any]) -> dict[str, Any]:
    """Keep only execution-relevant catalog fields in a canonical identity."""

    payload = {field: option.get(field) for field in _IDENTITY_FIELDS}
    # The public response contract serializes omitted sampling maps as empty maps.
    # Hash the same representation clients receive so the digest is verifiable.
    for field in _IDENTITY_MAPPING_FIELDS:
        if not isinstance(payload[field], dict):
            payload[field] = {}
    return payload


def model_option_identity_sha256(option: dict[str, Any]) -> str:
    payload = json.dumps(
        model_option_identity_payload(option),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def attach_model_option_identity(option: dict[str, Any]) -> dict[str, Any]:
    option["identity_sha256"] = model_option_identity_sha256(option)
    return option
