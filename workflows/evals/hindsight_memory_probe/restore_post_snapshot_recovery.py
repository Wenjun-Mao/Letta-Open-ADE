"""Bounded preservation and retirement of a failed post-restore snapshot."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from . import restore, restore_cleanup, restore_database as db
from . import restore_compare, restore_process, restore_retirement_archive as archive, restore_snapshot
from .restore_post_snapshot_archive import (
    _archive, _remove_active_sources, verify_archive,
)
from .restore_post_snapshot_contract import (
    SCOPES, _authority, _container_identity, _json_digest, _sha,
    _write_once,
)
from .restore_post_snapshot_admission import _validate_original
from .receipts import ReceiptStore
from .restore_post_snapshot_expiry import (
    _cancel_expiry_timer, _require_expiry_guard, _start_expiry_timer,
)
from .restore_post_snapshot_resume import resume_archived_retirement

def _stable_identity(identity: dict) -> dict:
    return {key: value for key, value in identity.items() if key != "started_at"}

def _run(directory: Path, operation: dict, deadline: float, label: str,
         command: list[str], timeout: int, *, stdout=None) -> int:
    scoped = {**operation, "cleanup_deadline": deadline,
              "_cleanup_recovery_container_id": operation["_cleanup_recovery_container_id"],
              "_post_restore_recovery": True}
    expiry_job = operation.get("_post_restore_expiry_job")
    def monitor():
        if expiry_job is not None:
            _require_expiry_guard(expiry_job, deadline)
        if label != "start":
            _monitor(directory, scoped)
    return restore_process.run_command(directory, scoped, command, timeout,
        operation_label="post-restore-recovery-" + label,
        monitor=monitor,
        stdout=stdout if stdout is not None else subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)


def _monitor(directory: Path, operation: dict) -> None:
    registry = json.loads((directory / "registry.json").read_text())
    monitor_root = directory / "restore-post-restore-recovery" / operation["token"] / "monitor-readback"
    monitor_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    monitor_operation = {**operation, "restore_root": str(monitor_root)}
    with restore_cleanup.registered_host_readback(directory, monitor_operation):
        restore._verify_host(directory, registry,
            {"containers": operation["finalization"]["containers"]}, prospective=False,
            post_restore_recovery_started_at=operation.get("_post_restore_recovery_started_at"))

def _ensure_exact_container_stopped(directory: Path, operation: dict, authority: dict,
                                    readback_operation: dict) -> bool:
    container_id = authority["container_id"]
    with restore_cleanup.registered_host_readback(directory, readback_operation):
        rows = db.docker_json(["docker", "inspect", container_id])
        if not rows:
            return True
        if len(rows) != 1 or rows[0].get("Id") != container_id:
            raise RuntimeError("restore_post_snapshot_recovery_stop_identity_invalid")
        row = rows[0]
        if row.get("State", {}).get("Status") == "running":
            scoped = {**operation, "_post_restore_recovery": True,
                      "_post_restore_recovery_started_at": row["State"]["StartedAt"]}
            _run(directory, scoped, authority["deadline"], "stop",
                 ["docker", "stop", "--time", "20", container_id], 45)
            rows = db.docker_json(["docker", "inspect", container_id])
            if (len(rows) != 1 or rows[0].get("Id") != container_id
                    or rows[0].get("State", {}).get("Status") == "running"):
                return False
        return True

def _capture_and_stop(directory: Path, operation: dict, authority_path: Path,
                      authority: dict, source_sha: str, source_path: str,
                      session_root: Path, run_operation: dict, readback_operation: dict,
                      container: dict, fresh_identity: dict, original_snapshot: Path) -> dict:
    token = operation["token"]
    expiry_child, expiry_job = _start_expiry_timer(
        directory, operation, authority_path, authority, source_path)
    guarded_run_operation = {**run_operation, "_post_restore_expiry_job": expiry_job}
    started_operation = None
    try:
        _write_once(session_root, "start.intent.json", {
            "schema": 1, "token": token, "container_id": container["Id"],
            "operation": "docker start exact failed restore DB",
            "authority_sha256": _sha(authority_path)})
        with restore_cleanup.registered_host_readback(directory, readback_operation):
            _require_expiry_guard(expiry_job, authority["deadline"])
            _run(directory, guarded_run_operation, authority["deadline"], "start",
                 ["docker", "start", container["Id"]], 30)
            started_row = db.docker_json(["docker", "inspect", container["Id"]])[0]
            started_at = started_row["State"]["StartedAt"]
            started_operation = {**readback_operation, "_post_restore_recovery": True,
                                 "_post_restore_expiry_job": expiry_job,
                                 "_post_restore_recovery_started_at": started_at}
            started = db.restore_container(started_operation)
            if (started is None or started["Id"] != container["Id"]
                    or started["State"].get("Status") != "running"
                    or _stable_identity(_container_identity(started)) != _stable_identity(fresh_identity)):
                raise RuntimeError("restore_post_snapshot_recovery_restart_identity_invalid")
            start_proof = {"schema": 1, "token": token, "container_id": started["Id"],
                           "original_started_at": fresh_identity["started_at"],
                           "recovery_started_at": started["State"]["StartedAt"],
                           "identity_sha256": _json_digest(_container_identity(started))}
            _write_once(session_root, "start.result.json", start_proof)

            first = _capture(directory, started_operation, authority["deadline"], started,
                             session_root / "capture")
            repeated = _capture(directory, started_operation, authority["deadline"], started,
                                session_root / "capture-check")
            hashes = lambda snapshot: {name: row["sha256"] for name, row in snapshot["tables"].items()}
            if hashes(first) != hashes(repeated):
                raise RuntimeError("restore_post_snapshot_recovery_state_not_stable")
            restored_rows = restore_compare._table_rows(first, session_root / "capture")
            selection = json.loads(Path(operation["selection"]["path"]).read_text())
            selected_scope = restore_compare._selected_state(restored_rows, selection)
            original = json.loads(original_snapshot.read_text())
            comparison = restore_compare.compare(original, Path(operation["snapshot"]["root"]),
                first, session_root / "capture", selection)
            scope_path = session_root / "scope-readback.json"
            _write_once(session_root, scope_path.name, {"schema": 1, "token": token,
                "capture_sha256": _json_digest(first), "selected_state": selected_scope,
                "comparison": comparison, "status": "captured_failed_attempt"})
            _write_once(session_root, "capture.result.json", {
                "schema": 1, "token": token, "snapshot_path": "capture/canonical-snapshot.json",
                "snapshot_sha256": _sha(session_root / "capture" / "canonical-snapshot.json"),
                "tables": first["tables"], "database": first["database"],
                "container_id": first["container_id"], "image_id": first["image_id"],
                "scope_sidecar": scope_path.name, "scope_sidecar_sha256": _sha(scope_path),
                "repeat_capture_sha256": _json_digest(repeated),
                "status": "failed_attempt_preserved_not_success"})

            _write_once(session_root, "stop.intent.json", {
                "schema": 1, "token": token, "container_id": started["Id"],
                "started_at": started["State"]["StartedAt"],
                "operation": "docker stop exact failed restore DB",
                "authority_sha256": _sha(authority_path)})
            _run(directory, started_operation, authority["deadline"], "stop",
                 ["docker", "stop", "--time", "20", started["Id"]], 45)
            stopped_row = db.docker_json(["docker", "inspect", started["Id"]])[0]
            stopped = db.restore_container({**started_operation,
                "_cleanup_recovery_container_id": started["Id"],
                "_post_restore_recovery_started_at": stopped_row["State"]["StartedAt"]})
            if (stopped is None or stopped["Id"] != started["Id"]
                    or stopped["State"].get("Status") != "exited"
                    or stopped["State"].get("StartedAt") != started["State"].get("StartedAt")
                    or stopped["State"].get("OOMKilled") is not False
                    or stopped.get("RestartCount") != 0):
                raise RuntimeError("restore_post_snapshot_recovery_stop_unproven")
            _write_once(session_root, "stop.result.json", {
                "schema": 1, "token": token, "container_id": stopped["Id"],
                "started_at": stopped["State"]["StartedAt"], "status": "stopped",
                "container_identity_sha256": _json_digest(_container_identity(stopped))})
        _cancel_expiry_timer(directory, operation, expiry_child, expiry_job)
        return first
    except Exception:
        try:
            if _ensure_exact_container_stopped(directory, run_operation, authority, readback_operation):
                _cancel_expiry_timer(directory, operation, expiry_child, expiry_job)
        except Exception:
            # The separately registered host-local expiry remains responsible
            # for stopping this exact container at the authority deadline.
            pass
        raise

def _capture(directory: Path, operation: dict, deadline: float, container: dict,
             capture_root: Path) -> dict:
    recovery_operation = {**operation, "restore_root": str(capture_root),
                          "cleanup_deadline": deadline}
    def command(arguments, timeout, *, operation_label, stdout, **kwargs):
        return _run(directory, {**recovery_operation,
            "_cleanup_recovery_container_id": container["Id"]}, deadline,
            "snapshot-query", arguments, timeout, stdout=stdout)
    return restore_snapshot.snapshot(directory, recovery_operation, container,
                                    ReceiptStore(capture_root), command)

def recover(directory: Path, authority_path: Path) -> dict:
    from .restore_retirement import admission_lease
    from . import restore_cleanup_recovery_contract

    with admission_lease(directory):
        token_match = re.search(r"restore-([a-f0-9]{32})-post-restore-authority-", authority_path.name)
        if token_match:
            completed_root = directory / "restore-post-restore-retired" / token_match.group(1)
            closure_path = completed_root / "closure" / "closure.json"
            if (completed_root / "retirement.json").is_file() and closure_path.is_file():
                manifest = verify_archive(completed_root, token_match.group(1))
                _remove_active_sources(directory, token_match.group(1), completed_root,
                                       authority_path, completed_root / "closure")
                return {"status": "failed_post_restore_retired", "token": token_match.group(1),
                        "archive": str(completed_root / "retirement.json"),
                        "sha256": archive.digest_file(completed_root / "retirement.json"),
                        "recovered_state": manifest["capture_sha256"]}
        operation = restore.read_operation(directory)
        token = operation["token"]
        proof, _archive_path, original_snapshot = _validate_original(directory, operation)
        failure_path = directory / f"restore-{token}-failure.result.json"
        cleanup_path = directory / f"restore-{token}-cleanup.result.json"
        authority, recovery_source_sha, recovery_source_path = _authority(
            authority_path, directory, operation, failure_path, cleanup_path)
        capture_root = directory / "restore-post-restore-recovery" / token / authority["admission_token"]
        archive_root = directory / "restore-post-restore-retired" / token
        if archive_root.exists() and (archive_root / "retirement.json").exists():
            return resume_archived_retirement(
                directory, operation, authority_path, authority,
                recovery_source_sha, proof, archive_root, _run)

        recovery_root = directory / "restore-post-restore-recovery"
        recovery_token_root = recovery_root / token
        for path in (recovery_root, recovery_token_root):
            path.mkdir(mode=0o700, exist_ok=True)
            if path.is_symlink() or not path.is_dir() or path.stat().st_mode & 0o077:
                raise RuntimeError("restore_post_snapshot_recovery_session_root_invalid")
        capture_root.mkdir(mode=0o700, exist_ok=False)
        (capture_root / "capture").mkdir(mode=0o700)
        (capture_root / "capture-check").mkdir(mode=0o700)
        session_root = capture_root
        run_operation = {**operation, "cleanup_deadline": authority["deadline"],
                         "_cleanup_recovery_container_id": proof["create"]["container_id"],
                         "_post_restore_recovery": True,
                         "_post_restore_recovery_admission_token": authority["admission_token"],
                         "_post_restore_recovery_authority_sha256": _sha(authority_path)}
        admission = {"schema": 1, "kind": "failed_post_restore_snapshot_recovery",
            "token": token, "admission_token": authority["admission_token"],
            "operation_sha256": authority["operation_sha256"], "authority_sha256": _sha(authority_path),
            "failure_sha256": authority["failure_sha256"], "cleanup_sha256": authority["cleanup_sha256"],
            "container_id": proof["create"]["container_id"], "volume": operation["compose"]["volume"],
            "old_operation_source_sha": Path(operation["release_path"]).name,
            "recovery_execution_source_sha": recovery_source_sha,
            "recovery_execution_source_path": recovery_source_path,
            "deadline": authority["deadline"], "scopes": SCOPES, "created_at": authority["issued_at"]}
        _write_once(session_root, "admission.json", admission)

        readback_operation = {**run_operation, "restore_root": str(session_root / "readback")}
        (session_root / "readback").mkdir(mode=0o700)
        with restore_cleanup.registered_host_readback(directory, readback_operation):
            registry = json.loads((directory / "registry.json").read_text())
            restore._verify_host(directory, registry,
                {"containers": operation["finalization"]["containers"]}, prospective=False)
            db.verify_compose(operation)
            container = db.restore_container(readback_operation)
            volume = db.verify_volume(readback_operation)
            if (container is None or volume is None or container["Id"] != authority["container_id"]
                    or volume.get("Name") != authority["volume"]
                    or container["State"].get("Status") != "exited"
                    or container["State"].get("OOMKilled") is not False
                    or container.get("RestartCount") != 0):
                raise RuntimeError("restore_post_snapshot_recovery_resource_identity_invalid")
            fresh_identity = _container_identity(container)
            volume_identity = restore_cleanup_recovery_contract._volume_identity(volume)
        _write_once(session_root, "original-resource-identity.json", {
            "container": fresh_identity, "container_sha256": _json_digest(fresh_identity),
            "volume": volume_identity, "volume_sha256": _json_digest(volume_identity)})

        capture = _capture_and_stop(directory, operation, authority_path, authority,
            recovery_source_sha, recovery_source_path, session_root, run_operation,
            readback_operation, container, fresh_identity, original_snapshot)

        stop_proof_path = session_root / "stop.result.json"
        if (stop_proof_path.is_symlink() or not stop_proof_path.is_file()
                or stop_proof_path.stat().st_mode & 0o377):
            raise RuntimeError("restore_post_snapshot_recovery_stop_receipt_missing")
        stop_proof = json.loads(stop_proof_path.read_text())
        start_proof_path = session_root / "start.result.json"
        if (start_proof_path.is_symlink() or not start_proof_path.is_file()
                or start_proof_path.stat().st_mode & 0o377):
            raise RuntimeError("restore_post_snapshot_recovery_start_receipt_invalid")
        start_proof = json.loads(start_proof_path.read_text())
        stopped_at = stop_proof.get("started_at")
        if (stop_proof.get("container_id") != authority["container_id"]
                or stop_proof.get("status") != "stopped"
                or not isinstance(stopped_at, str) or not stopped_at
                or stop_proof.get("container_identity_sha256") != start_proof.get("identity_sha256")
                or stopped_at != start_proof.get("recovery_started_at")):
            raise RuntimeError("restore_post_snapshot_recovery_stop_receipt_invalid")
        post_capture_operation = {**run_operation,
                                  "_post_restore_recovery_started_at": stopped_at}
        post_capture_readback = {**readback_operation,
                                 "_post_restore_recovery_started_at": stopped_at}
        with restore_cleanup.registered_host_readback(directory, post_capture_readback):
            stopped_container = db.restore_container(post_capture_readback)
        if (stopped_container is None or stopped_container.get("Id") != authority["container_id"]
                or stopped_container.get("State", {}).get("Status") != "exited"
                or stopped_container.get("State", {}).get("StartedAt") != stopped_at
                or _json_digest(_container_identity(stopped_container))
                   != stop_proof.get("container_identity_sha256")):
            raise RuntimeError("restore_post_snapshot_recovery_stop_readback_invalid")
        remove_container = ["docker", "rm", authority["container_id"]]
        remove_volume = ["docker", "volume", "rm", operation["compose"]["volume"]]
        _write_once(session_root, "remove-container.intent.json", {
            "schema": 1, "token": token, "command": remove_container,
            "authority_sha256": _sha(authority_path)})
        _write_once(session_root, "remove-volume.intent.json", {
            "schema": 1, "token": token, "command": remove_volume,
            "authority_sha256": _sha(authority_path)})
        root = _archive(directory, token, authority_path, session_root, operation,
                        recovery_source_sha, capture)
        _run(directory, post_capture_operation, authority["deadline"], "remove-container", remove_container, 45)
        with restore_cleanup.registered_host_readback(directory, post_capture_readback):
            remaining_container = db.restore_container(post_capture_readback)
        if remaining_container is not None:
            raise RuntimeError("restore_post_snapshot_recovery_container_removal_unproven")
        with restore_cleanup.registered_host_readback(directory, post_capture_readback):
            consumers = db.docker_text(["docker", "ps", "-aq", "--no-trunc", "--filter",
                                        "volume=" + operation["compose"]["volume"]])
        if consumers:
            raise RuntimeError("restore_post_snapshot_recovery_volume_consumer_detected")
        _run(directory, post_capture_operation, authority["deadline"], "remove-volume", remove_volume, 45)
        with restore_cleanup.registered_host_readback(directory, post_capture_readback):
            remaining_volume = db.verify_volume(post_capture_readback)
        if remaining_volume is not None:
            raise RuntimeError("restore_post_snapshot_recovery_volume_removal_unproven")
        with restore_cleanup.registered_host_readback(directory, post_capture_readback):
            restore._verify_host(directory, registry,
                {"containers": operation["finalization"]["containers"]}, prospective=False)
        _remove_active_sources(directory, token, root, authority_path, session_root)
        return {"status": "failed_post_restore_retired", "token": token,
                "archive": str(root / "retirement.json"), "sha256": archive.digest_file(root / "retirement.json"),
                "recovered_state": _json_digest(capture)}

def prepare_next_attempt(directory: Path) -> None:
    root = directory / "restore-post-restore-retired"
    if not root.exists():
        return
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("restore_post_snapshot_recovery_history_invalid")
    for archive_root in root.iterdir():
        if archive_root.is_symlink() or not archive_root.is_dir():
            raise RuntimeError("restore_post_snapshot_recovery_history_invalid")
        token = archive_root.name
        manifest = verify_archive(archive_root, token)
        closure_path = archive_root / "closure" / "closure.json"
        seal_path = archive_root / "closure" / "closure-seal.json"
        if seal_path.is_symlink():
            raise RuntimeError("restore_post_snapshot_recovery_history_invalid")
        if closure_path.is_symlink() or not closure_path.is_file():
            raise RuntimeError("restore_post_snapshot_recovery_history_incomplete")
        closure = json.loads(closure_path.read_text())
        seal = json.loads(seal_path.read_text()) if seal_path.is_file() else None
        if (closure.get("token") != token or closure.get("status") != "failed_post_restore_retired"
                or closure.get("archive_sha256") != archive.digest_file(archive_root / "retirement.json")
                or any(closure.get(field) is not True for field in
                       ("container_absent", "volume_absent", "main_baseline_unchanged"))
                or seal is not None and seal != {"schema": 1, "token": token, "sha256": _sha(closure_path)}
                or manifest.get("capture_sha256") is None):
            raise RuntimeError("restore_post_snapshot_recovery_history_invalid")
        removal_rows = closure.get("closure_receipts")
        if not isinstance(removal_rows, list):
            raise RuntimeError("restore_post_snapshot_recovery_history_invalid")
        closure_evidence = archive_root / "closure" / "evidence"
        listed = set()
        for row in removal_rows:
            if not isinstance(row, dict) or set(row) != {"path", "sha256", "bytes"}:
                raise RuntimeError("restore_post_snapshot_recovery_history_invalid")
            path = closure_evidence / row["path"]
            if (Path(row["path"]).name != row["path"] or path.is_symlink() or not path.is_file()
                    or path.stat().st_size != row["bytes"] or archive.digest_file(path) != row["sha256"]):
                raise RuntimeError("restore_post_snapshot_recovery_history_invalid")
            listed.add(row["path"])
        found = {path.name for path in closure_evidence.iterdir()} if closure_evidence.exists() else set()
        if found != listed:
            raise RuntimeError("restore_post_snapshot_recovery_history_invalid")
        _remove_active_sources(directory, token, archive_root, Path(), archive_root / "closure")
