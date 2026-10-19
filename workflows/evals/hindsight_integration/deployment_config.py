"""Generate only the new, unqualified Stage 1 manifest; never rebind a release ledger."""

import argparse
import copy
import json
from pathlib import Path

from ade_api.features.agent_runtime.release_policy import production_policy_hashes
from model_catalog_contracts.deployment_manifest import (
    DeploymentFingerprint,
    DeploymentManifest,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path("workflows/evals/hindsight_integration/config/deployments.json")


def candidate_manifest(root=PROJECT_ROOT):
    original = json.loads(
        (root / "config/model-router/deployment-manifest.json").read_text()
    )
    candidates = [
        item
        for item in original["deployments"]
        if item["id"] == "deepseek-v4_1-flash-development"
    ]
    if len(candidates) != 1 or candidates[0]["route_aliases"] != [
        "deepseek::deepseek-flash"
    ]:
        raise ValueError("Approved DeepSeek development identity changed")
    deployment = copy.deepcopy(candidates[0])
    fingerprint = deployment["fingerprint"]
    if {
        key: fingerprint[key]
        for key in (
            "provider",
            "endpoint_identity",
            "served_model",
            "artifact_reference",
        )
    } != {
        "provider": "deepseek",
        "endpoint_identity": "api.deepseek.com",
        "served_model": "deepseek-flash",
        "artifact_reference": "DeepSeek-V4.1-Flash",
    }:
        raise ValueError("Approved provider/model identity changed")
    deployment["id"] = "deepseek-hindsight-stage1-development"
    deployment["roles"] = ["conversation", "compaction"]
    deployment["lifecycle"] = "candidate"
    for name, digest in production_policy_hashes(root).items():
        fingerprint[f"{name}_policy_sha256"] = digest
    fingerprint["sampling_settings"]["required_tool_choice"] = (
        "auto; discretionary curated tools"
    )
    fingerprint["sampling_settings"]["structured_output"] = (
        "compaction only: json_object; ADE closed validation"
    )
    fingerprint["context_settings"].pop("reviewer_repair_count", None)
    deployment["qualification"] = {
        "fingerprint_sha256": DeploymentFingerprint.from_payload(fingerprint).sha256,
        "qualified": False,
        "stale_round_count": 0,
        "role_results": [
            {
                "role": role,
                "observed_rounds": 0,
                "consecutive_passing_rounds": 0,
                "qualified": False,
            }
            for role in deployment["roles"]
        ],
    }
    payload = {"schema_version": 1, "deployments": [deployment]}
    DeploymentManifest.from_payload(payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate only the Stage 1 candidate configuration",
    )
    arguments = parser.parse_args()
    payload = candidate_manifest()
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if arguments.write:
        destination = PROJECT_ROOT / OUTPUT
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered)
        print(f"Generated unqualified candidate: {OUTPUT}")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
