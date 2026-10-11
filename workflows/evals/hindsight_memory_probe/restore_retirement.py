"""Explicit retirement of a diagnosed restore failure before creation."""

from __future__ import annotations

import fcntl
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

from . import restore_process
from .receipts import ReceiptStore
from .campaign_clock import WORK_CUTOFF
from . import restore_retirement_archive as archive


@contextmanager
def admission_lease(directory: Path):
    descriptor = os.open(
        directory / "restore-admission.lock",
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
    )
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("restore_admission_lease_busy") from exc
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _diagnosis(path: Path, operation: dict, directory: Path) -> dict:
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_mode & 0o222
        or path.stat().st_mode & 0o077
    ):
        raise RuntimeError("restore_diagnosis_not_private_immutable")
    failure_path = directory / f"restore-{operation['token']}-failure.result.json"
    if (
        failure_path.is_symlink()
        or not failure_path.is_file()
        or failure_path.stat().st_mode & 0o077
    ):
        raise RuntimeError("restore_retirement_failure_receipt_required")
    value = json.loads(path.read_text())
    expected_fields = {
        "schema",
        "kind",
        "failure_stage",
        "failure_code",
        "token",
        "operation_sha256",
        "archive_sha256",
        "snapshot_sha256",
        "selection_sha256",
        "failure_result_sha256",
        "no_create_intent",
        "no_create_result",
        "controller_gone",
        "registered_processes_gone",
        "restore_container_absent",
        "restore_volume_absent",
        "main_stopped",
        "baseline_unchanged",
    }
    required_true = (
        "no_create_intent",
        "no_create_result",
        "controller_gone",
        "registered_processes_gone",
        "restore_container_absent",
        "restore_volume_absent",
        "main_stopped",
        "baseline_unchanged",
    )
    if (
        not isinstance(value, dict)
        or set(value) != expected_fields
        or value.get("schema") != 1
        or value.get("kind") != "failed_before_creation"
        or value.get("failure_stage") != "controller-start"
        or value.get("failure_code") != "pre_creation_controller_admission_failure"
        or value.get("token") != operation["token"]
        or any(value.get(key) is not True for key in required_true)
        or value.get("operation_sha256")
        != archive.digest_file(directory / "restore-operation.json")
        or value.get("failure_result_sha256") != archive.digest_file(failure_path)
        or value.get("archive_sha256") != operation["archive"]["sha256"]
        or value.get("snapshot_sha256") != operation["snapshot"]["sha256"]
        or value.get("selection_sha256") != operation["selection"]["sha256"]
    ):
        raise RuntimeError("restore_diagnosis_contract_invalid")
    return value


def _verify_operation_sources(
    directory: Path,
    operation: dict,
    registry: dict,
    epoch: dict,
    admission: dict,
    evidence: dict,
) -> None:
    expected = {
        "registry_sha256": registry["registry_sha256"],
        "epoch_sha256": epoch["sha256"],
        "parent_finalization_token": admission["token"],
        "parent_stopped_epoch_sha256": epoch["sha256"],
        "release_path": epoch["release"],
        "finalization": {
            "containers": admission["containers"],
            "restart_selection": admission["restart_selection"],
            "restart_readback": admission["restart_readback"],
        },
    }
    if any(operation.get(key) != value for key, value in expected.items()):
        raise RuntimeError("restore_operation_source_identity_mismatch")
    if (
        Path(operation["snapshot"].get("root", "")) != evidence["archive"].parent
        or operation["archive"].get("bytes") != evidence["dump"]["bytes"]
        or operation["archive"].get("dump_result_sha256")
        != archive.digest_file(directory / evidence["finalized"]["dump_result"])
    ):
        raise RuntimeError("restore_operation_source_identity_mismatch")
    sources = {
        "archive": (
            Path(operation["archive"]["path"]),
            evidence["archive"],
            operation["archive"]["sha256"],
            evidence["dump"]["bytes"],
        ),
        "snapshot": (
            Path(operation["snapshot"]["path"]),
            evidence["snapshot_path"],
            operation["snapshot"]["sha256"],
            None,
        ),
        "selection": (
            Path(operation["selection"]["path"]),
            evidence["selection_path"],
            operation["selection"]["sha256"],
            None,
        ),
    }
    for name, (path, expected_path, expected_hash, expected_bytes) in sources.items():
        if (
            path != expected_path
            or path.is_symlink()
            or not path.is_file()
            or archive.digest_file(path) != expected_hash
            or archive.digest_file(path) != archive.digest_file(expected_path)
            or (expected_bytes is not None and path.stat().st_size != expected_bytes)
        ):
            raise RuntimeError(f"restore_operation_{name}_source_mismatch")
    if (
        operation["selection"].get("restart_proof_sha256")
        != admission["restart_readback"]["sha256"]
    ):
        raise RuntimeError("restore_operation_selection_source_mismatch")


def _retirement_readback_admission(directory: Path, operation: dict) -> dict:
    if time.time() >= WORK_CUTOFF:
        raise RuntimeError("restore_retirement_readback_deadline_elapsed")
    operation_hash = archive.digest_file(directory / "restore-operation.json")
    value = {
        "schema": 1,
        "kind": "read_only_restore_retirement",
        "token": operation["token"],
        "operation_sha256": operation_hash,
        "deadline": WORK_CUTOFF,
        "commands": [
            "docker ps",
            "docker inspect",
            "docker volume ls",
            "docker volume inspect",
        ],
    }
    path = directory / f"restore-{operation['token']}-retirement-admission.json"
    if path.exists():
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_mode & 0o222
            or path.stat().st_mode & 0o077
            or json.loads(path.read_text()) != value
        ):
            raise RuntimeError("restore_retirement_readback_admission_conflict")
    else:
        ReceiptStore(directory).write(path.name, value)
        path.chmod(0o400)
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return value


def retire_failed_before_create(directory: Path, diagnosis_path: Path) -> dict:
    from . import host_guard as host, restore, restore_cleanup, restore_database as db

    with admission_lease(directory):
        if archive.prepare_next_attempt(directory):
            return {"status": "retired_failed_before_creation", "recovered": True}
        operation = restore.read_operation(directory)
        diagnosis = _diagnosis(diagnosis_path, operation, directory)
        token = operation["token"]
        if any(
            (directory / f"restore-{token}-{suffix}.intent.json").exists()
            for suffix in ("create", "restore", "stop")
        ):
            raise RuntimeError("restore_retirement_after_creation_rejected")
        if any(
            (directory / f"restore-{token}-{suffix}.result.json").exists()
            for suffix in ("create", "restore", "snapshot", "compare", "cleanup")
        ):
            raise RuntimeError("restore_retirement_terminal_or_after_creation_rejected")
        if (directory / f"restore-{token}-result.json").exists():
            raise RuntimeError("restore_retirement_successful_operation_rejected")
        failure_path = directory / f"restore-{token}-failure.result.json"
        if (
            failure_path.is_symlink()
            or not failure_path.is_file()
            or failure_path.stat().st_mode & 0o077
        ):
            raise RuntimeError("restore_retirement_failure_receipt_required")
        failure = json.loads(failure_path.read_text())
        if (
            failure.get("token") != token
            or failure.get("status") != "failed"
            or failure.get("stage") != "controller-start"
        ):
            raise RuntimeError("restore_retirement_failure_stage_rejected")
        if not list(directory.glob(f"restore-{token}-controller-*.json")):
            raise RuntimeError("restore_retirement_controller_evidence_missing")
        if any(
            host.identity_matches(json.loads(path.read_text()).get("identity", {}))
            for path in directory.glob(f"restore-{token}-controller-*.json")
        ):
            raise RuntimeError("restore_controller_still_running")
        jobs = restore_process.registered_jobs(directory, token)
        if any(
            job.get("operation") not in restore_process.READ_ONLY_HOST_OPERATIONS
            for job in jobs
        ):
            raise RuntimeError("restore_retirement_restore_command_was_registered")
        if any(host.tagged_processes(job["token"]) for job in jobs):
            raise RuntimeError("restore_consumer_process_still_running")
        registry, epoch, admission, evidence = restore._load_main(directory)
        _verify_operation_sources(
            directory, operation, registry, epoch, admission, evidence
        )
        readback_admission = _retirement_readback_admission(directory, operation)
        with restore_cleanup.retirement_readback(
            directory, operation, readback_admission
        ):
            restore._verify_host(
                directory,
                json.loads((directory / "registry.json").read_text()),
                {"containers": operation["finalization"]["containers"]},
                prospective=False,
            )
            db.verify_compose(operation)
            if (
                db.restore_container(operation) is not None
                or db.verify_volume(operation) is not None
            ):
                raise RuntimeError("restore_retirement_after_creation_rejected")
        existing_root = directory / "restore-retired" / token
        if (existing_root / "retirement.json").is_file():
            manifest = archive.verify_archive(existing_root, token)
            if manifest.get("operation_sha256") != archive.digest_file(
                directory / "restore-operation.json"
            ) or manifest.get("diagnosis_sha256") != archive.digest_file(
                diagnosis_path
            ):
                raise RuntimeError("restore_retirement_archive_conflict")
            root = existing_root
        else:
            root = archive.archive_attempt(
                directory, diagnosis_path, operation, diagnosis
            )
        archive.verify_archive(root, token)
        archive.publish_active_marker(directory, token, root)
        archive.remove_sources(directory, token, root)
        return {
            "status": "retired_failed_before_creation",
            "token": token,
            "retirement": str(root / "retirement.json"),
            "sha256": archive.digest_file(root / "retirement.json"),
        }
