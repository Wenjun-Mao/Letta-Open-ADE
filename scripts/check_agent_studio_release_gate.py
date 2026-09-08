from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from model_catalog_contracts.deployment_manifest import (
    DeploymentManifest,
    load_deployment_manifest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ade_api.features.agent_runtime.release_evidence import (
    AgentStudioReleaseEvidence,
    AgentStudioReleaseEvidenceError,
    file_sha256,
    load_agent_studio_release_evidence,
    validate_agent_studio_release_evidence,
)
from ade_api.features.agent_runtime.release_policy import production_policy_hashes
from scripts.source_fingerprint import is_governed_source_path, source_fingerprint


DEFAULT_MANIFEST = PROJECT_ROOT / "config/model-router/deployment-manifest.json"
DEFAULT_EVIDENCE = PROJECT_ROOT / "config/agent-studio/release-evidence.json"


class AgentStudioReleaseGateError(RuntimeError):
    pass


def validate_agent_studio_release_gate(
    manifest: DeploymentManifest,
    *,
    policy_hashes: Mapping[str, str],
    source_clean: bool,
    evidence_payload: Mapping[str, Any],
    manifest_sha256: str,
) -> AgentStudioReleaseEvidence:
    if not source_clean:
        raise AgentStudioReleaseGateError(
            "Agent Studio release requires a clean Git-visible source tree"
        )
    return validate_agent_studio_release_evidence(
        evidence_payload,
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        policy_hashes=policy_hashes,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail closed unless reviewed steady-state evidence authorizes "
            "Agent Studio release."
        )
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    try:
        evidence = validate_agent_studio_release_gate(
            load_deployment_manifest(args.manifest, project_root=PROJECT_ROOT),
            policy_hashes=production_policy_hashes(PROJECT_ROOT),
            source_clean=_git_tree_is_clean(),
            evidence_payload=load_agent_studio_release_evidence(args.evidence),
            manifest_sha256=file_sha256(args.manifest),
        )
        _validate_source_lineage(evidence.evaluated_source_revision)
        if source_fingerprint(PROJECT_ROOT) != evidence.evaluated_source_fingerprint:
            raise AgentStudioReleaseGateError(
                "Agent Studio governed source does not match the evaluated build"
            )
    except (
        AgentStudioReleaseEvidenceError,
        AgentStudioReleaseGateError,
        ValueError,
    ) as exc:
        parser.error(str(exc))
    print(
        "Agent Studio release gate passed for qualified native routes, deterministic "
        f"conformance, and the reviewed agent bundle ({evidence.evidence_sha256})."
    )
    return 0


def _git_tree_is_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return not result.stdout.strip()


def _validate_source_lineage(evaluated_revision: str) -> None:
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", evaluated_revision, "HEAD"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestor.returncode != 0:
        raise AgentStudioReleaseGateError(
            "Agent Studio release source is not descended from the evaluated revision"
        )
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", f"{evaluated_revision}..HEAD"],
        cwd=PROJECT_ROOT,
        text=True,
    ).splitlines()
    offenders = [path for path in changed if is_governed_source_path(path)]
    if offenders:
        raise AgentStudioReleaseGateError(
            "Agent Studio runtime changed after evidence collection: "
            + ", ".join(sorted(offenders))
        )


if __name__ == "__main__":
    raise SystemExit(main())
