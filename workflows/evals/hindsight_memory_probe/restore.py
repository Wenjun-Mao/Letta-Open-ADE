"""Guard-owned, single-use P4 disposable PostgreSQL restore controller."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from . import candidate_database, epochs, host_guard as host, lifecycle, releases
from .campaign_clock import DEADLINE, WORK_CUTOFF
from .receipts import ReceiptStore
from . import restore_database as db, restore_process
from . import restore_cleanup

MAX_RESTORE_SECONDS = 1800
CLEANUP_RESERVE_SECONDS = 360


def operation_path(directory: Path) -> Path:
    return directory / "restore-operation.json"


def read_operation(directory: Path) -> dict:
    path = operation_path(directory)
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("restore_operation_missing")
    value = json.loads(path.read_text())
    seal_path = directory / "restore-operation-seal.json"
    if (seal_path.is_symlink() or not seal_path.is_file()
            or json.loads(seal_path.read_text()).get("sha256") != candidate_database.sha256_file(path)):
        raise RuntimeError("restore_operation_seal_invalid")
    if (not isinstance(value, dict) or value.get("schema") != 1
            or not isinstance(value.get("token"), str)
            or value.get("compose", {}).get("project") != "ade-hindsight-restore-" + value.get("token", "")[:16]
            or value.get("deadline", 0) > WORK_CUTOFF
            or value.get("cleanup_deadline", 0) < value.get("deadline", 0)
            or value.get("cleanup_deadline", 0) > WORK_CUTOFF
            or value.get("hard_deadline") != DEADLINE):
        raise RuntimeError("restore_operation_invalid")
    return value


def _load_main(directory: Path) -> tuple[dict, dict, dict, dict]:
    from .supervisor import load_registry

    registry = load_registry(directory)
    epoch = epochs.active(directory, registry)
    admission_path = directory / f"epoch-{epoch['index']:04d}.finalize-admission.json"
    finalized_path = directory / f"epoch-{epoch['index']:04d}.finalized.json"
    stopped_path = epochs.stopped_path(directory, epoch)
    if any(not path.is_file() for path in (admission_path, finalized_path, stopped_path)):
        raise RuntimeError("restore_requires_completed_ordered_finalization")
    admission = json.loads(admission_path.read_text())
    finalized = json.loads(finalized_path.read_text())
    stopped = json.loads(stopped_path.read_text())
    if (admission.get("registry_sha256") != registry["registry_sha256"]
            or admission.get("epoch_sha256") != epoch["sha256"]
            or finalized.get("registry_sha256") != registry["registry_sha256"]
            or finalized.get("epoch_sha256") != epoch["sha256"]
            or finalized.get("token") != admission.get("token")
            or finalized.get("p4_complete") is not True
            or finalized.get("baseline_unchanged") is not True
            or finalized.get("all_candidate_services_stopped") is not True
            or stopped.get("epoch_sha256") != epoch["sha256"]):
        raise RuntimeError("restore_finalization_proof_invalid")
    if finalized.get("dump_result") != f"finalize-{admission['token']}-dump-result.json":
        raise RuntimeError("restore_dump_reference_invalid")
    dump_path = directory / finalized["dump_result"]
    if (not dump_path.is_file() or candidate_database.sha256_file(dump_path)
            != finalized.get("dump_result_sha256")):
        raise RuntimeError("restore_dump_result_hash_mismatch")
    dump = json.loads(dump_path.read_text())
    archive = directory / "finalization" / admission["token"] / dump.get("archive", "")
    if (not archive.is_file() or candidate_database.sha256_file(archive) != dump.get("sha256")
            or dump.get("toc_valid") is not True
            or dump.get("registry_sha256") != registry["registry_sha256"]
            or dump.get("epoch_sha256") != epoch["sha256"]):
        raise RuntimeError("restore_archive_identity_invalid")
    snapshot_path = directory / f"finalize-{admission['token']}-canonical-snapshot.json"
    if not snapshot_path.is_file():
        raise RuntimeError("restore_canonical_snapshot_missing")
    snapshot = json.loads(snapshot_path.read_text())
    selection_ref = admission.get("restart_selection", {})
    restart_ref = admission.get("restart_readback", {})
    if selection_ref.get("status") != "frozen" or restart_ref.get("status") != "completed":
        raise RuntimeError("restore_requires_frozen_restart_selection")
    from . import p4_evidence

    release_sha = Path(epoch["release"]).name
    selection_path = p4_evidence.resolve_reference(directory, selection_ref, release_sha, "selection")
    if candidate_database.sha256_file(selection_path) != selection_ref.get("sha256"):
        raise RuntimeError("restore_selection_reference_invalid")
    selection = json.loads(selection_path.read_text())
    from .restart_selection import validate_selection

    validate_selection(selection)
    proof = p4_evidence.resolve_reference(directory, restart_ref, release_sha, "completed")
    if candidate_database.sha256_file(proof) != restart_ref.get("sha256"):
        raise RuntimeError("restore_restart_proof_reference_invalid")
    for artifact in ("before", "after"):
        reference = restart_ref.get(artifact, {})
        readback_path = p4_evidence.resolve_reference(directory, reference, release_sha, artifact)
        if candidate_database.sha256_file(readback_path) != reference.get("sha256"):
            raise RuntimeError("restore_restart_proof_reference_invalid")
    if (snapshot.get("container_id") != next(row["id"] for row in admission["containers"] if row["service"] == "db")
            or snapshot.get("image_id") != dump.get("image_id")
            or snapshot.get("volume") != "ade-hindsight-probe_db-data"):
        raise RuntimeError("restore_snapshot_source_identity_mismatch")
    return registry, epoch, admission, {"finalized": finalized, "stopped": stopped,
        "dump": dump, "archive": archive, "snapshot": snapshot,
        "snapshot_path": snapshot_path, "selection": selection, "selection_path": selection_path}


def _verify_host(directory: Path, registry: dict, admission: dict, *, prospective: bool,
                 allow_restore_creation: bool = False,
                 post_restore_recovery_started_at: str | None = None) -> list[dict]:
    items = host.containers()
    main_candidates = host.candidate_containers(items, epochs.effective_registry(directory, registry))
    expected_baseline = {row["id"]: row for row in registry["baseline"]}
    actual = {row["Id"]: row for row in items}
    if any(host.baseline_projection(actual.get(identifier, {})) != projection
           for identifier, projection in expected_baseline.items()):
        raise RuntimeError("restore_baseline_identity_changed")
    baseline_ids = set(expected_baseline)
    main_ids = {row["Id"] for row in main_candidates}
    expected_rows = {row["id"]: row for row in admission["containers"]}
    if not main_ids.issubset(expected_rows):
        raise RuntimeError("restore_main_container_identity_changed")
    missing_main = set(expected_rows) - main_ids
    if any(expected_rows[identifier].get("service") != "runner" or not expected_rows[identifier].get("oneoff")
           for identifier in missing_main):
        raise RuntimeError("restore_main_container_identity_missing")
    restore_ids = set()
    operation_path = directory / "restore-operation.json"
    if operation_path.is_file():
        operation = json.loads(operation_path.read_text())
        if post_restore_recovery_started_at is not None:
            operation = {**operation, "_post_restore_recovery": True,
                         "_post_restore_recovery_started_at": post_restore_recovery_started_at}
        restore_container = db.restore_container(
            operation, allow_unregistered=allow_restore_creation, inventory=items
        )
        volume = db.verify_volume(operation, allow_unregistered=allow_restore_creation)
        if restore_container is not None and volume is None:
            raise RuntimeError("restore_container_volume_missing")
        if restore_container is not None:
            restore_ids.add(restore_container["Id"])
    if set(actual) != baseline_ids | main_ids | restore_ids:
        raise RuntimeError("restore_unowned_container_detected")
    for container in main_candidates:
        row = expected_rows[container["Id"]]
        labels = container.get("Config", {}).get("Labels") or {}
        identity = lifecycle.identity(container)
        if (container["Image"] != row["image_id"] or container["State"]["StartedAt"] != row["started_at"]
                or identity["id"] != row["id"]
                or labels.get("com.docker.compose.service") != row["service"]
                or labels.get("com.docker.compose.project") != host.PROJECT
                or container["State"]["Status"] != "exited"):
            raise RuntimeError("restore_main_container_identity_changed")
    from .supervisor import jobs

    for job in jobs(directory):
        if host.tagged_processes(job["token"]):
            raise RuntimeError("restore_main_registered_process_active")
    sample = host.host_sample(admission.get("release_path", registry["release"]))
    minimum = (db.RESTORE_MEMORY + int(1.5 * host.GIB)) if prospective else int(1.5 * host.GIB)
    if (sample["memory_available"] < minimum or sample["cpus"] < db.RESTORE_CPU + 0.5
            or sample["disk_free"] < 15 * host.GIB):
        raise RuntimeError("restore_host_headroom_insufficient")
    return items


def active(directory: Path) -> bool:
    path = operation_path(directory)
    if not path.is_file():
        return False
    operation = read_operation(directory)
    cleanup = directory / f"restore-{operation['token']}-cleanup.result.json"
    return not cleanup.is_file() or json.loads(cleanup.read_text()).get("status") != "completed"


def _controller_present(directory: Path, token: str) -> bool:
    for path in directory.glob(f"restore-{token}-controller*.json"):
        value = json.loads(path.read_text())
        identity = value.get("identity")
        if identity and host.identity_matches(identity):
            return True
    return False


@contextmanager
def _controller_lease(directory: Path):
    descriptor = os.open(directory / "restore-controller.lock",
                         os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("restore_controller_lease_busy") from exc
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _launch_exclusive(directory: Path, operation: dict, *, resume: bool = False) -> None:
    with _controller_lease(directory):
        if _controller_present(directory, operation["token"]):
            raise RuntimeError("restore_controller_already_running")
        _launch(directory, operation, resume=resume)


def _launch(directory: Path, operation: dict, *, resume: bool = False) -> None:
    token = uuid.uuid4().hex
    read_fd, write_fd = os.pipe()
    cmd = [sys.executable, "-m", "workflows.evals.hindsight_memory_probe.restore_controller",
           "--state", str(directory), "--token", operation["token"], "--gate-fd", str(read_fd)]
    if resume:
        cmd.append("--resume")
    child = None
    try:
        child = subprocess.Popen(cmd, cwd=Path(operation["release_path"]), pass_fds=(read_fd,),
                                 start_new_session=True,
                                 env={**os.environ, "ADE_PROBE_PROCESS_OWNER": token},
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.close(read_fd)
        read_fd = -1
        identity = host.registered_child_identity(child.pid, cmd, token, child)
        if identity is None:
            raise RuntimeError("restore_controller_identity_missing")
        ReceiptStore(directory).write(f"restore-{operation['token']}-controller-{token}.json", {
            "token": operation["token"], "controller_token": token, "identity": identity,
            "deadline": operation["deadline"], "resume": resume, "created_at": time.time(),
        })
        if host.registered_child_identity(child.pid, cmd, token, child) != identity:
            raise RuntimeError("restore_controller_identity_changed")
        if time.time() >= operation["deadline"]:
            raise RuntimeError("restore_controller_deadline_elapsed")
        os.write(write_fd, b"1")
        os.close(write_fd)
    except Exception:
        if child is not None and child.poll() is None:
            child.kill()
            child.wait(timeout=5)
        for descriptor in (read_fd, write_fd):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        raise


def _start_unlocked(directory: Path, timeout: int = MAX_RESTORE_SECONDS) -> dict:
    if not 1 <= timeout <= MAX_RESTORE_SECONDS:
        raise RuntimeError("restore_timeout_invalid")
    restore_root = directory / "restore"
    if (operation_path(directory).exists() or list(directory.glob("restore-*.json"))
            or (restore_root.exists() and any(restore_root.iterdir()))):
        raise RuntimeError("restore_prior_or_partial_publication_exists")
    registry, epoch, admission, evidence = _load_main(directory)
    releases.verify(epoch["release"])
    now = time.time()
    deadline = min(now + timeout, WORK_CUTOFF - CLEANUP_RESERVE_SECONDS)
    cleanup_deadline = min(WORK_CUTOFF, deadline + CLEANUP_RESERVE_SECONDS)
    if deadline <= now:
        raise RuntimeError("restore_cleanup_reserve_unavailable")
    token = uuid.uuid4().hex
    restore_root = directory / "restore" / token
    source_image = f"ade-hindsight-probe-db:{Path(epoch['release']).name}"
    compose = db.write_compose(restore_root, token, source_image, evidence["dump"]["image_id"])
    operation = {
        "schema": 1, "status": "admitted", "token": token,
        "registry_sha256": registry["registry_sha256"], "epoch_sha256": epoch["sha256"],
        "parent_finalization_token": admission["token"], "parent_stopped_epoch_sha256": epoch["sha256"],
        "release_path": epoch["release"], "admitted_at": now, "deadline": deadline,
        "cleanup_deadline": cleanup_deadline,
        "hard_deadline": DEADLINE, "restore_memory_bytes": db.RESTORE_MEMORY,
        "restore_cpu": db.RESTORE_CPU,
        "finalization": {"containers": admission["containers"], "restart_selection": admission["restart_selection"],
                         "restart_readback": admission["restart_readback"]},
        "archive": {"path": str(evidence["archive"]), "sha256": evidence["dump"]["sha256"],
                    "bytes": evidence["dump"]["bytes"], "dump_result_sha256": candidate_database.sha256_file(directory / evidence["finalized"]["dump_result"])},
        "snapshot": {"path": str(evidence["snapshot_path"]), "sha256": candidate_database.sha256_file(evidence["snapshot_path"]),
                     "root": str(directory / "finalization" / admission["token"])},
        "selection": {"path": str(evidence["selection_path"]), "sha256": candidate_database.sha256_file(evidence["selection_path"]),
                      "restart_proof_sha256": admission["restart_readback"]["sha256"]},
        "compose": compose, "restore_root": str(restore_root), "state_directory": str(directory),
    }
    operation_file = directory / "restore-operation.json"
    ReceiptStore(directory).write(operation_file.name, operation)
    ReceiptStore(directory).write("restore-operation-seal.json", {
        "schema": 1, "token": token, "sha256": candidate_database.sha256_file(operation_file),
        "created_at": time.time(),
    })
    _launch_exclusive(directory, operation)
    return {"status": "admitted", "token": token, "deadline": deadline,
            "project": compose["project"], "compose_sha256": compose["sha256"]}


def start(directory: Path, timeout: int = MAX_RESTORE_SECONDS) -> dict:
    from . import restore_retirement, restore_retirement_archive as retirement_archive
    from . import restore_cleanup_recovery
    from . import restore_post_snapshot_recovery

    with restore_retirement.admission_lease(directory):
        retirement_archive.prepare_next_attempt(directory)
        retirement_archive.validate_retired_history(directory)
        restore_cleanup_recovery.prepare_next_attempt(directory)
        restore_post_snapshot_recovery.prepare_next_attempt(directory)
        return _start_unlocked(directory, timeout)


def inspect(directory: Path) -> dict:
    operation = read_operation(directory)
    with restore_cleanup.registered_host_readback(directory, operation):
        db.verify_compose(operation)
        controller_alive = _controller_present(directory, operation["token"])
        container = db.restore_container(operation)
        volume = db.verify_volume(operation)
    receipts = {}
    for suffix in ("create", "restore", "snapshot", "compare", "failure", "result", "cleanup"):
        path = directory / f"restore-{operation['token']}-{suffix}.result.json"
        if path.is_file():
            receipts[suffix] = json.loads(path.read_text())
    failure_path = directory / f"restore-{operation['token']}-failure.result.json"
    result_path = directory / f"restore-{operation['token']}-result.json"
    status = ("failed" if failure_path.is_file() else "completed" if result_path.is_file()
              else "deadline_elapsed" if time.time() >= operation["deadline"] else "active")
    return {"status": status, "token": operation["token"],
            "deadline": operation["deadline"], "seconds_remaining": max(0, operation["deadline"] - time.time()),
            "controller_alive": controller_alive,
            "container": None if container is None else db.identity_projection(container),
            "volume_present": volume is not None, "receipts": receipts}


def resume(directory: Path) -> None:
    operation = read_operation(directory)
    stop_requested = (directory / f"restore-{operation['token']}-stop.intent.json").is_file()
    allowed_deadline = operation["cleanup_deadline"] if stop_requested else operation["deadline"]
    if time.time() >= allowed_deadline or time.time() >= WORK_CUTOFF:
        raise RuntimeError("restore_resume_deadline_elapsed")
    if any(host.tagged_processes(job["token"])
           for job in restore_process.registered_jobs(directory, operation["token"])):
        raise RuntimeError("restore_registered_process_still_active")
    create_intent = directory / f"restore-{operation['token']}-create.intent.json"
    create_result = directory / f"restore-{operation['token']}-create.result.json"
    with restore_cleanup.registered_host_readback(directory, operation):
        container = db.restore_container(operation)
        volume = db.verify_volume(operation, allow_unregistered=not create_result.exists())
    if create_intent.exists():
        if container is None or container["State"]["Status"] != "running":
            raise RuntimeError("restore_resume_requires_same_running_container")
    elif container is not None or volume is not None:
        raise RuntimeError("restore_resume_fresh_state_collision")
    if ((directory / f"restore-{operation['token']}-failure.result.json").exists()
            or (directory / f"restore-{operation['token']}-result.json").exists()):
        raise RuntimeError("restore_failed_operation_cannot_resume")
    _launch_exclusive(directory, operation, resume=True)


def stop(directory: Path) -> dict:
    operation = read_operation(directory)
    token = operation["token"]
    intent_path = directory / f"restore-{token}-stop.intent.json"
    if intent_path.exists():
        return json.loads(intent_path.read_text())
    if any((directory / f"restore-{token}-{suffix}.result.json").exists()
           for suffix in ("result", "failure", "cleanup")):
        raise RuntimeError("restore_stop_requires_active_operation")
    value = {"schema": 1, "token": token, "registry_sha256": operation["registry_sha256"],
             "epoch_sha256": operation["epoch_sha256"], "requested_at": time.time(),
             "kind": "emergency_restore_preemption"}
    ReceiptStore(directory).write(intent_path.name, value)
    if not _controller_present(directory, token):
        try:
            resume(directory)
        except RuntimeError as exc:
            if str(exc) not in {"restore_controller_already_running", "restore_controller_lease_busy"}:
                raise
    return value



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    sub = parser.add_subparsers(dest="action", required=True)
    start_parser = sub.add_parser("start")
    start_parser.add_argument("--timeout", type=int, default=MAX_RESTORE_SECONDS)
    retire_parser = sub.add_parser("retire-failed-before-create")
    retire_parser.add_argument("--diagnosis", type=Path, required=True)
    recover_parser = sub.add_parser("recover-failed-create-cleanup")
    recover_parser.add_argument("--diagnosis", type=Path, required=True)
    post_restore_parser = sub.add_parser("recover-failed-post-restore-snapshot")
    post_restore_parser.add_argument("--authority", type=Path, required=True)
    authorize_post_restore_parser = sub.add_parser("authorize-failed-post-restore-recovery")
    authorize_post_restore_parser.add_argument("--timeout", type=int, default=300)
    sub.add_parser("inspect")
    sub.add_parser("resume")
    sub.add_parser("stop")
    sub.add_parser("cleanup")
    args = parser.parse_args()
    try:
        if args.action == "start":
            result = start(args.state, args.timeout)
        elif args.action == "retire-failed-before-create":
            from .restore_retirement import retire_failed_before_create

            result = retire_failed_before_create(args.state, args.diagnosis)
        elif args.action == "recover-failed-create-cleanup":
            from .restore_cleanup_recovery import recover

            result = recover(args.state, args.diagnosis)
        elif args.action == "recover-failed-post-restore-snapshot":
            from .restore_post_snapshot_recovery import recover

            result = recover(args.state, args.authority)
        elif args.action == "authorize-failed-post-restore-recovery":
            from .restore_post_snapshot_contract import issue_authority

            path = issue_authority(args.state, args.timeout)
            result = {"status": "authority_issued", "authority": str(path)}
        elif args.action == "inspect":
            result = inspect(args.state)
        elif args.action == "resume":
            resume(args.state)
            result = {"status": "resumed"}
        elif args.action == "stop":
            result = stop(args.state)
        else:
            result = restore_cleanup.cleanup(args.state)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print("probe_restore_failed; inspect private operation receipts", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
