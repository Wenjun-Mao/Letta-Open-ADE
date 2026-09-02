from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from model_catalog_contracts.deployment_manifest import (
    DeploymentManifest,
    DeploymentManifestEntry,
    load_deployment_manifest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ade_api.features.agent_runtime_v3.release_policy import AGENT_STUDIO_RELEASE_ROUTES
from ade_api.features.agent_runtime_v3.release_evidence import (
    AgentStudioReleaseEvidence,
    AgentStudioReleaseEvidenceError,
    file_sha256,
    load_agent_studio_release_evidence,
    validate_agent_studio_release_evidence,
)

DEFAULT_MANIFEST = PROJECT_ROOT / "config/model-router/deployment-manifest.json"
DEFAULT_EVIDENCE = PROJECT_ROOT / "config/agent-studio/release-evidence.json"
DEFAULT_CONVERSATION_MODEL = AGENT_STUDIO_RELEASE_ROUTES["conversation"]
DEFAULT_REVIEWER_MODEL = AGENT_STUDIO_RELEASE_ROUTES["reviewer"]
DEFAULT_EMBEDDING_MODEL = AGENT_STUDIO_RELEASE_ROUTES["retriever"]


class AgentStudioReleaseGateError(RuntimeError):
    pass


def _production_policy_hashes() -> dict[str, str]:
    from workflows.evals.agent_runtime_v3_acceptance.policy import (
        production_policy_hashes,
    )

    return production_policy_hashes(PROJECT_ROOT)


def validate_agent_studio_release_gate(
    manifest: DeploymentManifest,
    *,
    conversation_model: str,
    reviewer_model: str,
    embedding_model: str,
    policy_hashes: dict[str, str],
    source_clean: bool,
    evidence_payload: Mapping[str, Any],
    manifest_sha256: str,
) -> AgentStudioReleaseEvidence:
    if not source_clean:
        raise AgentStudioReleaseGateError(
            "Agent Studio release requires a clean Git-visible source tree"
        )
    requirements = (
        (conversation_model, "conversation"),
        (reviewer_model, "reviewer"),
        (embedding_model, "retriever"),
    )
    for route_alias, role in requirements:
        deployment = manifest.for_route_alias(route_alias)
        if deployment is None:
            raise AgentStudioReleaseGateError(
                f"Agent Studio route alias is absent from the manifest: {route_alias}"
            )
        _validate_role(deployment, role, policy_hashes)
    return validate_agent_studio_release_evidence(
        evidence_payload,
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        policy_hashes=policy_hashes,
        release_routes=AGENT_STUDIO_RELEASE_ROUTES,
    )


def _validate_role(
    deployment: DeploymentManifestEntry,
    role: str,
    policy_hashes: dict[str, str],
) -> None:
    if deployment.lifecycle != "qualified" or not deployment.qualification.qualified:
        raise AgentStudioReleaseGateError(
            f"Deployment {deployment.deployment_id} is not promoted to qualified"
        )
    if deployment.qualification.stale_round_count != 0:
        raise AgentStudioReleaseGateError(
            f"Deployment {deployment.deployment_id} contains stale qualification rounds"
        )
    role_result = next(
        (item for item in deployment.qualification.role_results if item.role == role),
        None,
    )
    if (
        role_result is None
        or not role_result.qualified
        or role_result.observed_rounds < 3
        or role_result.consecutive_passing_rounds < 3
    ):
        raise AgentStudioReleaseGateError(
            f"Deployment {deployment.deployment_id} is not qualified for {role}"
        )
    fingerprint = deployment.fingerprint
    actual_policy_hashes = {
        "prompt": fingerprint.prompt_policy_sha256,
        "tool": fingerprint.tool_policy_sha256,
        "schema": fingerprint.schema_policy_sha256,
        "retrieval": fingerprint.retrieval_policy_sha256,
    }
    if actual_policy_hashes != policy_hashes:
        raise AgentStudioReleaseGateError(
            f"Deployment {deployment.deployment_id} qualification uses stale policy hashes"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed unless the exact Agent Studio release roles are promoted."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--conversation-model", default=DEFAULT_CONVERSATION_MODEL)
    parser.add_argument("--reviewer-model", default=DEFAULT_REVIEWER_MODEL)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    args = parser.parse_args()
    try:
        evidence = validate_agent_studio_release_gate(
            load_deployment_manifest(args.manifest, project_root=PROJECT_ROOT),
            conversation_model=args.conversation_model,
            reviewer_model=args.reviewer_model,
            embedding_model=args.embedding_model,
            policy_hashes=_production_policy_hashes(),
            source_clean=_git_tree_is_clean(),
            evidence_payload=load_agent_studio_release_evidence(args.evidence),
            manifest_sha256=file_sha256(args.manifest),
        )
        _validate_source_lineage(evidence.evaluated_source_revision)
    except (
        AgentStudioReleaseEvidenceError,
        AgentStudioReleaseGateError,
        ValueError,
    ) as exc:
        parser.error(str(exc))
    print(
        "Agent Studio release gate passed for qualified routes, paired parity, "
        f"capability evidence, and rollback rehearsal ({evidence.evidence_sha256})."
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
    offenders = [path for path in changed if not _is_post_evidence_path(path)]
    if offenders:
        raise AgentStudioReleaseGateError(
            "Agent Studio implementation changed after evidence collection: "
            + ", ".join(sorted(offenders))
        )


def _is_post_evidence_path(path: str) -> bool:
    return path in {
        "config/agent-studio/release-evidence.json",
        "config/model-router/deployment-manifest.json",
        "docs/adr/0016-ade-native-agent-studio-cutover.md",
        "docs/architecture/system-status.md",
        "docs/product-roadmap.md",
    } or path.startswith("docs/baselines/agent-studio-cutover/")


if __name__ == "__main__":
    raise SystemExit(main())
