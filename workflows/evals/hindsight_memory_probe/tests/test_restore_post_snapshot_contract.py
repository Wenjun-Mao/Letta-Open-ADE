"""Historical P4 admission is bound to the exact observed receipt layout."""

import hashlib
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from workflows.evals.hindsight_memory_probe import (
    host_guard,
    restore,
    restore_post_snapshot_admission as admission,
    restore_post_snapshot_archive as retirement_archive,
    restore_cleanup_recovery_contract,
    restore_post_snapshot_contract as contract,
    restore_post_snapshot_expiry as expiry,
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
        "schema": 1, "token": token,
        "compose": {"project": "ade-hindsight-restore-" + token[:16],
                    "path": "/compose.yml", "volume": volume, "source_image_id": "image-id"},
        "archive": {"path": str(archive_path), "sha256": hashlib.sha256(b"archive").hexdigest()},
        "snapshot": {"path": str(snapshot_path), "root": str(tmp_path),
                     "sha256": hashlib.sha256(b"snapshot").hexdigest()},
        "selection": {"path": str(selection_path), "sha256": hashlib.sha256(b"selection").hexdigest()},
        "restore_root": str(tmp_path / "restore"), "finalization": {"containers": []},
        "release_path": "/opt/restore/releases/source-sha",
        "deadline": restore.WORK_CUTOFF - 1000,
        "cleanup_deadline": restore.WORK_CUTOFF - 500,
        "hard_deadline": restore.DEADLINE,
    }
    _write(tmp_path / "restore-operation.json", json.dumps(operation).encode())
    _write(tmp_path / "restore-operation-seal.json", json.dumps({
        "sha256": hashlib.sha256((tmp_path / "restore-operation.json").read_bytes()).hexdigest()
    }).encode())
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
    historical_job_count = len(jobs)

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

    # Exercise the public issuer after an actual guard run has expired. This
    # keeps the original-attempt validator real while isolating the staged
    # release SHA, which is not available in this local synthetic fixture.
    clock = [time.time()]
    monkeypatch.setattr(contract, "_execution_source", lambda: ("1" * 40, "/fake/release"))
    monkeypatch.setattr(contract.time, "time", lambda: clock[0])
    first_authority_path = contract.issue_authority(tmp_path, timeout=300)
    first_authority = json.loads(first_authority_path.read_text())
    owner_token = first_authority["admission_token"]
    row = {"Id": container_id, "Image": "image-id", "RestartCount": 0,
        "Config": {"Labels": {"ade.hindsight.restore.token": token,
                               "com.docker.compose.project": operation["compose"]["project"]}},
        "Mounts": [{"Name": volume}],
        "State": {"Status": "running", "StartedAt": "historical-start", "OOMKilled": False}}

    def expiry_command(command, **_kwargs):
        if command[1] == "stop":
            row["State"]["Status"] = "exited"
        return SimpleNamespace(stdout=json.dumps([row]).encode())

    monkeypatch.setattr(expiry.subprocess, "run", expiry_command)
    monkeypatch.setattr(expiry.time, "time", lambda: clock[0])
    monkeypatch.setattr(expiry.time, "sleep", lambda _seconds: clock.__setitem__(
        0, first_authority["deadline"] + 1))
    read_fd, write_fd = os.pipe()
    os.write(write_fd, b"1")
    os.close(write_fd)
    assert expiry.run(tmp_path, token, first_authority_path.name, container_id,
                      "historical-start", first_authority["deadline"],
                      hashlib.sha256(first_authority_path.read_bytes()).hexdigest(),
                      owner_token, read_fd) == 0
    expiry_job = {"schema": 1, "token": owner_token, "operation_token": token,
                  "operation": "post-restore-recovery-expiry",
                  "created_at": first_authority["issued_at"] + 1,
                  "deadline": first_authority["deadline"], "container_id": container_id}
    _write(tmp_path / f"restore-{token}-{owner_token}-job.json", json.dumps(expiry_job).encode())
    jobs.append(expiry_job)
    second_authority_path = contract.issue_authority(tmp_path, timeout=300)
    assert second_authority_path != first_authority_path
    assert clock[0] > first_authority["deadline"]

    archived = retirement_archive._archive(
        tmp_path, token, authority_path, tmp_path / "session", operation,
        "2" * 40, {"status": "captured_failed_attempt"})
    retirement = json.loads((archived / "retirement.json").read_text())
    absent = set(retirement["absent_original_results"])
    assert historical_job_count == 194
    assert f"job-{failed_token}.result.json" in absent
    assert f"restore-{token}-{failed_token}-result.json" in absent
    terminal_table = next(job for job in jobs
                          if job["operation"] == "restore-snapshot-table-unit_entities")
    assert f"restore-{token}-{terminal_table['token']}-result.json" in absent
    assert not any(f"job-{job['token']}.result.json" in absent
                   for job in jobs if job["operation"] == restore_process.IDENTITY_LIST_READBACK
                   and job["token"] != failed_token)

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


def test_identity_list_readback_rejects_unrecognized_calculated_command_hash(tmp_path):
    token, volume = "e" * 32, "restore-volume"
    successful = _success_job(tmp_path, token, restore_process.IDENTITY_LIST_READBACK,
        ["docker", "ps", "-aq", "--no-trunc"], 1,
        command_hash=hashlib.sha256(b"unrecognized command").hexdigest())
    failed_token = "f" * 32
    failed = {"token": failed_token, "operation": restore_process.IDENTITY_LIST_READBACK,
              "command_sha256": hashlib.sha256(
                  json.dumps(["docker", "ps", "-aq", "--no-trunc"]).encode()).hexdigest(),
              "identity": {"cmd_sha256": hashlib.sha256(b"").hexdigest()}}
    _write(tmp_path / f"restore-{token}-{failed_token}-job.json", json.dumps(failed).encode())

    with pytest.raises(RuntimeError, match="identity_list_receipt_incomplete"):
        contract._failed_identity_list_readback(tmp_path, token, [successful, failed], volume)


def test_snapshot_prefix_accepts_a_short_ordered_prefix_with_terminal_child_only(tmp_path):
    token, container_id = "c" * 32, "d" * 64
    jobs = []
    tables = restore_snapshot.candidate_database.SNAPSHOT_TABLES[:3]
    for index, table in enumerate(tables):
        command = ["docker", "exec", "-i", container_id, "psql", "-U",
                   "hindsight_probe", "-d", "hindsight_probe", "-At", "-c",
                   restore_snapshot.table_query(table)]
        jobs.append(_success_job(tmp_path, token, f"restore-snapshot-table-{table}",
                                 command, float(index), wrapper=index < 2))

    terminal = contract._validate_snapshot_prefix(tmp_path, token, container_id, jobs)

    assert terminal is jobs[-1]
