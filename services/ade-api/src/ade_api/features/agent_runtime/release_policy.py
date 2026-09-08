from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from model_catalog_contracts.deployment_manifest import load_deployment_manifest

from .errors import RuntimeNotReady
from .release_evidence import (
    AgentStudioReleaseEvidence,
    AgentStudioReleaseEvidenceError,
    file_sha256,
    load_agent_studio_release_evidence,
    validate_agent_studio_release_evidence,
)


AGENT_STUDIO_RELEASE_EVIDENCE_PATH: Final = Path(
    "config/agent-studio/release-evidence.json"
)
AGENT_STUDIO_DEPLOYMENT_MANIFEST_PATH: Final = Path(
    "config/model-router/deployment-manifest.json"
)


# Every source file under a governed root participates in the policy digest. Exact
# singletons cover runtime entrypoints without broadening qualification to docs,
# frontend code, or completed evaluator implementations.
POLICY_INPUT_ROOTS: Final[dict[str, tuple[str, ...]]] = {
    "prompt": (
        "content/personas",
        "content/prompts/system/chat",
        "services/ade-api/src/ade_api/features/agent_runtime",
    ),
    "tool": (
        "services/ade-api/src/ade_api/features/agent_runtime",
        "services/model-router/src/model_router",
    ),
    "schema": (
        "packages/agent-runtime-eval-contracts/src/agent_runtime_eval_contracts",
        "services/ade-api/migrations/versions",
        "services/ade-api/src/ade_api/features/agent_runtime",
    ),
    "retrieval": (
        "packages/agent-runtime-eval-contracts/src/agent_runtime_eval_contracts/data",
        "services/ade-api/src/ade_api/features/agent_runtime",
    ),
}
POLICY_INPUT_FILES: Final[dict[str, tuple[str, ...]]] = {
    "prompt": (),
    "tool": (
        "config/model-router/model-profiles.json",
        "config/model-router/sources.json",
    ),
    "schema": (
        "scripts/check_agent_studio_release_gate.py",
        "scripts/promote_agent_studio_release.py",
        "scripts/rebind_agent_runtime_policy.py",
        "scripts/record_agent_studio_conformance.py",
        "scripts/source_fingerprint.py",
        "services/ade-api/Dockerfile",
        "services/ade-api/src/ade_api/platform/app.py",
        "services/ade-api/src/ade_api/platform/auth.py",
        "services/ade-api/src/ade_api/platform/project_paths.py",
        "services/ade-api/src/ade_api/platform/settings.py",
    ),
    "retrieval": (),
}


def production_policy_hashes(project_root: Path) -> dict[str, str]:
    return {
        name: _policy_bundle_hash(
            project_root,
            roots=POLICY_INPUT_ROOTS[name],
            files=POLICY_INPUT_FILES[name],
        )
        for name in POLICY_INPUT_ROOTS
    }


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


def load_validated_agent_studio_release(
    project_root: Path | None = None,
) -> AgentStudioReleaseEvidence:
    """Load the only release contract used by runtime execution."""

    if project_root is None:
        from ade_api.platform.project_paths import PROJECT_ROOT

        project_root = PROJECT_ROOT
    manifest_path = project_root / AGENT_STUDIO_DEPLOYMENT_MANIFEST_PATH
    evidence_path = project_root / AGENT_STUDIO_RELEASE_EVIDENCE_PATH
    return validate_agent_studio_release_evidence(
        load_agent_studio_release_evidence(evidence_path),
        manifest=load_deployment_manifest(manifest_path, project_root=project_root),
        manifest_sha256=file_sha256(manifest_path),
        policy_hashes=production_policy_hashes(project_root),
    )


def release_validation_kwargs(mode: str) -> dict[str, Any]:
    if mode != "release":
        return {}
    release = load_validated_agent_studio_release()
    return {
        "expected_policy_hashes": current_production_policy_hashes(),
        "expected_route_aliases": release.route_aliases,
        "expected_agent_bundle": {
            "prompt_key": release.agent_bundle.prompt_key,
            "persona_key": release.agent_bundle.persona_key,
            "tool_names": list(release.agent_bundle.tool_names),
        },
        "source_clean": source_tree_is_clean(),
    }


def ensure_agent_studio_release_ready(mode: str) -> None:
    """Fail closed until one reviewed release ledger authorizes traffic."""

    if mode != "release":
        return
    try:
        load_validated_agent_studio_release()
    except (AgentStudioReleaseEvidenceError, OSError, ValueError) as exc:
        raise RuntimeNotReady(
            "Agent Studio release is waiting for reviewed release evidence"
        ) from exc


def _policy_bundle_hash(
    project_root: Path, *, roots: tuple[str, ...], files: tuple[str, ...]
) -> str:
    paths: set[Path] = set()
    for relative_root in roots:
        root = project_root / relative_root
        if not root.is_dir():
            raise ValueError(f"policy input root does not exist: {relative_root}")
        paths.update(path for path in root.rglob("*") if _is_policy_source_file(path))
    for relative_file in files:
        path = project_root / relative_file
        if not path.is_file():
            raise ValueError(f"policy input does not exist: {relative_file}")
        paths.add(path)

    digest = hashlib.sha256()
    for path in sorted(paths):
        relative_path = path.relative_to(project_root).as_posix()
        encoded_path = relative_path.encode("utf-8")
        content = path.read_bytes()
        digest.update(len(encoded_path).to_bytes(8, "big"))
        digest.update(encoded_path)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _is_policy_source_file(path: Path) -> bool:
    return path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
