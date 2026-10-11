"""Historical P4 admission is bound to the exact observed receipt layout."""

import hashlib
import json
from pathlib import Path

import pytest

from workflows.evals.hindsight_memory_probe import (
    host_guard,
    restore,
    restore_post_snapshot_admission as admission,
    restore_cleanup_recovery_contract,
    restore_post_snapshot_contract as contract,
    restore_process,
    restore_snapshot,
)


def _write(path: Path, value: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(value)
    path.chmod(0o400)


def _success_job(directory: Path, operation_token: str, label: str,
                 command: list[str], created_at: float, *, wrapper=True,
                 command_hash=None, identity_hash="a" * 64) -> dict:
    job_token = f"{len(list(directory.glob('restore-*-job.json'))):032x}"
    digest = command_hash or hashlib.sha256(json.dumps(command).encode()).hexdigest()
    job = {"schema": 1, "token": job_token, "operation_token": operation_token,
           "operation": label, "command_sha256": digest, "created_at": created_at,
           "deadline": created_at + 1,
           "identity": {"cmd_sha256": identity_hash}}
    _write(directory / f"job-{job_token}.result.json", b'{"exit_code":0}')
    if wrapper:
        _write(directory / f"restore-{operation_token}-{job_token}-result.json",
               json.dumps({"operation": label, "exit_code": 0,
                           "command_sha256": digest}).encode())
    _write(directory / f"restore-{operation_token}-{job_token}-job.json",
           json.dumps(job).encode())
    return job


def test_original_proof_accepts_observed_inventory_and_authorized_recovery_readback(tmp_path, monkeypatch):
    token = "b" * 32
    container_id = "c" * 64
    volume = "ade-hindsight-restore-fixture_data"
    archive_path, snapshot_path, selection_path = (
        tmp_path / name for name in ("archive.dump", "snapshot.json", "selection.json"))
    for path, content in ((archive_path, b"archive"), (snapshot_path, b"snapshot"),
                          (selection_path, b"selection")):
        _write(path, content)
    operation = {
        "token": token,
        "compose": {"project": "restore-fixture", "path": "/compose.yml", "volume": volume},
        "archive": {"path": str(archive_path), "sha256": hashlib.sha256(b"archive").hexdigest()},
        "snapshot": {"path": str(snapshot_path), "root": str(tmp_path),
                     "sha256": hashlib.sha256(b"snapshot").hexdigest()},
        "selection": {"path": str(selection_path), "sha256": hashlib.sha256(b"selection").hexdigest()},
        "restore_root": str(tmp_path / "restore"), "finalization": {"containers": []},
    }
    _write(tmp_path / "restore-operation.json", json.dumps(operation).encode())
    _write(tmp_path / f"restore-{token}-failure.result.json", json.dumps({
        "token": token, "status": "failed", "stage": "snapshot",
        "reason": "restore_process_identity_changed", "time": 209.0}).encode())
    _write(tmp_path / f"restore-{token}-cleanup.result.json", json.dumps({
        "token": token, "status": "preserved_failed_state",
        "reason": "post_restore_snapshot_not_preserved", "removed": False,
        "container_id": container_id, "time": 210.0}).encode())
    _write(tmp_path / f"restore-{token}-create.result.json", json.dumps({
        "token": token, "container_id": container_id, "volume": volume}).encode())
    _write(tmp_path / f"restore-{token}-restore.result.json", json.dumps({
        "token": token, "status": "completed", "container_id": container_id,
        "archive_sha256": operation["archive"]["sha256"]}).encode())
    _write(tmp_path / f"restore-{token}-restore.intent.json", json.dumps({
        "container_id": container_id, "archive_sha256": operation["archive"]["sha256"]}).encode())

    jobs = []
    create_command = ["docker", "compose", "--project-name", operation["compose"]["project"],
                      "-f", operation["compose"]["path"], "up", "-d", "--pull", "never", "db"]
    restore_command = ["docker", "exec", "-i", container_id, "pg_restore", "--exit-on-error",
                       "--single-transaction", "--no-owner", "--no-acl", "-U",
                       "hindsight_probe", "-d", "hindsight_probe"]
    jobs.append(_success_job(tmp_path, token, "compose-create", create_command, 1))
    jobs.append(_success_job(tmp_path, token, "pg-restore", restore_command, 2))
    read_command_hash = hashlib.sha256(json.dumps(
        ["docker", "exec", "-i", container_id, "psql", "-U", "hindsight_probe", "-d",
         "hindsight_probe", "-At", "-c", "SELECT current_database()"]).encode()).hexdigest()
    jobs.append(_success_job(tmp_path, token, "database-readiness", [], 3,
                             command_hash=read_command_hash))
    jobs.append(_success_job(tmp_path, token, "restore-snapshot-query", [], 4,
                             command_hash=read_command_hash))
    for index, table in enumerate(restore_snapshot.candidate_database.SNAPSHOT_TABLES[:8]):
        command = ["docker", "exec", "-i", container_id, "psql", "-U", "hindsight_probe",
                   "-d", "hindsight_probe", "-At", "-c", restore_snapshot.table_query(table)]
        jobs.append(_success_job(tmp_path, token, f"restore-snapshot-table-{table}", command,
                                 200 + index, wrapper=index < 7))
    for index in range(59):
        jobs.append(_success_job(tmp_path, token, restore_process.IDENTITY_LIST_READBACK,
            ["docker", "ps", "-aq", "--no-trunc"], 10 + index))
    for index in range(30):
        jobs.append(_success_job(tmp_path, token, restore_process.IDENTITY_LIST_READBACK,
            ["docker", "volume", "ls", "-q", "--filter", f"name={volume}"], 80 + index))
    failed_token = f"{len(list(tmp_path.glob('restore-*-job.json'))):032x}"
    failed = {"schema": 1, "token": failed_token, "operation_token": token,
              "operation": restore_process.IDENTITY_LIST_READBACK,
              "command_sha256": hashlib.sha256(
                  json.dumps(["docker", "ps", "-aq", "--no-trunc"]).encode()).hexdigest(),
              "created_at": 207.5, "deadline": 208,
              "identity": {"cmd_sha256": hashlib.sha256(b"").hexdigest()}}
    _write(tmp_path / f"restore-{token}-{failed_token}-job.json", json.dumps(failed).encode())
    jobs.append(failed)
    for label, count in ((restore_process.IDENTITY_READBACK, 87),
                         (restore_process.OPERATOR_READBACK, 2),
                         (restore_process.OPERATOR_LIST_READBACK, 2)):
        for index in range(count):
            jobs.append(_success_job(tmp_path, token, label, ["docker", "inspect", container_id],
                                     150 + index / 10))
    jobs.append(_success_job(tmp_path, token, "cleanup-preserve-stop",
        ["docker", "stop", "--time", "20", container_id], 208))

    admission_token = "9" * 32
    failure_path = tmp_path / f"restore-{token}-failure.result.json"
    cleanup_path = tmp_path / f"restore-{token}-cleanup.result.json"
    authority_path = tmp_path / f"restore-{token}-post-restore-authority-{admission_token}.json"
    authority = {"schema": 1, "kind": "failed_post_restore_snapshot_recovery",
        "admission_token": admission_token, "token": token,
        "operation_sha256": hashlib.sha256((tmp_path / "restore-operation.json").read_bytes()).hexdigest(),
        "failure_sha256": hashlib.sha256(failure_path.read_bytes()).hexdigest(),
        "cleanup_sha256": hashlib.sha256(cleanup_path.read_bytes()).hexdigest(),
        "container_id": container_id, "volume": volume, "recovery_source_sha": "1" * 40,
        "issued_at": 211.0, "deadline": 300.0, "scopes": contract.SCOPES}
    _write(authority_path, json.dumps(authority).encode())
    readback = _success_job(tmp_path, token,
        restore_process.POST_RESTORE_RECOVERY_READBACK, ["docker", "inspect", container_id], 212)
    readback["recovery_admission_token"] = admission_token
    readback["recovery_authority_sha256"] = hashlib.sha256(authority_path.read_bytes()).hexdigest()
    registration = tmp_path / f"restore-{token}-{readback['token']}-job.json"
    registration.chmod(0o600)
    registration.write_text(json.dumps(readback))
    registration.chmod(0o400)
    jobs.append(readback)

    monkeypatch.setattr(restore_cleanup_recovery_contract, "_source_proof", lambda *_args: None)
    monkeypatch.setattr(restore_process, "registered_jobs", lambda *_args: jobs)
    monkeypatch.setattr(host_guard, "tagged_processes", lambda *_args: [])
    monkeypatch.setattr(restore, "_controller_present", lambda *_args: False)

    proof, _archive, original_snapshot = admission._validate_original(tmp_path, operation)
    assert proof["failed_job"]["token"] == failed_token
    assert original_snapshot == snapshot_path

    jobs.pop(next(index for index, job in enumerate(jobs)
                  if job["operation"] == restore_process.IDENTITY_LIST_READBACK
                  and job["token"] != failed_token))
    proof, _, _ = admission._validate_original(tmp_path, operation)
    assert proof["failed_job"]["token"] == failed_token
    incomplete = next(job for job in jobs
                      if job["operation"] == restore_process.IDENTITY_LIST_READBACK
                      and job["token"] != failed_token)
    (tmp_path / f"restore-{token}-{incomplete['token']}-result.json").unlink()
    with pytest.raises(RuntimeError, match="identity_list_receipt_incomplete"):
        admission._validate_original(tmp_path, operation)
