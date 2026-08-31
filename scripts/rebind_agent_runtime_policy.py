from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from model_catalog_contracts.deployment_manifest import (
    DeploymentFingerprint,
    DeploymentManifest,
)

from workflows.evals.agent_runtime_v3_acceptance.policy import (
    production_policy_hashes,
)


DEFAULT_MANIFEST = REPOSITORY_ROOT / "config/model-router/deployment-manifest.json"
_FINGERPRINT_POLICY_FIELDS = {
    "prompt": "prompt_policy_sha256",
    "tool": "tool_policy_sha256",
    "schema": "schema_policy_sha256",
    "retrieval": "retrieval_policy_sha256",
}


def rebind_manifest(
    payload: dict[str, Any], policy_hashes: dict[str, str]
) -> dict[str, Any]:
    DeploymentManifest.from_payload(payload)
    if set(policy_hashes) != set(_FINGERPRINT_POLICY_FIELDS):
        raise ValueError(
            "policy hashes must include prompt, tool, schema, and retrieval"
        )

    updated = deepcopy(payload)
    for deployment in updated["deployments"]:
        fingerprint = deployment["fingerprint"]
        current_policy_hashes = {
            policy_name: fingerprint[fingerprint_field]
            for policy_name, fingerprint_field in _FINGERPRINT_POLICY_FIELDS.items()
        }
        if current_policy_hashes == policy_hashes:
            continue
        for policy_name, fingerprint_field in _FINGERPRINT_POLICY_FIELDS.items():
            fingerprint[fingerprint_field] = policy_hashes[policy_name]

        qualification = deployment["qualification"]
        qualification["fingerprint_sha256"] = DeploymentFingerprint.from_payload(
            fingerprint
        ).sha256
        qualification["qualified"] = False
        qualification["stale_round_count"] = 0
        for result in qualification["role_results"]:
            result["observed_rounds"] = 0
            result["consecutive_passing_rounds"] = 0
            result["qualified"] = False
        if deployment["lifecycle"] == "qualified":
            deployment["lifecycle"] = "candidate"

    DeploymentManifest.from_payload(updated)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Bind deployment fingerprints to current ADE runtime policy and invalidate "
            "prior qualification evidence."
        )
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the rebound manifest; otherwise only report whether it is stale.",
    )
    args = parser.parse_args()

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    rebound = rebind_manifest(payload, production_policy_hashes(REPOSITORY_ROOT))
    if rebound == payload:
        print("Deployment manifest is already bound to current runtime policy.")
        return 0
    if not args.apply:
        print(
            "Deployment manifest uses stale runtime policy identity; run with --apply "
            "before collecting qualification evidence."
        )
        return 1

    temporary_path = args.manifest.with_suffix(f"{args.manifest.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(rebound, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(args.manifest)
    print(
        "Rebound deployment fingerprints and reset all qualification evidence for "
        "changed runtime policy."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
