"""Proof that the retained failed restore matches the immutable P4 incident."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

from . import host_guard, restore, restore_process
from .restore_post_snapshot_contract import (
    FAILED_MONITOR_JOB, SCOPES, _failed_identity_list_readback, _require_successful_job,
    _sha, _validate_snapshot_prefix,
)


def _validate_recovery_authority(directory: Path, operation: dict, failure_path: Path,
                                 cleanup_path: Path, job: dict) -> None:
    admission_token = job.get("recovery_admission_token")
    authority_hash = job.get("recovery_authority_sha256")
    if job.get("operation") == "post-restore-recovery-expiry":
        admission_token = job.get("token")
    if not isinstance(admission_token, str) or not re.fullmatch(r"[a-f0-9]{32}", admission_token):
        raise RuntimeError("restore_post_snapshot_recovery_job_authority_invalid")
    token = operation["token"]
    path = directory / f"restore-{token}-post-restore-authority-{admission_token}.json"
    if (path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o377
            or job.get("operation") != "post-restore-recovery-expiry"
               and (not isinstance(authority_hash, str) or _sha(path) != authority_hash)):
        raise RuntimeError("restore_post_snapshot_recovery_job_authority_invalid")
    authority = json.loads(path.read_text())
    created_at = job.get("created_at")
    cleanup_time = json.loads(cleanup_path.read_text()).get("time")
    authority_fields = {"schema", "kind", "admission_token", "token", "operation_sha256",
                        "failure_sha256", "cleanup_sha256", "container_id", "volume",
                        "recovery_source_sha", "issued_at", "deadline", "scopes"}
    if (not isinstance(authority, dict)
            or set(authority) != authority_fields
            or authority.get("schema") != 1
            or authority.get("kind") != "failed_post_restore_snapshot_recovery"
            or authority.get("admission_token") != admission_token
            or authority.get("token") != token
            or authority.get("operation_sha256") != _sha(directory / "restore-operation.json")
            or authority.get("failure_sha256") != _sha(failure_path)
            or authority.get("cleanup_sha256") != _sha(cleanup_path)
            or authority.get("container_id") != json.loads(
                (directory / f"restore-{token}-create.result.json").read_text()).get("container_id")
            or authority.get("volume") != operation["compose"]["volume"]
            or not re.fullmatch(r"[a-f0-9]{40}", authority.get("recovery_source_sha", ""))
            or type(created_at) not in (int, float) or not math.isfinite(created_at)
            or type(authority.get("issued_at")) not in (int, float)
            or not math.isfinite(authority["issued_at"])
            or type(authority.get("deadline")) not in (int, float)
            or not math.isfinite(authority["deadline"])
            or type(cleanup_time) not in (int, float) or not math.isfinite(cleanup_time)
            or not cleanup_time < authority["issued_at"] <= created_at <= authority["deadline"]
            or authority["deadline"] > authority["issued_at"] + 600
            or authority.get("scopes") != SCOPES):
        raise RuntimeError("restore_post_snapshot_recovery_job_authority_invalid")
    if job.get("operation") == "post-restore-recovery-expiry":
        if (job.get("container_id") != authority["container_id"]
                or job.get("deadline") != authority["deadline"]):
            raise RuntimeError("restore_post_snapshot_recovery_job_authority_invalid")
        ready_path = directory / f"restore-{token}-{admission_token}-expiry.ready.json"
        result_path = directory / f"restore-{token}-{admission_token}-expiry.result.json"
        if (ready_path.is_symlink() or result_path.is_symlink()
                or not ready_path.is_file() or not result_path.is_file()
                or ready_path.stat().st_mode & 0o377 or result_path.stat().st_mode & 0o377):
            raise RuntimeError("restore_post_snapshot_recovery_expiry_receipt_missing")
        ready, result = json.loads(ready_path.read_text()), json.loads(result_path.read_text())
        if (ready != {"token": token, "expiry_token": admission_token,
                      "deadline": authority["deadline"], "ready": True}
                or result.get("token") != token or result.get("expiry_token") != admission_token
                or result.get("container_id") != authority["container_id"]
                or result.get("status") not in {"cancelled_before_database_restart",
                    "cancelled_after_database_stop", "expired_stop_completed", "drifted_container_stopped"}
                or result.get("container_status") != "exited"
                or result.get("oom_killed") is not False or result.get("restart_count") != 0
                or not isinstance(result.get("started_at"), str)
                or type(result.get("completed_at")) not in (int, float)
                or not math.isfinite(result["completed_at"])):
            raise RuntimeError("restore_post_snapshot_recovery_expiry_receipt_invalid")
    else:
        child_path = directory / f"job-{job['token']}.result.json"
        wrapper_path = directory / f"restore-{token}-{job['token']}-result.json"
        if child_path.exists() or wrapper_path.exists():
            _require_successful_job(directory, token, job)


def _validate_original(directory: Path, operation: dict) -> tuple[dict, Path, Path]:
    token = operation["token"]
    failure_path = directory / f"restore-{token}-failure.result.json"
    cleanup_path = directory / f"restore-{token}-cleanup.result.json"
    result_path = directory / f"restore-{token}-result.json"
    if (not failure_path.is_file() or failure_path.is_symlink()
            or not cleanup_path.is_file() or cleanup_path.is_symlink()
            or result_path.exists() or result_path.is_symlink()):
        raise RuntimeError("restore_post_snapshot_recovery_terminal_state_invalid")
    failure, cleanup = json.loads(failure_path.read_text()), json.loads(cleanup_path.read_text())
    failure_time, cleanup_time = failure.get("time"), cleanup.get("time")
    if (type(failure_time) not in (int, float) or not math.isfinite(failure_time)
            or type(cleanup_time) not in (int, float) or not math.isfinite(cleanup_time)
            or cleanup_time < failure_time):
        raise RuntimeError("restore_post_snapshot_recovery_failure_time_invalid")
    create_path = directory / f"restore-{token}-create.result.json"
    restore_path = directory / f"restore-{token}-restore.result.json"
    restore_intent_path = directory / f"restore-{token}-restore.intent.json"
    snapshot_result_path = directory / f"restore-{token}-snapshot.result.json"
    compare_result_path = directory / f"restore-{token}-compare.result.json"
    if (failure.get("token") != token or failure.get("status") != "failed"
            or failure.get("stage") != "snapshot"
            or failure.get("reason") != "restore_process_identity_changed"
            or cleanup.get("token") != token or cleanup.get("status") != "preserved_failed_state"
            or cleanup.get("reason") != "post_restore_snapshot_not_preserved"
            or cleanup.get("removed") is not False
            or not create_path.is_file() or create_path.is_symlink()
            or not restore_path.is_file() or restore_path.is_symlink()
            or not restore_intent_path.is_file() or restore_intent_path.is_symlink()
            or snapshot_result_path.exists() or snapshot_result_path.is_symlink()
            or compare_result_path.exists() or compare_result_path.is_symlink()
            or Path(operation["restore_root"], "canonical-snapshot.json").exists()
            or Path(operation["restore_root"], "canonical-snapshot.json").is_symlink()):
        raise RuntimeError("restore_post_snapshot_recovery_failure_contract_invalid")
    create = json.loads(create_path.read_text())
    restored = json.loads(restore_path.read_text())
    restore_intent = json.loads(restore_intent_path.read_text())
    if (create.get("token") != token or create.get("container_id") != cleanup.get("container_id")
            or create.get("volume") != operation["compose"]["volume"]
            or restored.get("token") != token or restored.get("status") != "completed"
            or restored.get("container_id") != create.get("container_id")
            or restored.get("archive_sha256") != operation["archive"]["sha256"]
            or restore_intent.get("container_id") != create.get("container_id")
            or restore_intent.get("archive_sha256") != operation["archive"]["sha256"]):
        raise RuntimeError("restore_post_snapshot_recovery_restore_proof_invalid")
    archive_path = Path(operation["archive"]["path"])
    original_snapshot = Path(operation["snapshot"]["path"])
    selection_path = Path(operation["selection"]["path"])
    if (not archive_path.is_file() or not original_snapshot.is_file() or not selection_path.is_file()
            or _sha(archive_path) != operation["archive"]["sha256"]
            or _sha(original_snapshot) != operation["snapshot"]["sha256"]
            or _sha(selection_path) != operation["selection"]["sha256"]):
        raise RuntimeError("restore_post_snapshot_recovery_source_changed")
    from .restore_cleanup_recovery_contract import _source_proof
    _source_proof(directory, operation)
    jobs = restore_process.registered_jobs(directory, token)
    if any(host_guard.tagged_processes(job["token"]) for job in jobs) or restore._controller_present(directory, token):
        raise RuntimeError("restore_post_snapshot_recovery_process_active")
    create_jobs = [job for job in jobs if job.get("operation") == "compose-create"]
    restore_jobs = [job for job in jobs if job.get("operation") == "pg-restore"]
    snapshot_jobs = [job for job in jobs
                     if isinstance(job.get("operation"), str)
                     and job["operation"].startswith("restore-snapshot-table-")]
    identity_list_jobs = [job for job in jobs if job.get("operation") == FAILED_MONITOR_JOB]
    identity_readback_jobs = [job for job in jobs
                              if job.get("operation") == restore_process.IDENTITY_READBACK]
    operator_readback_jobs = [job for job in jobs
                              if job.get("operation") == restore_process.OPERATOR_READBACK]
    operator_list_jobs = [job for job in jobs
                          if job.get("operation") == restore_process.OPERATOR_LIST_READBACK]
    readiness_jobs = [job for job in jobs if job.get("operation") == "database-readiness"]
    snapshot_probe_jobs = [job for job in jobs if job.get("operation") == "restore-snapshot-query"]
    preserve_stop_jobs = [job for job in jobs if job.get("operation") == "cleanup-preserve-stop"]
    recovery_operations = {
        "post-restore-recovery-expiry", "post-restore-recovery-readback",
        "post-restore-recovery-start", "post-restore-recovery-snapshot-query",
        "post-restore-recovery-stop", "post-restore-recovery-remove-container",
        "post-restore-recovery-remove-volume",
    }
    recovery_jobs = [job for job in jobs if job.get("operation") in recovery_operations]
    modeled_jobs = (create_jobs + restore_jobs + snapshot_jobs + identity_list_jobs
                    + identity_readback_jobs + operator_readback_jobs + operator_list_jobs
                    + readiness_jobs + snapshot_probe_jobs + preserve_stop_jobs + recovery_jobs)
    other = [job for job in jobs if job not in modeled_jobs]
    if (len(create_jobs) != 1 or len(restore_jobs) != 1 or not identity_list_jobs
            or not identity_readback_jobs or not operator_readback_jobs or not operator_list_jobs or other
            or len(readiness_jobs) != 1 or len(snapshot_probe_jobs) != 1
            or len(preserve_stop_jobs) != 1):
        raise RuntimeError("restore_post_snapshot_recovery_job_set_invalid")
    if len(create_jobs) == len(restore_jobs) == 1:
        create_command = ["docker", "compose", "--project-name", operation["compose"]["project"],
                          "-f", operation["compose"]["path"], "up", "-d", "--pull", "never", "db"]
        restore_command = ["docker", "exec", "-i", create["container_id"], "pg_restore",
                           "--exit-on-error", "--single-transaction", "--no-owner", "--no-acl",
                           "-U", "hindsight_probe", "-d", "hindsight_probe"]
        expected_commands = {create_jobs[0]["token"]: create_command,
                             restore_jobs[0]["token"]: restore_command}
    else:
        expected_commands = {}
    for job in create_jobs + restore_jobs:
        child = directory / f"job-{job['token']}.result.json"
        wrapper = directory / f"restore-{token}-{job['token']}-result.json"
        if (not child.is_file() or not wrapper.is_file()
                or job.get("command_sha256") != hashlib.sha256(
                    json.dumps(expected_commands[job["token"]]).encode()).hexdigest()
                or json.loads(child.read_text()).get("exit_code") != 0
                or json.loads(wrapper.read_text()).get("exit_code") != 0
                or json.loads(wrapper.read_text()).get("command_sha256") != job.get("command_sha256")):
            raise RuntimeError("restore_post_snapshot_recovery_command_not_completed")
    last_snapshot_job = _validate_snapshot_prefix(directory, token, create["container_id"], snapshot_jobs)

    readiness_command = ["docker", "exec", "-i", create["container_id"], "psql", "-U",
        "hindsight_probe", "-d", "hindsight_probe", "-At", "-c", "SELECT current_database()"]
    if readiness_jobs[0].get("command_sha256") != hashlib.sha256(
            json.dumps(readiness_command).encode()).hexdigest():
        raise RuntimeError("restore_post_snapshot_recovery_readiness_command_invalid")
    _require_successful_job(directory, token, readiness_jobs[0])
    if snapshot_probe_jobs[0].get("command_sha256") != hashlib.sha256(
            json.dumps(readiness_command).encode()).hexdigest():
        raise RuntimeError("restore_post_snapshot_recovery_snapshot_probe_command_invalid")
    _require_successful_job(directory, token, snapshot_probe_jobs[0])
    preserve_stop_command = ["docker", "stop", "--time", "20", create["container_id"]]
    if preserve_stop_jobs[0].get("command_sha256") != hashlib.sha256(
            json.dumps(preserve_stop_command).encode()).hexdigest():
        raise RuntimeError("restore_post_snapshot_recovery_preserve_stop_command_invalid")
    _require_successful_job(directory, token, preserve_stop_jobs[0])
    for job in identity_readback_jobs + operator_readback_jobs + operator_list_jobs:
        if (type(job.get("created_at")) not in (int, float)
                or not math.isfinite(job["created_at"]) or job["created_at"] > cleanup_time):
            raise RuntimeError("restore_post_snapshot_recovery_original_readback_time_invalid")
        _require_successful_job(directory, token, job)
    for job in identity_list_jobs:
        if (type(job.get("created_at")) not in (int, float)
                or not math.isfinite(job["created_at"]) or job["created_at"] > cleanup_time):
            raise RuntimeError("restore_post_snapshot_recovery_original_readback_time_invalid")

    failed = _failed_identity_list_readback(
        directory, token, identity_list_jobs, operation["compose"]["volume"])
    if (not (last_snapshot_job["created_at"] < failed["created_at"]
             <= last_snapshot_job["deadline"])
            or failed["created_at"] > failure_time
            or failed["created_at"] > cleanup_time):
        raise RuntimeError("restore_post_snapshot_recovery_failure_not_in_snapshot_monitor")
    for job in recovery_jobs:
        if (type(job.get("created_at")) not in (int, float)
                or not math.isfinite(job["created_at"]) or job["created_at"] <= cleanup_time):
            raise RuntimeError("restore_post_snapshot_recovery_job_time_invalid")
        _validate_recovery_authority(directory, operation, failure_path, cleanup_path, job)
    return {"create": create, "restore": restored, "failed_job": failed}, archive_path, original_snapshot
