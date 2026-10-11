"""Evidence-bound admission and identity contracts for failed-create cleanup."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path

from . import restore_retirement_archive as source_archive
from .campaign_clock import WORK_CUTOFF
from .receipts import ReceiptStore

RECOVERY_SECONDS = 600
STAGES = ("stop", "remove-container", "remove-volume")

def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _write_once(directory: Path, name: str, value: dict, *, readonly: bool = True) -> Path:
    path = directory / name
    if path.exists():
        if path.is_symlink() or not path.is_file() or json.loads(path.read_text()) != value:
            raise RuntimeError("restore_cleanup_recovery_receipt_conflict")
        return path
    ReceiptStore(directory).write(name, value)
    if readonly:
        path.chmod(0o400)
    return path


def _readback_admission(directory: Path, operation: dict, diagnosis_path: Path) -> dict:
    token = operation["token"]
    name = f"restore-{token}-cleanup-recovery-readback-admission.json"
    seal_name = f"restore-{token}-cleanup-recovery-readback-admission.seal.json"
    path, seal_path = directory / name, directory / seal_name
    operation_hash = source_archive.digest_file(directory / "restore-operation.json")
    diagnosis_hash = source_archive.digest_file(diagnosis_path)
    commands = ["docker ps", "docker inspect", "docker volume ls", "docker volume inspect"]
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o377:
            raise RuntimeError("restore_cleanup_recovery_readback_admission_invalid")
        value = json.loads(path.read_text())
        seal = json.loads(seal_path.read_text()) if seal_path.is_file() and not seal_path.is_symlink() else {}
        if (set(value) != {"schema", "kind", "token", "operation_sha256", "diagnosis_sha256",
                           "deadline", "commands", "created_at"}
                or value.get("schema") != 1
                or seal.get("token") != token or seal.get("sha256") != source_archive.digest_file(path)
                or value.get("kind") != "read_only_restore_cleanup_recovery"
                or value.get("token") != token or value.get("operation_sha256") != operation_hash
                or value.get("diagnosis_sha256") != diagnosis_hash or value.get("commands") != commands
                or type(value.get("deadline")) not in (int, float) or not math.isfinite(value["deadline"])
                or value["deadline"] > WORK_CUTOFF
                or type(value.get("created_at")) not in (int, float) or not math.isfinite(value["created_at"])
                or value["deadline"] > value["created_at"] + RECOVERY_SECONDS
                or value["deadline"] <= value["created_at"]):
            raise RuntimeError("restore_cleanup_recovery_readback_admission_invalid")
    else:
        deadline = min(WORK_CUTOFF, time.time() + RECOVERY_SECONDS)
        if deadline <= time.time():
            raise RuntimeError("restore_cleanup_recovery_readback_deadline_unavailable")
        value = {"schema": 1, "kind": "read_only_restore_cleanup_recovery", "token": token,
                 "operation_sha256": operation_hash, "diagnosis_sha256": diagnosis_hash,
                 "deadline": deadline, "commands": commands, "created_at": time.time()}
        _write_once(directory, name, value)
        _write_once(directory, seal_name, {"schema": 1, "token": token,
                                           "sha256": source_archive.digest_file(path)})
    if time.time() >= value["deadline"]:
        raise RuntimeError("restore_cleanup_recovery_readback_deadline_elapsed")
    return value


def _admission(directory: Path, operation: dict, diagnosis_path: Path, diagnosis: dict,
               container: dict, volume: dict) -> dict:
    token = operation["token"]
    path = directory / f"restore-{token}-cleanup-recovery-admission.json"
    seal_path = directory / f"restore-{token}-cleanup-recovery-admission.seal.json"
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o377:
            raise RuntimeError("restore_cleanup_recovery_admission_invalid")
        value = json.loads(path.read_text())
        seal = json.loads(seal_path.read_text()) if seal_path.is_file() and not seal_path.is_symlink() else {}
        if (set(value) != {"schema", "kind", "token", "operation_sha256", "diagnosis_sha256",
                           "container_identity", "volume_identity", "deadline", "created_at"}
                or seal.get("token") != token or seal.get("sha256") != source_archive.digest_file(path)
                or value.get("schema") != 1 or value.get("kind") != "restore_cleanup_only_recovery"
                or value.get("token") != token
                or value.get("operation_sha256") != source_archive.digest_file(directory / "restore-operation.json")
                or value.get("diagnosis_sha256") != source_archive.digest_file(diagnosis_path)
                or value.get("container_identity") != (container if "id" in container else _container_identity(container))
                or value.get("volume_identity") != _volume_identity(volume)
                or type(value.get("deadline")) not in (int, float) or not math.isfinite(value["deadline"])
                or value["deadline"] > WORK_CUTOFF
                or type(value.get("created_at")) not in (int, float) or not math.isfinite(value["created_at"])
                or value["deadline"] > value["created_at"] + RECOVERY_SECONDS
                or value["deadline"] <= value["created_at"]):
            raise RuntimeError("restore_cleanup_recovery_admission_invalid")
        if time.time() >= value["deadline"]:
            raise RuntimeError("restore_cleanup_recovery_deadline_elapsed")
        return value
    deadline = min(WORK_CUTOFF, time.time() + RECOVERY_SECONDS)
    if deadline <= time.time():
        raise RuntimeError("restore_cleanup_recovery_deadline_unavailable")
    value = {"schema": 1, "kind": "restore_cleanup_only_recovery", "token": token,
             "operation_sha256": source_archive.digest_file(directory / "restore-operation.json"),
             "diagnosis_sha256": source_archive.digest_file(diagnosis_path),
             "container_identity": _container_identity(container),
             "volume_identity": _volume_identity(volume), "deadline": deadline,
             "created_at": time.time()}
    _write_once(directory, path.name, value)
    _write_once(directory, seal_path.name, {"schema": 1, "token": token,
                                             "sha256": source_archive.digest_file(path)})
    return value


def _container_identity(row: dict) -> dict:
    labels = row.get("Config", {}).get("Labels") or {}
    return {"id": row.get("Id"), "image_id": row.get("Image"),
            "config_image": row.get("Config", {}).get("Image"), "labels": labels,
            "environment": row.get("Config", {}).get("Env") or [],
            "started_at": row.get("State", {}).get("StartedAt"),
            "oom_killed": row.get("State", {}).get("OOMKilled"),
            "restart_count": row.get("RestartCount"),
            "network_mode": row.get("HostConfig", {}).get("NetworkMode"),
            "memory": row.get("HostConfig", {}).get("Memory"),
            "nano_cpus": row.get("HostConfig", {}).get("NanoCpus"),
            "ports": row.get("NetworkSettings", {}).get("Ports"),
            "mounts": [{key: mount.get(key) for key in ("Type", "Name", "Source", "Destination", "Driver", "Mode", "RW", "Propagation")}
                       for mount in row.get("Mounts", [])]}


def _volume_identity(row: dict) -> dict:
    return {key: row.get(key) for key in ("Name", "Driver", "Scope", "Options", "Mountpoint", "CreatedAt", "Labels")}


def _diagnosis(directory: Path, operation: dict, path: Path) -> dict:
    from . import restore_process

    token = operation["token"]
    failure_path = directory / f"restore-{token}-failure.result.json"
    intent_path = directory / f"restore-{token}-create.intent.json"
    fields = {"schema", "kind", "token", "operation_sha256", "failure_sha256",
              "create_intent_sha256", "create_job_token", "create_job_registration_sha256",
              "create_child_result_sha256", "container_id", "container_started_at", "image_id",
              "container_identity_sha256", "create_wrapper_result_absent", "volume",
              "volume_identity_sha256", "controller_gone", "processes_gone",
              "main_stopped", "baseline_unchanged"}
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o377:
        raise RuntimeError("restore_cleanup_recovery_diagnosis_not_immutable")
    value = json.loads(path.read_text())
    if (set(value) != fields or value.get("schema") != 1
            or value.get("kind") != "created_but_unpublished_cleanup_only"
            or value.get("token") != token
            or value.get("operation_sha256") != source_archive.digest_file(directory / "restore-operation.json")
            or not failure_path.is_file() or value.get("failure_sha256") != source_archive.digest_file(failure_path)
            or not intent_path.is_file() or value.get("create_intent_sha256") != source_archive.digest_file(intent_path)
            or value.get("create_wrapper_result_absent") is not True
            or any(value.get(key) is not True for key in ("controller_gone", "processes_gone", "main_stopped", "baseline_unchanged"))):
        raise RuntimeError("restore_cleanup_recovery_diagnosis_invalid")
    present_intents = {p.name for p in directory.glob(f"restore-{token}-*.intent.json")}
    allowed_intents = {f"restore-{token}-create.intent.json"}
    recovery_intents = {f"restore-{token}-cleanup-recovery-{stage}.intent.json" for stage in STAGES}
    forbidden_results = [f"restore-{token}-{suffix}.result.json"
                         for suffix in ("create", "restore", "snapshot", "compare", "result")]
    if (not allowed_intents.issubset(present_intents)
            or not present_intents.issubset(allowed_intents | recovery_intents)
            or any((directory / name).exists() for name in forbidden_results)):
        raise RuntimeError("restore_cleanup_recovery_after_create_progress_rejected")
    failure = json.loads(failure_path.read_text())
    intent = json.loads(intent_path.read_text())
    if (failure.get("token") != token or failure.get("status") != "failed"
            or failure.get("stage") != "create" or failure.get("reason") != "restore_unowned_container_detected"
            or intent.get("token") != token or intent.get("compose_sha256") != operation["compose"]["sha256"]
            or intent.get("project") != operation["compose"]["project"]
            or intent.get("volume") != operation["compose"]["volume"]):
        raise RuntimeError("restore_cleanup_recovery_failure_or_intent_invalid")
    controllers = list(directory.glob(f"restore-{token}-controller-*.json"))
    from . import host_guard as host

    if not controllers or any(host.identity_matches(json.loads(p.read_text()).get("identity", {})) for p in controllers):
        raise RuntimeError("restore_cleanup_recovery_controller_active")
    jobs = restore_process.registered_jobs(directory, token)
    create_jobs = [job for job in jobs if job.get("operation") == "compose-create"]
    allowed_cleanup_ops = {"cleanup-recovery-" + stage for stage in STAGES}
    other = [job for job in jobs if job.get("operation") != "compose-create"
             and job.get("operation") not in restore_process.READ_ONLY_HOST_OPERATIONS
             and job.get("operation") not in allowed_cleanup_ops]
    if len(create_jobs) != 1 or other or any(host.tagged_processes(job["token"]) for job in jobs):
        raise RuntimeError("restore_cleanup_recovery_job_set_invalid")
    cleanup_jobs = [job for job in jobs if job.get("operation") in allowed_cleanup_ops]
    for job in cleanup_jobs:
        stage = job["operation"].removeprefix("cleanup-recovery-")
        stage_intent = directory / f"restore-{token}-cleanup-recovery-{stage}.intent.json"
        if not stage_intent.is_file():
            raise RuntimeError("restore_cleanup_recovery_job_without_intent")
        command = json.loads(stage_intent.read_text()).get("command")
        if command is None or job.get("command_sha256") != hashlib.sha256(json.dumps(command).encode()).hexdigest():
            raise RuntimeError("restore_cleanup_recovery_job_command_mismatch")
    job = create_jobs[0]
    job_token = job["token"]
    registration_path = directory / f"restore-{token}-{job_token}-job.json"
    child_result_path = directory / f"job-{job_token}.result.json"
    wrapper_result_path = directory / f"restore-{token}-{job_token}-result.json"
    expected = ["docker", "compose", "--project-name", operation["compose"]["project"],
                "-f", operation["compose"]["path"], "up", "-d", "--pull", "never", "db"]
    if (job.get("command_sha256") != hashlib.sha256(json.dumps(expected).encode()).hexdigest()
            or value.get("create_job_token") != job_token
            or value.get("create_job_registration_sha256") != source_archive.digest_file(registration_path)
            or not child_result_path.is_file()
            or value.get("create_child_result_sha256") != source_archive.digest_file(child_result_path)
            or json.loads(child_result_path.read_text()).get("exit_code") != 0
            or wrapper_result_path.exists()):
        raise RuntimeError("restore_cleanup_recovery_create_proof_invalid")
    return value


def _source_proof(directory: Path, operation: dict) -> None:
    from . import restore
    from .restore_retirement import _verify_operation_sources

    registry, epoch, admission, evidence = restore._load_main(directory)
    _verify_operation_sources(directory, operation, registry, epoch, admission, evidence)


def _verify_diagnosis_container(diagnosis: dict, container: dict, volume: dict) -> None:
    volume_identity = _volume_identity(volume)
    if (container["Id"] != diagnosis["container_id"]
            or container["State"].get("StartedAt") != diagnosis["container_started_at"]
            or container["Image"] != diagnosis["image_id"]
            or _digest(_container_identity(container)) != diagnosis["container_identity_sha256"]
            or hashlib.sha256(json.dumps(volume_identity, sort_keys=True).encode()).hexdigest()
            != diagnosis["volume_identity_sha256"]
            or not re.fullmatch(r"[a-f0-9]{64}", container["Id"])
            or container["State"].get("OOMKilled") is not False
            or container.get("RestartCount") != 0):
        raise RuntimeError("restore_cleanup_recovery_resource_identity_invalid")
