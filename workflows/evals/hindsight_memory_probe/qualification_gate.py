"""No live provider provisioning before locally recorded OCI safety qualification."""

import hashlib
import json
import time

from .campaign_clock import DEADLINE, WORK_CUTOFF

REQUIRED = {
    "dummy_disconnect",
    "dummy_expiry",
    "resume_readback",
    "build_daemon_cancelled",
    "baseline_unchanged",
}


def require_oci_proof(directory):
    proof_path = directory / "receipts/supervisor/oci-supervisor-proof.json"
    proof = json.loads(proof_path.read_text())
    if proof["hard_deadline"] != DEADLINE or time.time() >= WORK_CUTOFF:
        raise RuntimeError("live_qualification_clock_invalid")
    if any(proof.get(key) is not True for key in REQUIRED):
        raise RuntimeError("oci_supervisor_qualification_incomplete")
    evidence = proof.get("evidence_sha256")
    if not isinstance(evidence, dict) or not evidence:
        raise RuntimeError("oci_proof_evidence_required")
    for name, sha in evidence.items():
        path = proof_path.parent / name
        if (
            proof_path.parent.resolve() not in path.resolve().parents
            or path.is_symlink()
        ):
            raise RuntimeError("oci_proof_evidence_not_scoped")
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise RuntimeError("oci_proof_evidence_changed")
