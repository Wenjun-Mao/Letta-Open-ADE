from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .config import (
    ADE_API_TRANSPORT_RETRIES,
    JUDGE_TRANSPORT_RETRIES,
    ChatMemoryEvalConfig,
    ade_api_timeout_seconds,
    effective_judge_model_key,
)
from .fixtures import ConversationFixture
from .scoring import DEFAULT_FORBIDDEN_REPLY_SUBSTRINGS


class TemplateClient(Protocol):
    def template(self, kind: str, key: str) -> dict[str, Any]: ...


_OPTION_IDENTITY_FIELDS = (
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


def capture_evaluation_provenance(
    *,
    run_id: str,
    api: TemplateClient,
    options: dict[str, Any],
    config: ChatMemoryEvalConfig,
    fixture: ConversationFixture,
    captured_at: datetime | None = None,
) -> dict[str, Any]:
    prompt = _template_snapshot(api.template("prompt", config.prompt_key), "prompt")
    persona = _template_snapshot(api.template("persona", config.persona_key), "persona")
    model = _option_snapshot(_selected_option(options.get("models"), config.model))
    embedding = (
        _option_snapshot(_selected_option(options.get("embeddings"), config.embedding))
        if config.embedding
        else None
    )
    fixture_payload = _fixture_payload(fixture)
    controls = {
        "rounds": config.rounds,
        "timeout_seconds": config.timeout_seconds,
        "retry_count": config.retry_count,
        "ade_api_timeout_seconds": ade_api_timeout_seconds(config),
        "ade_api_transport_retries": ADE_API_TRANSPORT_RETRIES,
        "judge_transport_retries": JUDGE_TRANSPORT_RETRIES,
        "stop_on_error": config.stop_on_error,
        "keep_agents": config.keep_agents,
        "judge_enabled": config.judge_enabled,
        "effective_judge_model_key": effective_judge_model_key(config),
        "judge_timeout_seconds": config.judge_timeout_seconds,
        "evaluator_source_revision": _source_env("ADE_SOURCE_REVISION", "unknown"),
        "evaluator_source_dirty": _source_env("ADE_SOURCE_DIRTY", "true"),
        "evaluator_source_fingerprint": _source_env(
            "ADE_SOURCE_FINGERPRINT", "unknown"
        ),
    }
    configuration_payload = {
        "scenario": "chat",
        "model_identity_sha256": model["identity_sha256"],
        "embedding_identity_sha256": (
            embedding["identity_sha256"] if embedding else None
        ),
        "prompt_content_sha256": prompt["content_sha256"],
        "persona_content_sha256": persona["content_sha256"],
        "fixture_sha256": _sha256(fixture_payload),
        "controls": controls,
    }
    payload = {
        "schema_version": 3,
        "run_id": run_id,
        "captured_at": (captured_at or datetime.now(timezone.utc)).isoformat(),
        "configuration_sha256": _sha256(configuration_payload),
        "fixture_sha256": configuration_payload["fixture_sha256"],
        "controls": controls,
        "prompt": prompt,
        "persona": persona,
        "model": model,
        "embedding": embedding,
    }
    payload["provenance_sha256"] = _sha256(payload)
    return payload


def write_provenance(path: Path, provenance: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def expected_agent_identities(provenance: dict[str, Any]) -> dict[str, str | None]:
    embedding = provenance.get("embedding")
    return {
        "model_identity_sha256": str(provenance["model"]["identity_sha256"]),
        "embedding_identity_sha256": (
            str(embedding["identity_sha256"]) if isinstance(embedding, dict) else None
        ),
        "prompt_content_sha256": str(provenance["prompt"]["content_sha256"]),
        "persona_content_sha256": str(provenance["persona"]["content_sha256"]),
    }


def assert_created_agent_identities(
    created: dict[str, Any], provenance: dict[str, Any]
) -> None:
    for field, expected in expected_agent_identities(provenance).items():
        if created.get(field) != expected:
            raise RuntimeError(
                f"Agent creation returned a different {field} than the captured evaluation provenance"
            )


def _template_snapshot(record: dict[str, Any], expected_kind: str) -> dict[str, Any]:
    content = str(record.get("content", ""))
    content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if record.get("kind") != expected_kind or record.get("scenario") != "chat":
        raise ValueError(f"Selected {expected_kind} is not an active chat template")
    if record.get("content_sha256") != content_sha256:
        raise ValueError(f"Selected {expected_kind} content identity is inconsistent")
    return {
        "kind": expected_kind,
        "scenario": "chat",
        "key": str(record.get("key", "")),
        "label": str(record.get("label", "")),
        "description": str(record.get("description", "")),
        "content": content,
        "content_sha256": content_sha256,
        "updated_at": str(record.get("updated_at", "")),
    }


def _selected_option(items: object, key: str) -> dict[str, Any]:
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and item.get("key") == key:
                return item
    raise ValueError(f"Selected catalog option '{key}' is unavailable")


def _option_snapshot(option: dict[str, Any]) -> dict[str, Any]:
    identity_payload = {field: option.get(field) for field in _OPTION_IDENTITY_FIELDS}
    identity_sha256 = _sha256(identity_payload)
    if option.get("identity_sha256") != identity_sha256:
        raise ValueError(
            f"Catalog option '{option.get('key', '')}' identity is inconsistent"
        )
    return {
        "key": str(option.get("key", "")),
        "label": str(option.get("label", "")),
        "source_id": str(option.get("source_id", "")),
        "source_label": str(option.get("source_label", "")),
        "provider_model_id": str(option.get("provider_model_id", "")),
        "upstream_provider_model_id": option.get("upstream_provider_model_id"),
        "sampling_defaults": option.get("sampling_defaults", {}),
        "scenario_sampling_defaults": option.get("scenario_sampling_defaults", {}),
        "supports_top_k": option.get("supports_top_k"),
        "supports_thinking": option.get("supports_thinking"),
        "thinking_default_enabled": option.get("thinking_default_enabled"),
        "tool_call_thinking_default_enabled": option.get(
            "tool_call_thinking_default_enabled"
        ),
        "profile_applied": option.get("profile_applied"),
        "profile_source": str(option.get("profile_source", "")),
        "agent_studio_candidate": option.get("agent_studio_candidate"),
        "agent_studio_compatible": option.get("agent_studio_compatible"),
        "deployment": option.get("deployment"),
        "identity_sha256": identity_sha256,
    }


def _fixture_payload(fixture: ConversationFixture) -> dict[str, Any]:
    return {
        "key": fixture.key,
        "description": fixture.description,
        "turns": list(fixture.turns),
        "expected_facts": [
            {"key": item.key, "label": item.label, "aliases": list(item.aliases)}
            for item in fixture.expected_facts
        ],
        "forbidden_reply_substrings": list(
            fixture.forbidden_reply_substrings or DEFAULT_FORBIDDEN_REPLY_SUBSTRINGS
        ),
    }


def _source_env(name: str, default: str) -> str:
    return str(os.getenv(name) or default).strip() or default


def _sha256(payload: object) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
