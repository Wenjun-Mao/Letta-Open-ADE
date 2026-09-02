from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

from model_catalog_contracts.deployment_manifest import load_deployment_manifest

from .errors import RuntimeNotReady
from .release_evidence import (
    AgentStudioReleaseEvidenceError,
    file_sha256,
    load_agent_studio_release_evidence,
    validate_agent_studio_release_evidence,
)


AGENT_STUDIO_RELEASE_ROUTES: Final[dict[str, str]] = {
    "conversation": "dgx_vllm::qwen3.6-35b-a3b-fp8",
    "reviewer": "dgx_vllm::qwen3.6-35b-a3b-fp8",
    "retriever": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
}
AGENT_STUDIO_RELEASE_PROMPT_KEY: Final = "chat_v20260516"
AGENT_STUDIO_RELEASE_PERSONA_KEY: Final = "chat_linxiaotang"
AGENT_STUDIO_RELEASE_TOOL_NAMES: Final[tuple[str, ...]] = ("search_memory",)
AGENT_STUDIO_RELEASE_EVIDENCE_PATH: Final = Path(
    "config/agent-studio/release-evidence.json"
)
AGENT_STUDIO_DEPLOYMENT_MANIFEST_PATH: Final = Path(
    "config/model-router/deployment-manifest.json"
)

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
        "services/ade-api/src/ade_api/features/agent_runtime_v3/tool_policy.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/turn_execution.py",
    ),
    "tool": (
        "config/model-router/model-profiles.json",
        "config/model-router/sources.json",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/contracts.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/definition_service.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/deployments.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/executor.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/tool_policy.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/turn_execution.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_events.py",
        "services/model-router/src/model_router/app.py",
        "services/model-router/src/model_router/settings.py",
    ),
    "schema": (
        "Makefile",
        "compose.yaml",
        "packages/agent-runtime-eval-contracts/src/agent_runtime_eval_contracts/data/study_cases.json",
        "packages/agent-runtime-eval-contracts/src/agent_runtime_eval_contracts/fixtures.py",
        "packages/agent-runtime-eval-contracts/src/agent_runtime_eval_contracts/observations.py",
        "packages/agent-runtime-eval-contracts/src/agent_runtime_eval_contracts/scoring.py",
        "scripts/agent_studio_rollback_state.py",
        "scripts/agent_studio_rollback_web.py",
        "scripts/check_agent_studio_release_gate.py",
        "scripts/record_agent_studio_conformance.py",
        "scripts/rehearse_agent_studio_rollback.py",
        "scripts/review_agent_studio_cutover.py",
        "scripts/source_fingerprint.py",
        "services/ade-api/Dockerfile",
        "services/ade-api/migrations/versions/20260829_0001_ade_native_runtime.py",
        "services/ade-api/migrations/versions/20260830_0002_ade_conversation_compaction.py",
        "services/ade-api/migrations/versions/20260830_0003_agent_runtime_worker_health.py",
        "services/ade-api/migrations/versions/20260830_0004_agent_runtime_source_fingerprint.py",
        "services/ade-api/migrations/versions/20260902_0005_agent_studio_cutover.py",
        "services/ade-api/migrations/versions/20260902_0006_run_runtime_mode.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/__init__.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/agent_studio_api.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/agent_studio_reset.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/agent_studio_sessions.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/api.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/api_boundary.py",
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
        "services/ade-api/src/ade_api/features/agent_runtime_v3/provider_tracing.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/release_evidence.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/release_policy.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/resource_service.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/retry.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/reviewer.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/router_transport.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/run_service.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/service_protocol.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/tool_policy.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/turn_execution.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_claims.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_control.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_events.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_finalization.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_health.py",
        "services/ade-api/src/ade_api/features/test_center/agent_runtime_parity_evaluations.py",
        "services/ade-api/src/ade_api/native_main.py",
        "services/ade-api/src/ade_api/platform/auth.py",
        "services/ade-api/src/ade_api/platform/project_paths.py",
        "services/ade-api/src/ade_api/platform/settings.py",
        "workflows/evals/agent_runtime_parity/artifacts.py",
        "workflows/evals/agent_runtime_parity/clients.py",
        "workflows/evals/agent_runtime_parity/config.py",
        "workflows/evals/agent_runtime_parity/provenance.py",
        "workflows/evals/agent_runtime_parity/scoring.py",
        "workflows/evals/agent_runtime_parity/workflow.py",
        "workflows/evals/agent_runtime_v3_acceptance/promotion_review.py",
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
        "expected_route_aliases": AGENT_STUDIO_RELEASE_ROUTES,
        "source_clean": source_tree_is_clean(),
    }


def ensure_agent_studio_release_ready(mode: str) -> None:
    """Fail closed until one reviewed evidence ledger authorizes product traffic."""

    if mode != "release":
        return
    from ade_api.platform.project_paths import PROJECT_ROOT

    manifest_path = PROJECT_ROOT / AGENT_STUDIO_DEPLOYMENT_MANIFEST_PATH
    evidence_path = PROJECT_ROOT / AGENT_STUDIO_RELEASE_EVIDENCE_PATH
    try:
        validate_agent_studio_release_evidence(
            load_agent_studio_release_evidence(evidence_path),
            manifest=load_deployment_manifest(manifest_path, project_root=PROJECT_ROOT),
            manifest_sha256=file_sha256(manifest_path),
            policy_hashes=production_policy_hashes(PROJECT_ROOT),
            release_routes=AGENT_STUDIO_RELEASE_ROUTES,
        )
    except (AgentStudioReleaseEvidenceError, OSError, ValueError) as exc:
        raise RuntimeNotReady(
            "Agent Studio release is waiting for reviewed cutover evidence"
        ) from exc


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
