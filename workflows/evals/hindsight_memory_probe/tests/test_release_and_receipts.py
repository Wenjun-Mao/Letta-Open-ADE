import hashlib
import json

import pytest

from workflows.evals.hindsight_memory_probe import releases
from workflows.evals.hindsight_memory_probe.phase import set_phase
from workflows.evals.hindsight_memory_probe.receipts import CaptureFailure, ReceiptStore


def test_receipts_exclusive_private_and_capture_failure_latched(tmp_path):
    path = tmp_path / "receipts"
    store = ReceiptStore(path)
    store.write("one.json", {"value": "synthetic"})
    assert path.stat().st_mode & 0o777 == 0o700
    assert (path / "one.json").stat().st_mode & 0o777 == 0o600
    with pytest.raises(CaptureFailure):
        store.write("one.json", {"value": "changed"})
    assert json.loads((path / "one.json").read_text())["value"] == "synthetic"
    store.failure("request", "synthetic_fail")
    assert ReceiptStore(path).failed


def test_atomic_phase_keeps_original_intents(tmp_path):
    set_phase(tmp_path, "startup", "first-start")
    set_phase(tmp_path, "recall", "query-1")
    assert json.loads((tmp_path / "phase.json").read_text())["phase"] == "recall"
    intents = [json.loads(p.read_text()) for p in tmp_path.glob("*.intent.json")]
    assert {v["phase"] for v in intents} == {"startup", "recall"}
    assert (tmp_path / "phase.json").stat().st_mode & 0o777 == 0o600


def test_release_hash_verification_rejects_modified_clean_sha(tmp_path, monkeypatch):
    monkeypatch.setattr(releases, "PARENT", tmp_path)
    release = tmp_path / ("a" * 40)
    release.mkdir()
    (release / "owned.py").write_text("synthetic")
    (release / ".probe-release.json").write_text(
        json.dumps(
            {
                "source_sha": "a" * 40,
                "source_dirty": False,
                "file_sha256": {"owned.py": hashlib.sha256(b"synthetic").hexdigest()},
            }
        )
    )
    assert releases.verify(release)["source_dirty"] is False
    (release / "owned.py").write_text("modified")
    with pytest.raises(RuntimeError, match="hash_changed"):
        releases.verify(release)
    with pytest.raises(RuntimeError, match="path_required"):
        releases.validate_path(tmp_path / "unknown")


def test_live_gate_requires_real_oci_proof_contract_and_current_evidence(
    tmp_path, monkeypatch
):
    from workflows.evals.hindsight_memory_probe import qualification_gate as gate

    state = tmp_path / "receipts/supervisor"
    state.mkdir(parents=True)
    evidence = state / "synthetic-unit-test-evidence.json"
    evidence.write_text("synthetic mechanics only")
    value = {key: True for key in gate.REQUIRED}
    value.update(
        hard_deadline=gate.DEADLINE,
        evidence_sha256={
            evidence.name: hashlib.sha256(evidence.read_bytes()).hexdigest()
        },
    )
    proof = state / "oci-supervisor-proof.json"
    proof.write_text(json.dumps(value))
    monkeypatch.setattr(gate.time, "time", lambda: gate.WORK_CUTOFF - 1)
    gate.require_oci_proof(tmp_path)
    value["build_daemon_cancelled"] = False
    proof.write_text(json.dumps(value))
    with pytest.raises(RuntimeError, match="incomplete"):
        gate.require_oci_proof(tmp_path)
    value["build_daemon_cancelled"] = True
    proof.write_text(json.dumps(value))
    evidence.write_text("changed")
    with pytest.raises(RuntimeError, match="changed"):
        gate.require_oci_proof(tmp_path)
    monkeypatch.setattr(gate.time, "time", lambda: gate.WORK_CUTOFF)
    with pytest.raises(RuntimeError, match="clock_invalid"):
        gate.require_oci_proof(tmp_path)


def test_reopening_partial_capture_does_not_silently_requalify(tmp_path):
    store = ReceiptStore(tmp_path)
    store.write("interrupted.incoming.json", {"request_id": "interrupted"})
    assert ReceiptStore(tmp_path).failed
