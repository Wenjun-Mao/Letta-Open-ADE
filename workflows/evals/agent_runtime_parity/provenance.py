from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from scripts.source_fingerprint import source_fingerprint

from .config import PROJECT_ROOT, ParityConfig, router_model_key
from .scoring import ConversationFixture, fixture_payload


OPTION_IDENTITY_FIELDS = (
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


async def capture_legacy_inputs(api: Any, config: ParityConfig) -> dict[str, Any]:
    options, prompt, persona = await asyncio.gather(
        api.options(),
        api.template("prompt", config.prompt_key),
        api.template("persona", config.persona_key),
    )
    return {
        "model": _option_snapshot(
            _selected_option(options.get("models"), config.legacy_model)
        ),
        "embedding": _option_snapshot(
            _selected_option(options.get("embeddings"), config.legacy_embedding)
        ),
        "prompt": _template_snapshot(prompt, "prompt", config.prompt_key),
        "persona": _template_snapshot(persona, "persona", config.persona_key),
    }


def build_parity_spec(
    *, config: ParityConfig, fixture: ConversationFixture, run_id: str
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "agent-runtime-parity-spec",
        "run_id": run_id,
        "shared_product_contract": {
            "native_product_api": "/api/v3/agent-studio/sessions",
            "checks": [
                "no_forbidden_disclosure",
                "expected_facts_captured",
                "all_turns_succeeded",
                "timeout_retry_controls_exact",
                "agent_studio_session_lifecycle",
            ],
            "internal_memory_representation": "not compared",
            "assistant_prose": "not compared",
            "advisory_llm_judge": "out_of_scope",
        },
        "fixture": fixture_payload(fixture),
        "controls": {
            "rounds": config.rounds,
            "timeout_seconds": config.timeout_seconds,
            "retry_count": config.retry_count,
            "client_transport_retries": 0,
        },
        "requested_inputs": {
            "prompt_key": config.prompt_key,
            "persona_key": config.persona_key,
            "legacy": {
                "model": config.legacy_model,
                "model_router_key": router_model_key(config.legacy_model),
                "embedding": config.legacy_embedding,
            },
            "native": {
                "conversation_model": config.native_conversation_model,
                "reviewer_model": config.native_reviewer_model,
                "embedding_model": config.native_embedding_model,
            },
        },
    }


def capture_source_identity(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    build_identity = _build_source_identity_from_environment()
    if build_identity is not None:
        return build_identity
    revision = _git_output(project_root, "rev-parse", "HEAD")
    status = _git_output(project_root, "status", "--porcelain")
    try:
        fingerprint = source_fingerprint(project_root)
    except (OSError, subprocess.SubprocessError):
        fingerprint = "unknown"
    return {
        "revision": revision or "unknown",
        "dirty": bool(status),
        "fingerprint": fingerprint or "unknown",
    }


def _build_source_identity_from_environment() -> dict[str, Any] | None:
    revision = str(os.getenv("ADE_SOURCE_REVISION") or "").strip()
    fingerprint = str(os.getenv("ADE_SOURCE_FINGERPRINT") or "").strip()
    dirty_value = str(os.getenv("ADE_SOURCE_DIRTY") or "").strip().casefold()
    if (
        not revision
        or revision == "unknown"
        or not fingerprint
        or fingerprint == "unknown"
    ):
        return None
    if dirty_value not in {"true", "false"}:
        return None
    return {
        "revision": revision,
        "dirty": dirty_value == "true",
        "fingerprint": fingerprint,
    }


def safe_native_health(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload.get(key)
        for key in (
            "status",
            "database_ready",
            "worker_ready",
            "compatible_worker_count",
            "matching_build_worker_count",
            "compatibility_fingerprint",
            "source_revision",
            "source_dirty",
            "source_fingerprint",
            "failure_code",
        )
        if key in payload
    }


def native_definition_snapshot(
    payload: dict[str, Any], *, expected_prompt_key: str, expected_persona_key: str
) -> dict[str, Any]:
    prompt_key = str(payload.get("prompt_key") or "")
    persona_key = str(payload.get("persona_key") or "")
    prompt_sha256 = _sha256_string(payload.get("prompt_sha256"))
    persona_sha256 = _sha256_string(payload.get("persona_sha256"))
    if prompt_key != expected_prompt_key or persona_key != expected_persona_key:
        raise ValueError("native definition did not use the requested prompt/persona")
    deployments = payload.get("deployments")
    if not isinstance(deployments, list) or len(deployments) != 3:
        raise ValueError("native definition did not return three deployment snapshots")
    normalized = [_deployment_snapshot(item) for item in deployments]
    roles = {item["role"] for item in normalized}
    if roles != {"conversation", "reviewer", "retriever"}:
        raise ValueError("native definition deployment roles were incomplete")
    return {
        "id": _required_string(payload, "id"),
        "definition_key": _required_string(payload, "definition_key"),
        "version": int(payload.get("version") or 0),
        "prompt_key": prompt_key,
        "prompt_sha256": prompt_sha256,
        "persona_key": persona_key,
        "persona_sha256": persona_sha256,
        "tool_names": _string_list(payload.get("tool_names")),
        "memory_policy_version": str(payload.get("memory_policy_version") or ""),
        "qualification_state": str(payload.get("qualification_state") or ""),
        "deployments": sorted(normalized, key=lambda item: item["role"]),
    }


def evaluate_comparability(
    *,
    parity_spec_sha256: str,
    parity_spec: dict[str, Any],
    legacy_inputs: dict[str, Any] | None,
    native_health: dict[str, Any] | None,
    native_rounds: list[dict[str, Any]],
    source_identity: dict[str, Any],
) -> dict[str, Any]:
    expected = parity_spec.get("requested_inputs")
    fixture = parity_spec.get("fixture")
    controls = parity_spec.get("controls")
    if not isinstance(expected, dict) or not isinstance(fixture, dict):
        return _incomparable("parity_spec_structure_invalid", parity_spec_sha256)
    try:
        expected_rounds = int(controls["rounds"] if isinstance(controls, dict) else 0)
    except (TypeError, ValueError):
        return _incomparable("parity_spec_rounds_invalid", parity_spec_sha256)
    if expected_rounds < 1:
        return _incomparable("parity_spec_rounds_invalid", parity_spec_sha256)
    checks: dict[str, bool] = {
        "parity_spec_hash_present": bool(parity_spec_sha256),
        "source_identity_complete": _source_identity_complete(source_identity),
        "native_worker_build_matches_evaluator": _native_worker_matches_source(
            native_health, source_identity
        ),
        "legacy_inputs_available": legacy_inputs is not None,
        "fixture_hash_present": bool(fixture.get("sha256")),
        "all_native_rounds_have_definitions": len(native_rounds) == expected_rounds
        and all(
            isinstance(item.get("native_definition"), dict) for item in native_rounds
        ),
    }
    if legacy_inputs is None:
        checks.update(
            {
                "prompt_snapshots_match": False,
                "persona_snapshots_match": False,
                "conversation_models_match": False,
                "reviewer_models_match": False,
                "native_embedding_matches": False,
            }
        )
    else:
        checks.update(
            {
                "prompt_snapshots_match": _all_native(
                    native_rounds,
                    "prompt_key",
                    expected["prompt_key"],
                    "prompt_sha256",
                    legacy_inputs["prompt"]["content_sha256"],
                ),
                "persona_snapshots_match": _all_native(
                    native_rounds,
                    "persona_key",
                    expected["persona_key"],
                    "persona_sha256",
                    legacy_inputs["persona"]["content_sha256"],
                ),
                "conversation_models_match": _all_deployments_match(
                    native_rounds,
                    "conversation",
                    expected["legacy"]["model_router_key"],
                    expected["native"]["conversation_model"],
                ),
                "reviewer_models_match": _all_deployments_match(
                    native_rounds,
                    "reviewer",
                    expected["native"]["reviewer_model"],
                    expected["native"]["reviewer_model"],
                ),
                "native_embedding_matches": _all_deployments_match(
                    native_rounds,
                    "retriever",
                    expected["native"]["embedding_model"],
                    expected["native"]["embedding_model"],
                ),
            }
        )
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "parity_spec_sha256": parity_spec_sha256,
        "fixture_sha256": fixture.get("sha256"),
    }


def build_provenance(
    *,
    run_id: str,
    parity_spec_sha256: str,
    source_identity: dict[str, Any],
    legacy_inputs: dict[str, Any] | None,
    native_health: dict[str, Any] | None,
    native_rounds: list[dict[str, Any]],
    cleanup: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "agent-runtime-parity-provenance",
        "run_id": run_id,
        "parity_spec_sha256": parity_spec_sha256,
        "source_identity": source_identity,
        "legacy": {"inputs": legacy_inputs},
        "native": {
            "worker_health": native_health,
            "definitions": [item.get("native_definition") for item in native_rounds],
        },
        "cleanup": cleanup,
    }


def _option_snapshot(option: dict[str, Any]) -> dict[str, Any]:
    identity = {field: option.get(field) for field in OPTION_IDENTITY_FIELDS}
    # The v2 model catalog defines this digest. It intentionally differs from
    # newline-terminated evidence-artifact hashing.
    expected_sha = _catalog_identity_sha256(identity)
    received_sha = str(option.get("identity_sha256") or "")
    if received_sha and received_sha != expected_sha:
        raise ValueError(
            f"catalog option '{option.get('key')}' identity was inconsistent"
        )
    return {
        **identity,
        "identity_sha256": expected_sha,
    }


def _template_snapshot(
    payload: dict[str, Any], expected_kind: str, expected_key: str
) -> dict[str, Any]:
    content = str(payload.get("content") or "")
    sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if (
        payload.get("kind") != expected_kind
        or payload.get("scenario") != "chat"
        or payload.get("key") != expected_key
        or payload.get("content_sha256") != sha
    ):
        raise ValueError(f"selected {expected_kind} template identity was inconsistent")
    return {
        "kind": expected_kind,
        "scenario": "chat",
        "key": expected_key,
        "content": content,
        "content_sha256": sha,
        "updated_at": str(payload.get("updated_at") or ""),
    }


def _selected_option(items: object, key: str) -> dict[str, Any]:
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and item.get("key") == key:
                return item
    raise ValueError(f"selected catalog option '{key}' was unavailable")


def _deployment_snapshot(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("native definition deployment was not an object")
    result = {
        "deployment_id": _required_string(value, "deployment_id"),
        "route_alias": _required_string(value, "route_alias"),
        "fingerprint": _required_string(value, "fingerprint"),
        "role": _required_string(value, "role"),
        "lifecycle": str(value.get("lifecycle") or ""),
        "qualification_state": str(value.get("qualification_state") or ""),
    }
    return result


def _all_native(
    rounds: list[dict[str, Any]],
    key_a: str,
    expected_a: str,
    key_b: str,
    expected_b: str,
) -> bool:
    return bool(rounds) and all(
        item.get("native_definition", {}).get(key_a) == expected_a
        and item.get("native_definition", {}).get(key_b) == expected_b
        for item in rounds
    )


def _all_deployments_match(
    rounds: list[dict[str, Any]], role: str, expected_legacy: str, expected_native: str
) -> bool:
    return bool(rounds) and all(
        _deployment_route(item.get("native_definition"), role)
        == router_model_key(expected_native)
        and router_model_key(expected_legacy) == router_model_key(expected_native)
        for item in rounds
    )


def _deployment_route(definition: object, role: str) -> str:
    if not isinstance(definition, dict):
        return ""
    deployments = definition.get("deployments")
    if not isinstance(deployments, list):
        return ""
    for deployment in deployments:
        if isinstance(deployment, dict) and deployment.get("role") == role:
            return str(deployment.get("route_alias") or "")
    return ""


def _source_identity_complete(source: dict[str, Any]) -> bool:
    return (
        bool(source.get("revision"))
        and source.get("revision") != "unknown"
        and bool(source.get("fingerprint"))
        and source.get("fingerprint") != "unknown"
    )


def _native_worker_matches_source(
    native_health: dict[str, Any] | None, source_identity: dict[str, Any]
) -> bool:
    if not isinstance(native_health, dict):
        return False
    return (
        native_health.get("database_ready") is True
        and native_health.get("worker_ready") is True
        and native_health.get("source_revision") == source_identity.get("revision")
        and native_health.get("source_dirty") == source_identity.get("dirty")
        and native_health.get("source_fingerprint")
        == source_identity.get("fingerprint")
    )


def _git_output(project_root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(project_root), *args], text=True
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"native definition is missing {key}")
    return value


def _sha256_string(value: object) -> str:
    normalized = str(value or "").strip()
    if len(normalized) != 64 or any(
        char not in "0123456789abcdef" for char in normalized
    ):
        raise ValueError("native definition returned an invalid SHA-256")
    return normalized


def _string_list(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _catalog_identity_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _incomparable(reason: str, parity_spec_sha256: str) -> dict[str, Any]:
    return {
        "pass": False,
        "checks": {reason: False},
        "parity_spec_sha256": parity_spec_sha256,
        "fixture_sha256": None,
    }
