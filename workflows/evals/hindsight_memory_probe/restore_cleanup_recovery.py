"""Sealed cleanup-only recovery for a failed Compose create with lost readback."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

from . import restore_retirement_archive as archive
from .receipts import ReceiptStore
from .campaign_clock import WORK_CUTOFF

RECOVERY_SECONDS = 600


def _write_immutable(directory: Path, name: str, value: dict) -> Path:
    path = directory / name
    ReceiptStore(directory).write(name, value)
    path.chmod(0o400)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return path


def _verify_terminal(directory: Path, operation: dict, diagnosis_path: Path) -> tuple[dict, dict]:
    from . import host_guard as host, restore, restore_database as db, restore_process

    token = operation["token"]
    diagnosis = json.loads(diagnosis_path.read_text())
    failure_path = directory / f"restore-{token}-failure.result.json"
    create_intent = directory / f"restore-{token}-create.intent.json"
    create_result = directory / f"restore-{token}-create.result.json"
    if (diagnosis_path.is_symlink() or not diagnosis_path.is_file()
            or diagnosis_path.stat().st_mode & 0o222 or diagnosis_path.stat().st_mode & 0o077):
        raise RuntimeError("restore_cleanup_recovery_diagnosis_not_immutable")
    fields = {"schema", "kind", "token", "operation_sha256", "failure_sha256",
              "create_intent_sha256", "create_job_token", "create_job_result_sha256",
              "container_id", "container_started_at", "image_id", "volume",
              "volume_identity_sha256", "controller_gone", "processes_gone",
              "main_stopped", "baseline_unchanged"}
    if (set(diagnosis) != fields or diagnosis.get("schema") != 1
            or diagnosis.get("kind") != "created_but_unpublished_cleanup_only"
            or diagnosis.get("token") != token
            or diagnosis.get("operation_sha256") != archive.digest_file(directory / "restore-operation.json")
            or diagnosis.get("failure_sha256") != archive.digest_file(failure_path)
            or diagnosis.get("create_intent_sha256") != archive.digest_file(create_intent)
            or any(diagnosis.get(key) is not True for key in ("controller_gone", "processes_gone", "main_stopped", "baseline_unchanged"))
            or create_result.exists() or not failure_path.is_file() or not create_intent.is_file()):
        raise RuntimeError("restore_cleanup_recovery_diagnosis_invalid")
    failure = json.loads(failure_path.read_text())
    if (failure.get("status") != "failed" or failure.get("stage") != "create"
            or failure.get("reason") != "restore_unowned_container_detected"):
        raise RuntimeError("restore_cleanup_recovery_failure_stage_invalid")
    controllers = list(directory.glob(f"restore-{token}-controller-*.json"))
    if not controllers or any(host.identity_matches(json.loads(p.read_text()).get("identity", {})) for p in controllers):
        raise RuntimeError("restore_cleanup_recovery_controller_active")
    jobs = restore_process.registered_jobs(directory, token)
    create_jobs = [job for job in jobs if job.get("operation") == "compose-create"]
    if len(create_jobs) != 1 or any(host.tagged_processes(job["token"]) for job in jobs):
        raise RuntimeError("restore_cleanup_recovery_job_identity_invalid")
    job = create_jobs[0]
    job_token = job["token"]
    job_result_path = directory / f"job-{job_token}.result.json"
    operation_result_path = directory / f"restore-{token}-{job_token}-result.json"
    expected_command = ["docker", "compose", "--project-name", operation["compose"]["project"],
                        "-f", operation["compose"]["path"], "up", "-d", "--pull", "never", "db"]
    command_hash = hashlib.sha256(json.dumps(expected_command).encode()).hexdigest()
    job_result = json.loads(job_result_path.read_text())
    process_result = json.loads(operation_result_path.read_text())
    if (job.get("command_sha256") != command_hash or job_result.get("exit_code") != 0
            or process_result.get("operation") != "compose-create" or process_result.get("exit_code") != 0
            or diagnosis.get("create_job_token") != job_token
            or diagnosis.get("create_job_result_sha256") != archive.digest_file(operation_result_path)):
        raise RuntimeError("restore_cleanup_recovery_create_proof_invalid")
    registry, epoch, admission, evidence = restore._load_main(directory)
    from .restore_retirement import _verify_operation_sources

    _verify_operation_sources(directory, operation, registry, epoch, admission, evidence)
    restore._verify_host(directory, registry, {"containers": operation["finalization"]["containers"]}, prospective=False,
                         allow_restore_creation=True)
    db.verify_compose(operation)
    container = db.restore_container(operation, allow_unregistered=True)
    volume = db.verify_volume(operation, allow_unregistered=True)
    volume_identity = {key: volume.get(key) for key in
                       ("Name", "Driver", "Scope", "Options", "Mountpoint", "CreatedAt")} if volume else None
    if (container is None or volume is None or container["Id"] != diagnosis.get("container_id")
            or operation["compose"]["volume"] != diagnosis.get("volume")
            or container["State"].get("StartedAt") != diagnosis.get("container_started_at")
            or container["Image"] != diagnosis.get("image_id")
            or hashlib.sha256(json.dumps(volume_identity, sort_keys=True).encode()).hexdigest()
            != diagnosis.get("volume_identity_sha256")
            or not re.fullmatch(r"[a-f0-9]{64}", container["Id"])
            or container["State"]["Status"] not in {"running", "exited"}
            or container["State"].get("OOMKilled") is not False or container.get("RestartCount") != 0):
        raise RuntimeError("restore_cleanup_recovery_resource_identity_invalid")
    if db.restore_container(operation, allow_unregistered=True) != container:
        raise RuntimeError("restore_cleanup_recovery_resource_changed")
    return diagnosis, container


def recover(directory: Path, diagnosis_path: Path) -> dict:
    from . import restore, restore_cleanup, restore_database as db

    operation = restore.read_operation(directory)
    token = operation["token"]
    deadline = min(WORK_CUTOFF, time.time() + RECOVERY_SECONDS)
    if deadline <= time.time():
        raise RuntimeError("restore_cleanup_recovery_deadline_unavailable")
    diagnosis, container = _verify_terminal(directory, operation, diagnosis_path)
    admission = {"schema": 1, "kind": "restore_cleanup_only_recovery", "token": token,
                 "operation_sha256": archive.digest_file(directory / "restore-operation.json"),
                 "diagnosis_sha256": archive.digest_file(diagnosis_path),
                 "container_id": container["Id"], "container_started_at": container["State"]["StartedAt"],
                 "image_id": container["Image"], "volume": operation["compose"]["volume"],
                 "volume_identity_sha256": diagnosis["volume_identity_sha256"],
                 "deadline": deadline, "created_at": time.time()}
    admission_path = directory / f"restore-{token}-cleanup-recovery-admission.json"
    admission_seal = directory / f"restore-{token}-cleanup-recovery-admission.seal.json"
    if admission_path.exists():
        existing = json.loads(admission_path.read_text())
        if (admission_path.is_symlink() or admission_path.stat().st_mode & 0o222
                or not admission_seal.is_file() or admission_seal.is_symlink()
                or json.loads(admission_seal.read_text()).get("sha256") != archive.digest_file(admission_path)
                or any(existing.get(key) != admission.get(key) for key in
                       ("schema", "kind", "token", "operation_sha256", "diagnosis_sha256", "container_id",
                        "container_started_at", "image_id", "volume", "volume_identity_sha256"))
                or existing.get("deadline", 0) > WORK_CUTOFF):
            raise RuntimeError("restore_cleanup_recovery_admission_conflict")
        admission = existing
    else:
        _write_immutable(directory, admission_path.name, admission)
        _write_immutable(directory, admission_seal.name, {"schema": 1, "token": token,
                         "sha256": archive.digest_file(admission_path)})
    deadline = admission["deadline"]
    op = {**operation, "cleanup_deadline": deadline,
          "_cleanup_recovery_container_id": container["Id"]}
    if time.time() >= deadline:
        raise RuntimeError("restore_cleanup_recovery_deadline_elapsed")
    with restore_cleanup.registered_host_readback(directory, op):
        current = db.restore_container(op, allow_unregistered=True)
        if current is None or current["Id"] != container["Id"]:
            raise RuntimeError("restore_cleanup_recovery_container_changed")
        if current["State"]["Status"] == "running":
            restore_cleanup._docker_cleanup_command(directory, op,
                ["docker", "stop", "--time", "20", container["Id"]], "recovery-stop")
        current = db.restore_container(op, allow_unregistered=True)
        if current is None or current["Id"] != container["Id"] or current["State"]["Status"] == "running":
            raise RuntimeError("restore_cleanup_recovery_stop_unproven")
        restore_cleanup._docker_cleanup_command(directory, op, ["docker", "rm", container["Id"]], "recovery-remove-container")
        consumers = db.docker_text(["docker", "ps", "-aq", "--no-trunc", "--filter",
                                    "volume=" + operation["compose"]["volume"]])
        if consumers:
            raise RuntimeError("restore_cleanup_recovery_volume_consumer_detected")
        restore_cleanup._docker_cleanup_command(directory, op,
            ["docker", "volume", "rm", operation["compose"]["volume"]], "recovery-remove-volume")
        if db.restore_container(op, allow_unregistered=True) is not None or db.verify_volume(op, allow_unregistered=True) is not None:
            raise RuntimeError("restore_cleanup_recovery_removal_unproven")
        registry, epoch, main_admission, _evidence = restore._load_main(directory)
        restore._verify_host(directory, registry, main_admission, prospective=False)
    root = directory / "restore-cleanup-recovered" / token
    archive._mkdir_durable(root)
    sources = archive._source_files(directory, token)
    sources["diagnosis.json"] = diagnosis_path
    sources["cleanup-recovery-admission.json"] = admission_path
    rows = []
    for relative, source in sorted(sources.items()):
        sha = archive.digest_file(source)
        archive._copy_immutable(source, root / "evidence" / relative)
        rows.append({"path": relative, "sha256": sha, "bytes": source.stat().st_size})
    manifest = {"schema": 1, "kind": "failed_create_cleaned", "token": token,
                "operation_sha256": admission["operation_sha256"], "files": rows, "created_at": time.time()}
    manifest_path = _write_immutable(root, "recovery.json", manifest)
    _write_immutable(root, "recovery-seal.json", {"schema": 1, "token": token,
                   "sha256": archive.digest_file(manifest_path)})
    # Archive verification precedes deleting active controls; a partial copy blocks re-admission.
    validate_history(directory)
    by_path = {row["path"]: row["sha256"] for row in rows}
    active_sources = archive._source_files(directory, token)
    for relative, source in active_sources.items():
        saved = root / "evidence" / relative
        if relative not in by_path or archive.digest_file(source) != by_path[relative] \
                or archive.digest_file(saved) != by_path[relative]:
            raise RuntimeError("restore_cleanup_recovery_source_changed")
    for source in active_sources.values():
        source.unlink()
    restore_root = directory / "restore" / token
    if restore_root.exists():
        import shutil
        shutil.rmtree(restore_root)
    archive._fsync_directory(directory)
    return {"status": "failed_create_cleaned", "token": token,
            "recovery": str(manifest_path), "sha256": archive.digest_file(manifest_path)}


def validate_history(directory: Path) -> None:
    parent = directory / "restore-cleanup-recovered"
    if not parent.exists():
        return
    if parent.is_symlink() or not parent.is_dir():
        raise RuntimeError("restore_cleanup_recovery_history_invalid")
    for root in parent.iterdir():
        if root.is_symlink() or not root.is_dir() or not re.fullmatch(r"[a-f0-9]{32}", root.name):
            raise RuntimeError("restore_cleanup_recovery_history_invalid")
        manifest_path, seal_path = root / "recovery.json", root / "recovery-seal.json"
        if not manifest_path.is_file() or not seal_path.is_file():
            raise RuntimeError("restore_cleanup_recovery_history_incomplete")
        manifest, seal = json.loads(manifest_path.read_text()), json.loads(seal_path.read_text())
        if (manifest.get("kind") != "failed_create_cleaned" or manifest.get("token") != root.name
                or seal.get("token") != root.name or seal.get("sha256") != archive.digest_file(manifest_path)):
            raise RuntimeError("restore_cleanup_recovery_history_seal_invalid")
        for row in manifest.get("files", []):
            path = Path(row["path"])
            archived = root / "evidence" / path
            if path.is_absolute() or ".." in path.parts or archived.is_symlink() or not archived.is_file() \
                    or archived.stat().st_size != row["bytes"] or archive.digest_file(archived) != row["sha256"]:
                raise RuntimeError("restore_cleanup_recovery_history_hash_invalid")


def prepare_next_attempt(directory: Path) -> None:
    validate_history(directory)
