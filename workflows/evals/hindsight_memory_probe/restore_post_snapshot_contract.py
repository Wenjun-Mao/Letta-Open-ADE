"""Immutable admission and original-attempt proof for post-restore recovery."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
import uuid
from pathlib import Path

from . import restore, restore_process, restore_snapshot
from .receipts import ReceiptStore

SCOPES = [
    "read_only_snapshot", "start_exact_restore_container", "stop_exact_restore_container",
    "archive_evidence", "remove_exact_restore_container", "remove_exact_restore_volume",
]
FAILED_MONITOR_JOB = restore_process.IDENTITY_LIST_READBACK


def _require_successful_job(directory: Path, token: str, job: dict) -> None:
    child_path = directory / f"job-{job['token']}.result.json"
    wrapper_path = directory / f"restore-{token}-{job['token']}-result.json"
    if (child_path.is_symlink() or wrapper_path.is_symlink()
            or not child_path.is_file() or not wrapper_path.is_file()):
        raise RuntimeError("restore_post_snapshot_recovery_job_result_missing")
    child, wrapper = json.loads(child_path.read_text()), json.loads(wrapper_path.read_text())
    if (not isinstance(child, dict) or type(child.get("exit_code")) is not int
            or child["exit_code"] != 0 or not isinstance(wrapper, dict)
            or wrapper.get("operation") != job.get("operation")
            or type(wrapper.get("exit_code")) is not int or wrapper["exit_code"] != 0
            or wrapper.get("command_sha256") != job.get("command_sha256")):
        raise RuntimeError("restore_post_snapshot_recovery_job_result_invalid")


def _failed_identity_list_readback(directory: Path, token: str, jobs: list[dict],
                                   volume: str) -> dict:
    """Separate one failed empty registration from completed nested list reads."""
    global_list = ["docker", "ps", "-aq", "--no-trunc"]
    volume_list = ["docker", "volume", "ls", "-q", "--filter", f"name={volume}"]
    allowed_command_hashes = {
        hashlib.sha256(json.dumps(command).encode()).hexdigest()
        for command in (global_list, volume_list)
    }
    failed_command_hash = hashlib.sha256(json.dumps(global_list).encode()).hexdigest()
    empty_command_hash = hashlib.sha256(b"").hexdigest()
    failed = []
    for job in jobs:
        child_path = directory / f"job-{job['token']}.result.json"
        wrapper_path = directory / f"restore-{token}-{job['token']}-result.json"
        if child_path.is_symlink() or wrapper_path.is_symlink():
            raise RuntimeError("restore_post_snapshot_recovery_identity_list_receipt_invalid")
        child_exists, wrapper_exists = child_path.exists(), wrapper_path.exists()
        identity_hash = job.get("identity", {}).get("cmd_sha256")
        if (identity_hash == empty_command_hash and not child_exists and not wrapper_exists
                and job.get("command_sha256") == failed_command_hash):
            failed.append(job)
            continue
        if (not isinstance(identity_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", identity_hash)
                or identity_hash == empty_command_hash or not child_exists or not wrapper_exists
                or not isinstance(job.get("command_sha256"), str)
                or job["command_sha256"] not in allowed_command_hashes):
            raise RuntimeError("restore_post_snapshot_recovery_identity_list_receipt_incomplete")
        _require_successful_job(directory, token, job)
    if len(failed) != 1:
        raise RuntimeError("restore_post_snapshot_recovery_failed_registration_invalid")
    return failed[0]


def _validate_snapshot_prefix(directory: Path, token: str, container_id: str,
                              jobs: list[dict]) -> dict:
    """Validate the exact ordered table-query prefix before the failed registration."""
    tables = restore_snapshot.candidate_database.SNAPSHOT_TABLES
    ordered = sorted(jobs, key=lambda job: job.get("created_at", -1))
    operations = [job.get("operation", "").removeprefix("restore-snapshot-table-")
                  for job in ordered]
    if (not ordered or len(ordered) >= len(tables)
            or operations != list(tables[:len(operations)])
            or any(type(job.get("created_at")) not in (int, float)
                   or not math.isfinite(job["created_at"]) for job in ordered)
            or any(earlier["created_at"] >= later["created_at"]
                   for earlier, later in zip(ordered, ordered[1:]))):
        raise RuntimeError("restore_post_snapshot_recovery_snapshot_prefix_invalid")

    for job in ordered:
        table = job["operation"].removeprefix("restore-snapshot-table-")
        query = restore_snapshot.table_query(table)
        command = ["docker", "exec", "-i", container_id, "psql", "-U",
                   "hindsight_probe", "-d", "hindsight_probe", "-At", "-c", query]
        child = directory / f"job-{job['token']}.result.json"
        if (job.get("command_sha256") != hashlib.sha256(json.dumps(command).encode()).hexdigest()
                or child.is_symlink() or not child.is_file()
                or json.loads(child.read_text()).get("exit_code") != 0):
            raise RuntimeError("restore_post_snapshot_recovery_snapshot_job_invalid")

    for job in ordered[:-1]:
        _require_successful_job(directory, token, job)
    last_wrapper = directory / f"restore-{token}-{ordered[-1]['token']}-result.json"
    if last_wrapper.exists() or last_wrapper.is_symlink():
        raise RuntimeError("restore_post_snapshot_recovery_snapshot_terminal_invalid")
    return ordered[-1]

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _json_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def _write_once(directory: Path, name: str, value: dict) -> Path:
    path = directory / name
    if path.exists():
        if path.is_symlink() or not path.is_file() or json.loads(path.read_text()) != value:
            raise RuntimeError("restore_post_snapshot_recovery_receipt_conflict")
        return path
    ReceiptStore(directory).write(name, value)
    path.chmod(0o400)
    return path

def _execution_source() -> tuple[str, str]:
    release = Path(__file__).resolve().parents[3]
    identity = restore.releases.verify(release)
    return identity["source_sha"], str(release)

def _authority(path: Path, directory: Path, operation: dict, failure_path: Path,
               cleanup_path: Path) -> tuple[dict, str, str]:
    token = operation["token"]
    if (not re.fullmatch(rf"restore-{token}-post-restore-authority-[a-f0-9]{{32}}\.json", path.name)
            or path.is_symlink() or not path.is_file() or path.parent.resolve() != directory.resolve()
            or path.stat().st_mode & 0o377):
        raise RuntimeError("restore_post_snapshot_recovery_authority_not_immutable")
    value = json.loads(path.read_text())
    fields = {"schema", "kind", "admission_token", "token", "operation_sha256",
              "failure_sha256", "cleanup_sha256", "container_id", "volume",
              "recovery_source_sha", "issued_at", "deadline", "scopes"}
    source_sha, source_path = _execution_source()
    now = time.time()
    if (not isinstance(value, dict) or set(value) != fields or value.get("schema") != 1
            or value.get("kind") != "failed_post_restore_snapshot_recovery"
            or not re.fullmatch(r"[a-f0-9]{32}", value.get("admission_token", ""))
            or value.get("admission_token") != path.stem.removeprefix(f"restore-{token}-post-restore-authority-")
            or value.get("token") != token
            or value.get("operation_sha256") != _sha(directory / "restore-operation.json")
            or value.get("failure_sha256") != _sha(failure_path)
            or value.get("cleanup_sha256") != _sha(cleanup_path)
            or value.get("container_id") != json.loads((directory / f"restore-{token}-create.result.json").read_text()).get("container_id")
            or value.get("volume") != operation["compose"]["volume"]
            or value.get("recovery_source_sha") != source_sha or value.get("scopes") != SCOPES
            or type(value.get("issued_at")) not in (int, float) or not math.isfinite(value["issued_at"])
            or type(value.get("deadline")) not in (int, float) or not math.isfinite(value["deadline"])
            or value["deadline"] <= now or value["issued_at"] > now
            or value["deadline"] > value["issued_at"] + 600):
        raise RuntimeError("restore_post_snapshot_recovery_authority_invalid")
    return value, source_sha, source_path

def issue_authority(directory: Path, timeout: int = 300) -> Path:
    """Create the explicit, short-lived authority for this exact failed attempt."""
    from .restore_post_snapshot_admission import _validate_original

    if type(timeout) is not int or not 1 <= timeout <= 600:
        raise RuntimeError("restore_post_snapshot_recovery_authority_timeout_invalid")
    from .restore_retirement import admission_lease
    from . import supervisor

    with admission_lease(directory):
        operation = restore.read_operation(directory)
        token = operation["token"]
        proof, _archive_path, _snapshot = _validate_original(directory, operation)
        failure = directory / f"restore-{token}-failure.result.json"
        cleanup = directory / f"restore-{token}-cleanup.result.json"
        source_sha, _source_path = _execution_source()
        issued_at = time.time()
        deadline = min(issued_at + timeout, supervisor.WORK_CUTOFF)
        if deadline <= issued_at:
            raise RuntimeError("restore_post_snapshot_recovery_authority_deadline_elapsed")
        admission_token = uuid.uuid4().hex
        authority = {
            "schema": 1, "kind": "failed_post_restore_snapshot_recovery",
            "admission_token": admission_token, "token": token,
            "operation_sha256": _sha(directory / "restore-operation.json"),
            "failure_sha256": _sha(failure), "cleanup_sha256": _sha(cleanup),
            "container_id": proof["create"]["container_id"],
            "volume": operation["compose"]["volume"],
            "recovery_source_sha": source_sha, "issued_at": issued_at,
            "deadline": deadline, "scopes": SCOPES,
        }
        path = directory / f"restore-{token}-post-restore-authority-{admission_token}.json"
        _write_once(directory, path.name, authority)
        return path

def _container_identity(container: dict) -> dict:
    from .restore_cleanup_recovery_contract import _container_identity as identity
    return identity(container)
