from __future__ import annotations

from pathlib import Path
from typing import Final

from agent_runtime_eval_contracts import policy_bundle_hash


PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]

# These bundles are the product behavior qualified by the production-path matrix.
# Paths are intentionally explicit: adding, removing, or renaming an input resets
# the deployment fingerprint instead of silently inheriting prior evidence.
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
        "scripts/source_fingerprint.py",
        "services/ade-api/Dockerfile",
        "services/ade-api/migrations/versions/20260829_0001_ade_native_runtime.py",
        "services/ade-api/migrations/versions/20260830_0002_ade_conversation_compaction.py",
        "services/ade-api/migrations/versions/20260830_0003_agent_runtime_worker_health.py",
        "services/ade-api/migrations/versions/20260830_0004_agent_runtime_source_fingerprint.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/api.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/compaction.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/contracts.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/dependencies.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/deployments.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/events.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/fact_registry.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/memory_commit.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/memory_policy.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/memory_review.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/conversations.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/leases.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/runs.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/persistence/workers.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/provider_tracing.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/retry.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/router_transport.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/run_service.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_claims.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_control.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_events.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_finalization.py",
        "services/ade-api/src/ade_api/features/agent_runtime_v3/worker_health.py",
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


def production_policy_hashes(project_root: Path = PROJECT_ROOT) -> dict[str, str]:
    return {
        name: policy_bundle_hash(project_root, paths).removeprefix("sha256:")
        for name, paths in PRODUCTION_POLICY_INPUTS.items()
    }


def fingerprint_policy_hashes(fingerprint: object) -> dict[str, str]:
    return {
        "prompt": str(getattr(fingerprint, "prompt_policy_sha256")),
        "tool": str(getattr(fingerprint, "tool_policy_sha256")),
        "schema": str(getattr(fingerprint, "schema_policy_sha256")),
        "retrieval": str(getattr(fingerprint, "retrieval_policy_sha256")),
    }
