"""No live provider provisioning before locally recorded OCI safety qualification."""

import hashlib
import json
import time

from .campaign_clock import (
    ACTIVATION_ID,
    DEADLINE,
    WORK_CUTOFF,
    activation_receipts_root,
)
from .supervisor import load_registry

REQUIRED = {
    "dummy_disconnect",
    "dummy_expiry",
    "resume_readback",
    "build_daemon_cancelled",
    "baseline_unchanged",
}


def require_oci_proof(directory):
    state = activation_receipts_root(directory) / "supervisor"
    registry = load_registry(state)
    proof_path = state / "oci-supervisor-proof.json"
    if proof_path.is_symlink() or not proof_path.is_file():
        raise RuntimeError("oci_supervisor_proof_path_invalid")
    proof = json.loads(proof_path.read_text())
    if (
        proof.get("activation_id") != ACTIVATION_ID
        or proof.get("registry_sha256") != registry["registry_sha256"]
    ):
        raise RuntimeError("oci_proof_registry_binding_invalid")
    if proof["hard_deadline"] != DEADLINE or time.time() >= WORK_CUTOFF:
        raise RuntimeError("live_qualification_clock_invalid")
    if any(proof.get(key) is not True for key in REQUIRED):
        raise RuntimeError("oci_supervisor_qualification_incomplete")
    evidence = proof.get("evidence_sha256")
    if not isinstance(evidence, dict) or not evidence:
        raise RuntimeError("oci_proof_evidence_required")
    cancellation_name = proof.get("build_cancellation_receipt")
    if cancellation_name not in evidence:
        raise RuntimeError("actual_build_cancellation_receipt_required")
    for name, sha in evidence.items():
        path = proof_path.parent / name
        if (
            proof_path.parent.resolve() not in path.resolve().parents
            or path.is_symlink()
        ):
            raise RuntimeError("oci_proof_evidence_not_scoped")
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise RuntimeError("oci_proof_evidence_changed")

    cancellation = json.loads((proof_path.parent / cancellation_name).read_text())
    if (
        cancellation.get("contract") != "ade-owned-buildkit-cancellation-v1"
        or cancellation.get("outcome") != "daemon_cancelled"
        or not cancellation.get("observed_sentinel")
        or cancellation.get("no_sentinel_samples", 0) < 3
    ):
        raise RuntimeError("build_daemon_cancellation_unproven")
    token = cancellation["job_token"]
    job_file = proof_path.parent / f"job-{token}.json"
    job = json.loads(job_file.read_text())
    if (
        job.get("kind") != "build-cancel"
        or job.get("build_sentinel") != token
        or hashlib.sha256(job_file.read_bytes()).hexdigest()
        != cancellation["job_sha256"]
    ):
        raise RuntimeError("build_cancellation_registration_not_bound")
