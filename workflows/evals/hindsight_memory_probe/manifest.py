"""Bind clean Git release and workflow inputs; runtime image IDs are a later receipt."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from .receipts import ReceiptStore

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = Path(__file__).resolve().parent


def candidate_manifest():
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)
    if status.strip():
        raise RuntimeError("clean_release_required")
    sha = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    )
    tracked = (
        subprocess.check_output(
            [
                "git",
                "ls-files",
                "workflows/evals/hindsight_memory_probe",
                "services/model-router",
                "services/ade-api/src/ade_api/features/agent_runtime",
                "packages",
                "pyproject.toml",
                "uv.lock",
            ],
            cwd=ROOT,
        )
        .decode()
        .splitlines()
    )
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tracked}
    value = {
        "contract": "ade-hindsight-infrastructure-v1",
        "source_sha": sha,
        "file_sha256": hashes,
        "pins": json.loads((WORKFLOW / "config/pins.json").read_text()),
        "runtime_image_ids": "P1 unmeasured",
        "semantic_fixtures": "subsequent serial assignment",
    }
    value["candidate_identity_sha256"] = hashlib.sha256(
        json.dumps(value, sort_keys=True).encode()
    ).hexdigest()
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    ReceiptStore(args.output_directory).write(
        "candidate-manifest.json", candidate_manifest()
    )
