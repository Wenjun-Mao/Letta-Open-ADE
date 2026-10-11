"""Exact preserve-or-remove cleanup for the isolated restore epoch."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

from . import host_guard as host
from . import restore_database as db
from .receipts import ReceiptStore
from .campaign_clock import WORK_CUTOFF

def cleanup(directory: Path, *, controller_token: str | None = None) -> dict:
    from . import restore

    operation = restore.read_operation(directory)
    token = operation["token"]
    result_path = directory / f"restore-{token}-cleanup.result.json"
    if result_path.exists():
        result = json.loads(result_path.read_text())
        return result
    if (not (directory / f"restore-{token}-result.json").is_file()
            and not (directory / f"restore-{token}-failure.result.json").is_file()):
        raise RuntimeError("restore_terminal_result_required_before_cleanup")
    archive = Path(operation["archive"]["path"])
    snapshot = Path(operation["snapshot"]["path"])
    if (not archive.is_file() or not snapshot.is_file()
            or restore.candidate_database.sha256_file(archive) != operation["archive"]["sha256"]
            or restore.candidate_database.sha256_file(snapshot) != operation["snapshot"]["sha256"]):
        raise RuntimeError("restore_failure_evidence_unavailable_before_cleanup")
    restore_intent = directory / f"restore-{token}-restore.intent.json"
    create_intent = directory / f"restore-{token}-create.intent.json"
    restored_snapshot = Path(operation["restore_root"]) / "canonical-snapshot.json"
    post_state_saved = False
    if restored_snapshot.is_file():
        try:
            from . import restore_compare

            restored_value = json.loads(restored_snapshot.read_text())
            rows = restore_compare._table_rows(restored_value, Path(operation["restore_root"]))
            selection = json.loads(Path(operation["selection"]["path"]).read_text())
            restore_compare._selected_state(rows, selection)
            post_state_saved = True
        except Exception:
            post_state_saved = False
    comparison_path = directory / f"restore-{token}-compare.result.json"
    comparison_mismatch = False
    if comparison_path.is_file():
        comparison_mismatch = json.loads(comparison_path.read_text()).get("status") != "completed"
    stopped_by_operator = (directory / f"restore-{token}-stop.intent.json").is_file()
    restore_started = restore_intent.is_file()
    container_creation_started = create_intent.is_file()
    if ((restore_started and (not post_state_saved or comparison_mismatch))
            or (container_creation_started and stopped_by_operator)):
        with registered_host_readback(directory, operation):
            create_result = directory / f"restore-{token}-create.result.json"
            unregistered = container_creation_started and not create_result.is_file()
            container = db.restore_container(operation, allow_unregistered=unregistered)
            if container is not None and container["State"]["Status"] == "running":
                _docker_cleanup_command(directory, operation,
                    ["docker", "stop", "--time", "20", container["Id"]], "preserve-stop")
            container = db.restore_container(operation, allow_unregistered=unregistered)
            if container is not None and container["State"]["Status"] == "running":
                raise RuntimeError("restore_failed_state_stop_unproven")
        preserved = {"status": "preserved_failed_state", "token": token,
                     "container_id": None if container is None else container["Id"],
                     "volume": operation["compose"]["volume"], "removed": False,
                     "reason": ("emergency_restore_preemption" if stopped_by_operator
                                else "restore_comparison_mismatch" if comparison_mismatch
                                else "post_restore_snapshot_not_preserved"), "time": time.time()}
        ReceiptStore(directory).write(result_path.name, preserved)
        return preserved
    live_controllers = []
    for path in directory.glob(f"restore-{token}-controller*.json"):
        value = json.loads(path.read_text())
        if value.get("identity") and host.identity_matches(value["identity"]):
            live_controllers.append(value)
    if any(row.get("controller_token") != controller_token for row in live_controllers):
        raise RuntimeError("restore_controller_still_running")
    from . import restore_process

    if any(host.tagged_processes(job["token"])
           for job in restore_process.registered_jobs(directory, token)):
        raise RuntimeError("restore_consumer_process_still_running")
    with registered_host_readback(directory, operation):
        restore._verify_host(directory, json.loads((directory / "registry.json").read_text()),
                     {"containers": operation["finalization"]["containers"]}, prospective=False)
        db.verify_compose(operation)
        container = db.restore_container(operation)
        had_container = container is not None
        had_volume = db.verify_volume(operation) is not None
        if container is not None:
            if container["State"]["Status"] == "running":
                _docker_cleanup_command(directory, operation, ["docker", "stop", "--time", "20", container["Id"]], "stop")
            container = db.restore_container(operation)
            if container is None or container["State"]["Status"] == "running":
                raise RuntimeError("restore_stopped_container_readback_failed")
            _docker_cleanup_command(directory, operation, ["docker", "rm", container["Id"]], "remove-container")
        volume = db.verify_volume(operation)
        if volume is not None:
            consumers = db.docker_text(["docker", "ps", "-aq", "--no-trunc", "--filter", "volume=" + operation["compose"]["volume"]])
            if consumers:
                raise RuntimeError("restore_volume_consumer_detected")
            _docker_cleanup_command(directory, operation,
                                    ["docker", "volume", "rm", operation["compose"]["volume"]], "remove-volume")
        if db.restore_container(operation) is not None or db.verify_volume(operation) is not None:
            raise RuntimeError("restore_cleanup_identity_remains")
    result = {"status": "completed", "token": token, "container_removed": had_container,
              "volume_removed": had_volume, "completed_at": time.time(),
              "archive_sha256": operation["archive"]["sha256"],
              "canonical_snapshot_sha256": operation["snapshot"]["sha256"]}
    ReceiptStore(directory).write(result_path.name, result)
    return result


@contextlib.contextmanager
def retirement_readback(directory: Path, operation: dict, admission: dict):
    """Allow only bounded read-only identity checks after restore-work expiry."""
    from . import candidate_database

    operation_hash = candidate_database.sha256_file(directory / "restore-operation.json")
    if (admission.get("schema") != 1 or admission.get("kind") != "read_only_restore_retirement"
            or admission.get("commands") != ["docker ps", "docker inspect", "docker volume ls", "docker volume inspect"]
            or admission.get("token") != operation.get("token")
            or admission.get("operation_sha256") != operation_hash
            or admission.get("deadline") != WORK_CUTOFF or time.time() >= WORK_CUTOFF):
        raise RuntimeError("restore_retirement_readback_admission_invalid")
    readback_operation = {**operation, "cleanup_deadline": admission["deadline"]}
    with registered_host_readback(directory, readback_operation):
        yield


def _docker_cleanup_command(directory: Path, operation: dict, command: list[str], suffix: str) -> None:
    from .restore_process import run_command

    run_command(directory, operation, command, timeout=45, operation_label="cleanup-" + suffix,
                monitor=lambda: None, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@contextlib.contextmanager
def registered_host_readback(directory: Path, operation: dict):
    from . import host_guard
    from .restore_process import run_command

    previous_reader, previous_text, previous_containers = db.COMMAND_RUNNER, db.TEXT_RUNNER, host_guard.CONTAINER_READER

    def command_json(arguments: list[str], timeout: int):
        target = Path(operation["restore_root"]) / f"readback-{uuid.uuid4().hex}.partial"
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as output:
                code = run_command(directory, operation, arguments, timeout,
                    operation_label="restore-operator-readback", monitor=lambda: None,
                    stdout=output, stderr=subprocess.DEVNULL)
                output.flush()
                os.fsync(output.fileno())
            if code != 0:
                raise RuntimeError("restore_docker_readback_failed")
            return json.loads(target.read_bytes())
        finally:
            target.unlink(missing_ok=True)

    def read_containers():
        identifiers = command_text(["docker", "ps", "-aq", "--no-trunc"], 10)
        return command_json(["docker", "inspect", *identifiers], 10) if identifiers else []

    def command_text(arguments: list[str], timeout: int):
        target = Path(operation["restore_root"]) / f"readback-{uuid.uuid4().hex}.partial"
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as output:
                code = run_command(directory, operation, arguments, timeout,
                    operation_label="restore-operator-list-readback", monitor=lambda: None,
                    stdout=output, stderr=subprocess.DEVNULL)
                output.flush()
                os.fsync(output.fileno())
            if code != 0:
                raise RuntimeError("restore_docker_readback_failed")
            return target.read_text(encoding="utf-8").splitlines()
        finally:
            target.unlink(missing_ok=True)

    db.COMMAND_RUNNER = command_json
    db.TEXT_RUNNER = command_text
    host_guard.CONTAINER_READER = read_containers
    try:
        yield
    finally:
        db.COMMAND_RUNNER = previous_reader
        db.TEXT_RUNNER = previous_text
        host_guard.CONTAINER_READER = previous_containers
