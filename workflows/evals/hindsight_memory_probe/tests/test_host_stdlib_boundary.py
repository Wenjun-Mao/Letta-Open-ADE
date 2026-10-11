"""Prove host finalization works without site packages or runner imports."""

import subprocess
import sys

from workflows.evals.hindsight_memory_probe.validate import ROOT

REPOSITORY = ROOT.parents[2]


def test_host_admission_and_snapshot_path_runs_under_python_no_site(tmp_path):
    script = tmp_path / "host_path.py"
    script.write_text(
        r'''
import contextlib, json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
from workflows.evals.hindsight_memory_probe import (
    candidate_database, epochs, finalization, host_guard, lifecycle, p4_evidence,
    quiescence, supervisor,
)
from workflows.evals.hindsight_memory_probe.receipts import ReceiptStore
from workflows.evals.hindsight_memory_probe.restart_selection import hash_json, sha256_file

base = Path(sys.argv[1])
receipts = base / "receipts"
state = receipts / "supervisor"
state.mkdir(parents=True, mode=0o700)
release_sha = "a" * 40
registry = {"registry_sha256": "b" * 64, "release": f"/release/{release_sha}"}
before_epoch, epoch_sha = "c" * 64, "d" * 64
epoch = {"index": 4, "release": registry["release"], "sha256": epoch_sha, "allocations": {}}
scope = {"character_root_id": "root", "tags": ["character:root", "kind:profile"],
         "tags_match": "any_strict", "cohort_ids": ["fact-a", "fact-b"],
         "positive_ids": ["fact-a"], "exclusion_ids": ["fact-b"]}
selection = {"schema": 1, "release_sha": release_sha,
    "registry_sha256": registry["registry_sha256"], "before_epoch_sha256": before_epoch,
    "banks": [{"bank_id": "opaque-public-bank", "workspace_id": "workspace",
        "subject_id": "subject", "scopes": [scope], "sources": [{
            "source_id": "source", "original_text_sha256": "1" * 64,
            "context_sha256": None, "content_hash": "document-content-hash", "curation_ids": [],
            "facts": {"valid": [{"id": "fact-a", "text_sha256": "2" * 64}],
                "invalidated": [{"id": "fact-b", "text_sha256": "3" * 64}]}}]}]}
evidence = receipts / "p4" / release_sha
evidence.mkdir(parents=True)
selection_path = evidence / "restart-selection.json"
selection_path.write_text(json.dumps(selection, sort_keys=True))
selection_hash = hash_json(selection)
before = {"selection_sha256": selection_hash, "run_identity": {
    "release_sha": release_sha, "registry_sha256": registry["registry_sha256"], "epoch_sha256": before_epoch}}
after = {"selection_sha256": selection_hash, "run_identity": {
    "release_sha": release_sha, "registry_sha256": registry["registry_sha256"], "epoch_sha256": epoch_sha}}
before_path, after_path = evidence / "restart-readback.before.json", evidence / "restart-readback.after.json"
before_path.write_text(json.dumps(before, sort_keys=True))
after_path.write_text(json.dumps(after, sort_keys=True))
proof = {"status": "completed", "claim": "bounded_restart_persistence_readback",
    "selection_sha256": selection_hash, "selection_file_sha256": sha256_file(selection_path),
    "before_file_sha256": sha256_file(before_path), "after_file_sha256": sha256_file(after_path),
    "before_sha256": hash_json(before), "after_sha256": hash_json(after),
    "registry_sha256": registry["registry_sha256"], "release_sha": release_sha,
    "before_epoch_sha256": before_epoch, "after_epoch_sha256": epoch_sha}
(evidence / "restart-readback.completed.json").write_text(json.dumps(proof, sort_keys=True))
# Historical root-level receipts do not satisfy a new release-scoped attempt.
(receipts / "restart-selection.json").write_text(json.dumps(selection, sort_keys=True))
(receipts / "restart-readback.completed.json").write_text(json.dumps(proof, sort_keys=True))

supervisor.load_registry = lambda _directory: registry
epochs.active = lambda *_args: epoch
epochs.effective_registry = lambda _directory, _registry: registry
quiescence.bounded_lease = lambda *_args, **_kwargs: contextlib.nullcontext()
quiescence.require_open = lambda *_args: None
supervisor.jobs = lambda _directory: []
host_guard.containers = lambda: containers
host_guard.candidate_containers = lambda items, _registry: items
host_guard.host_sample = lambda _release: {"memory_available": 10 * host_guard.GIB, "disk_free": 10 * host_guard.GIB}
host_guard.guard_reason = lambda *_args, **_kwargs: (None, None)
lifecycle.classify = lambda *_args: {"containers": {}, "reason": None}
finalization.time.time = lambda: finalization.WORK_CUTOFF - 5000

containers = []
for index, service in enumerate(("db", "hindsight", "model-router")):
    containers.append({"Id": f"container-{service}", "Image": f"image-{service}",
        "State": {"StartedAt": f"started-{index}", "Status": "running"},
        "Config": {"Labels": {"com.docker.compose.service": service,
            "com.docker.compose.project": "ade-hindsight-probe",
            "com.docker.compose.project.working_dir": f"{registry['release']}/workflows/evals/hindsight_memory_probe",
            "com.docker.compose.project.config_files": f"{registry['release']}/workflows/evals/hindsight_memory_probe/compose.yaml",
            "com.docker.compose.oneoff": "False"}}})

admitted = finalization.admit(state, drain_timeout=30, dump_timeout=30)
assert admitted["restart_selection"]["status"] == "frozen"
assert admitted["restart_readback"]["status"] == "completed"
assert admitted["restart_selection"]["path"] == f"../p4/{release_sha}/restart-selection.json"
assert admitted["restart_readback"]["path"] == f"../p4/{release_sha}/restart-readback.completed.json"
assert "httpx" not in sys.modules and "ade_api" not in sys.modules
candidate_database.db_container = lambda *_args: {"Id": "container-db", "Image": "image-db"}
candidate_database.operation_status_counts = lambda *_args: {"failed": 1, "cancelled": 2}
candidate_database.psql_text = lambda _dir, _reg, _adm, _db, query, _run: (
    "hindsight_probe" if query == "SELECT current_database()" else "{}")
def monitored(_dir, _reg, _epoch, _adm, _cmd, _timeout, *, stdout, **_kwargs):
    stdout.write(b"[]\n")
    return 0
snapshot = candidate_database.snapshot_database(state, registry, admitted, ReceiptStore(state), monitored)
scope_receipt = json.loads((state / "finalization" / admitted["token"] / "scope-eligibility.json").read_text())
assert snapshot["async_operation_status_counts"] == {"failed": 1, "cancelled": 2}
assert scope_receipt["selection_sha256"] == proof["selection_sha256"]
assert scope_receipt["selection_file_sha256"] == proof["selection_file_sha256"]
assert scope_receipt["before_file_sha256"] == proof["before_file_sha256"]
assert scope_receipt["after_file_sha256"] == proof["after_file_sha256"]
assert (receipts / "restart-selection.json").is_file()
print("host_finalization_stdlib_ok")
''',
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-S", str(script), str(tmp_path), str(REPOSITORY)],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert result.stdout.strip() == "host_finalization_stdlib_ok"
