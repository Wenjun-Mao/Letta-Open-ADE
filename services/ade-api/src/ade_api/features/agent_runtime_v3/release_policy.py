from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any, Final


PREVIEW_RELEASE_ROUTES: Final[dict[str, str]] = {
    "conversation": "dgx_vllm::qwen3.6-35b-a3b-fp8",
    "reviewer": "dgx_vllm::qwen3.6-35b-a3b-fp8",
    "retriever": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
}
PREVIEW_RELEASE_PROMPT_KEY: Final = "chat_v20260516"
PREVIEW_RELEASE_PERSONA_KEY: Final = "chat_linxiaotang"
PREVIEW_RELEASE_TOOL_NAMES: Final[tuple[str, ...]] = ("search_memory",)

# These path-bound bundles are the executable behavior qualified by the
# production-path matrix. Mutable qualification results are deliberately not inputs.
PRODUCTION_POLICY_INPUTS: Final[dict[str, tuple[str, ...]]] = {
    "prompt": (
        "content/personas/personas.jsonl",
        "content/prompts/system/chat/chat_v20260516.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/compaction.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/context.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/contracts.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/definition_service.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/executor.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/reviewer.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/turn_execution.py",
    ),
    "tool": (
        "services/ade-api/src/ade_api/features/agent_runtime_v3/contracts.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/definition_service.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/deployments.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/executor.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/turn_execution.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_events.py",
    ),
    "schema": (
        "Makefile",
        "compose.yaml",
        "packages/agent-runtime-eval-contracts/src/agent_runtime_eval_contracts/data/study_cases.json",
        "packages/agent-runtime-eval-contracts/src/agent_runtime_eval_contracts/fixtures.py",
        "packages/agent-runtime-eval-contracts/src/agent_runtime_eval_contracts/observations.py",
        "packages/agent-runtime-eval-contracts/src/agent_runtime_eval_contracts/scoring.py",
        "scripts/check_native_preview_gate.py",
        "scripts/source_fingerprint.py",
        "services/ade-api/Dockerfile",
        "services/ade-api/migrations/versions/20260829_0001_ade_native_runtime.py",
        "services/ade-api/migrations/versions/20260830_0002_ade_conversation_compaction.py",
        "services/ade-api/migrations/versions/20260830_0003_agent_runtime_worker_health.py",
        "services/ade-api/migrations/versions/20260830_0004_agent_runtime_source_fingerprint.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/__init__.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/api.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/application.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/bootstrap.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/compaction.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/contracts.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/database_boundary.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/definition_service.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/dependencies.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/deployments.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/embeddings.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/errors.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/events.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/executor.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/fact_registry.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/flags.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/memory_commit.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/memory_intent.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/memory_policy.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/memory_review.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/base.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/conversations.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/database.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/definitions.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/leases.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/memory.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/metadata.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/runs.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/validation.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/workers.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/workspaces.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/presenters.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/preview_session_service.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/provider_tracing.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/release_policy.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/resource_service.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/retry.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/reviewer.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/router_transport.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/run_service.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/service_protocol.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/turn_execution.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_claims.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_control.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_events.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_finalization.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_health.py",
        "services/ade-api/src/ade_api/native_main.py",
        "services/ade-api/src/ade_api/platform/auth.py",
        "services/ade-api/src/ade_api/platform/project_paths.py",
        "services/ade-api/src/ade_api/platform/settings.py",
    ),
    "retrieval": (
        "packages/agent-runtime-eval-contracts/src/agent_runtime_eval_contracts/data/semantic_retrieval_cases.json",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/context.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/embeddings.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/memory.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/turn_execution.py",
    ),
}


def production_policy_hashes(project_root: Path) -> dict[str, str]:
    """Return an isolated snapshot so callers cannot mutate the cached policy."""

    return dict(_production_policy_hash_items(project_root))


@lru_cache(maxsize=4)
def _production_policy_hash_items(project_root: Path) -> tuple[tuple[str, str], ...]:
    return tuple(
        (name, _policy_bundle_hash(project_root, paths))
        for name, paths in PRODUCTION_POLICY_INPUTS.items()
    )


def fingerprint_policy_hashes(fingerprint: object) -> dict[str, str]:
    def field(name: str) -> str:
        if isinstance(fingerprint, Mapping):
            return str(fingerprint.get(name, ""))
        return str(getattr(fingerprint, name))

    return {
        "prompt": field("prompt_policy_sha256"),
        "tool": field("tool_policy_sha256"),
        "schema": field("schema_policy_sha256"),
        "retrieval": field("retrieval_policy_sha256"),
    }


def current_production_policy_hashes() -> dict[str, str]:
    from ade_api.platform.project_paths import PROJECT_ROOT

    return production_policy_hashes(PROJECT_ROOT)


def source_tree_is_clean() -> bool:
    return str(os.getenv("ADE_SOURCE_DIRTY") or "true").strip().casefold() in {
        "0",
        "false",
        "no",
        "off",
    }


def release_validation_kwargs(mode: str) -> dict[str, Any]:
    if mode != "release":
        return {}
    return {
        "expected_policy_hashes": current_production_policy_hashes(),
        "expected_route_aliases": PREVIEW_RELEASE_ROUTES,
        "source_clean": source_tree_is_clean(),
    }


def _policy_bundle_hash(project_root: Path, relative_paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative_path in sorted(relative_paths):
        normalized = Path(relative_path).as_posix()
        path = project_root / normalized
        if not path.is_file():
            raise ValueError(f"policy input does not exist: {normalized}")
        encoded_path = normalized.encode("utf-8")
        content = path.read_bytes()
        digest.update(len(encoded_path).to_bytes(8, "big"))
        digest.update(encoded_path)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()
