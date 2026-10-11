"""Host-local finite stop guard for a restarted failed restore container."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

from .restore_post_snapshot_contract import SCOPES, _sha
from .receipts import ReceiptStore
from . import host_guard

_cancelled = False


def _request_cancel(_signum, _frame):
    global _cancelled
    _cancelled = True


def _read_authority(state: Path, operation_token: str, authority_name: str,
                    authority_sha256: str) -> dict:
    operation_path = state / "restore-operation.json"
    seal_path = state / "restore-operation-seal.json"
    authority_path = state / authority_name
    if (any(path.is_symlink() or not path.is_file() for path in (operation_path, seal_path, authority_path))
            or authority_path.parent.resolve() != state.resolve()
            or not re.fullmatch(rf"restore-{operation_token}-post-restore-authority-[a-f0-9]{{32}}\.json",
                                authority_path.name)
            or authority_path.stat().st_mode & 0o377
            or hashlib.sha256(authority_path.read_bytes()).hexdigest() != authority_sha256):
        raise RuntimeError("restore_expiry_source_missing")
    operation_bytes = operation_path.read_bytes()
    operation = json.loads(operation_bytes)
    authority = json.loads(authority_path.read_text())
    failure = state / f"restore-{operation_token}-failure.result.json"
    cleanup = state / f"restore-{operation_token}-cleanup.result.json"
    create = state / f"restore-{operation_token}-create.result.json"
    fields = {"schema", "kind", "admission_token", "token", "operation_sha256",
              "failure_sha256", "cleanup_sha256", "container_id", "volume",
              "recovery_source_sha", "issued_at", "deadline", "scopes"}
    if (set(authority) != fields or authority.get("schema") != 1
            or authority.get("kind") != "failed_post_restore_snapshot_recovery"
            or authority.get("token") != operation_token
            or authority.get("scopes") != SCOPES
            or operation.get("token") != operation_token
            or json.loads(seal_path.read_text()).get("sha256") != hashlib.sha256(operation_bytes).hexdigest()
            or authority.get("token") != operation_token
            or authority.get("operation_sha256") != hashlib.sha256(operation_bytes).hexdigest()
            or failure.is_symlink() or not failure.is_file()
            or authority.get("failure_sha256") != hashlib.sha256(failure.read_bytes()).hexdigest()
            or cleanup.is_symlink() or not cleanup.is_file()
            or authority.get("cleanup_sha256") != hashlib.sha256(cleanup.read_bytes()).hexdigest()
            or create.is_symlink() or not create.is_file()
            or authority.get("container_id") != json.loads(create.read_text()).get("container_id")
            or authority.get("volume") != operation.get("compose", {}).get("volume")
            or not isinstance(authority.get("admission_token"), str)
            or not re.fullmatch(r"[a-f0-9]{32}", authority["admission_token"])
            or type(authority.get("issued_at")) not in (int, float)
            or type(authority.get("deadline")) not in (int, float)
            or authority["deadline"] <= time.time()
            or authority["issued_at"] > time.time()
            or authority["deadline"] > authority["issued_at"] + 600):
        raise RuntimeError("restore_expiry_authority_invalid")
    return authority


def _inspect_exact(container_id: str, owner_token: str, expected: dict) -> dict:
    environment = {**os.environ, "ADE_PROBE_PROCESS_OWNER": owner_token}
    inspected = subprocess.run(["docker", "inspect", container_id], check=True, capture_output=True,
                               timeout=10, env=environment)
    rows = json.loads(inspected.stdout)
    if not isinstance(rows, list) or len(rows) != 1 or rows[0].get("Id") != container_id:
        raise RuntimeError("restore_expiry_container_identity_invalid")
    return rows[0]


def _matches_expected(row: dict, expected: dict) -> bool:
    labels = row.get("Config", {}).get("Labels") or {}
    mounts = row.get("Mounts") or []
    return (labels.get("ade.hindsight.restore.token") == expected["operation_token"]
            and labels.get("com.docker.compose.project") == expected["project"]
            and row.get("Image") == expected["image_id"]
            and len(mounts) == 1 and mounts[0].get("Name") == expected["volume"])


def _stop_exact(container_id: str, owner_token: str, expected: dict) -> dict:
    environment = {**os.environ, "ADE_PROBE_PROCESS_OWNER": owner_token}
    row = _inspect_exact(container_id, owner_token, expected)
    drifted = (not _matches_expected(row, expected)
               or row.get("State", {}).get("StartedAt") != expected["started_at"])
    if row.get("State", {}).get("Status") == "running":
        subprocess.run(["docker", "stop", "--time", "20", container_id], check=True,
                       capture_output=True, timeout=30, env=environment)
    return _stop_readback(container_id, owner_token, expected, drifted=drifted)


def _stop_readback(container_id: str, owner_token: str, expected: dict, *, drifted: bool) -> dict:
    row = _inspect_exact(container_id, owner_token, expected)
    state = row.get("State", {})
    if state.get("Status") == "running":
        raise RuntimeError("restore_expiry_stop_not_observed")
    return {"status": "drifted_container_stopped" if drifted else "expired_stop_completed",
            "container_id": container_id, "started_at": state.get("StartedAt"),
            "container_status": state.get("Status"), "oom_killed": state.get("OOMKilled"),
            "restart_count": row.get("RestartCount")}


def run(state: Path, operation_token: str, authority_name: str, container_id: str,
        started_at: str, deadline: float, authority_sha256: str,
        owner_token: str, gate_fd: int) -> int:
    if not select.select([gate_fd], [], [], 20)[0] or os.read(gate_fd, 1) != b"1":
        return 1
    os.close(gate_fd)
    authority = _read_authority(state, operation_token, authority_name, authority_sha256)
    if (authority.get("admission_token") != owner_token or authority.get("container_id") != container_id
            or authority.get("deadline") != deadline or time.time() >= deadline):
        raise RuntimeError("restore_expiry_registration_invalid")
    operation = json.loads((state / "restore-operation.json").read_text())
    expected = {"operation_token": operation_token, "project": operation["compose"]["project"],
                "image_id": operation["compose"]["source_image_id"], "volume": operation["compose"]["volume"],
                "started_at": started_at}
    signal.signal(signal.SIGTERM, _request_cancel)
    ReceiptStore(state).write(f"restore-{operation_token}-{owner_token}-expiry.ready.json",
                              {"token": operation_token, "expiry_token": owner_token,
                               "deadline": deadline, "ready": True})
    while time.time() < deadline and not _cancelled:
        time.sleep(min(1.0, max(0.05, deadline - time.time())))
    if _cancelled:
        stopped_row = _inspect_exact(container_id, owner_token, expected)
        container_state = stopped_row.get("State", {})
        if (not _matches_expected(stopped_row, expected)
                or container_state.get("Status") != "exited"
                or container_state.get("OOMKilled") is not False or stopped_row.get("RestartCount") != 0):
            raise RuntimeError("restore_expiry_cancel_stop_unproven")
        stopped = {"container_id": container_id, "started_at": container_state.get("StartedAt"),
                   "container_status": container_state.get("Status"), "oom_killed": container_state.get("OOMKilled"),
                   "restart_count": stopped_row.get("RestartCount")}
        cancel_status = ("cancelled_before_database_restart"
                         if stopped["started_at"] == expected["started_at"]
                         else "cancelled_after_database_stop")
        ReceiptStore(state).write(f"restore-{operation_token}-{owner_token}-expiry.result.json",
                                  {"token": operation_token, "expiry_token": owner_token,
                                   "status": cancel_status, **stopped,
                                   "completed_at": time.time()})
        return 0
    result = _stop_exact(container_id, owner_token, expected)
    ReceiptStore(state).write(f"restore-{operation_token}-{owner_token}-expiry.result.json",
                              {"token": operation_token, "expiry_token": owner_token,
                               **result, "completed_at": time.time()})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--authority", required=True)
    parser.add_argument("--container-id", required=True)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--deadline", type=float, required=True)
    parser.add_argument("--authority-sha256", required=True)
    parser.add_argument("--owner-token", required=True)
    parser.add_argument("--gate-fd", type=int, required=True)
    args = parser.parse_args()
    try:
        code = run(args.state, args.token, args.authority, args.container_id,
                   args.started_at, args.deadline, args.authority_sha256,
                   args.owner_token, args.gate_fd)
    except Exception:
        print("restore_expiry_failed; inspect private receipts", file=sys.stderr)
        code = 1
    ReceiptStore(args.state).write(f"job-{args.owner_token}.result.json", {"exit_code": code})
    ReceiptStore(args.state).write(
        f"restore-{args.token}-{args.owner_token}-result.json", {
            "operation": "post-restore-recovery-expiry", "exit_code": code})
    return code


if __name__ == "__main__":
    raise SystemExit(main())


def _require_expiry_guard(job: dict, deadline: float) -> None:
    identity = job.get("identity", {})
    tagged = host_guard.tagged_processes(job.get("token", ""))
    if (time.time() >= deadline or not host_guard.identity_matches(identity)
            or tagged != [identity]):
        raise RuntimeError("restore_post_snapshot_recovery_expiry_guard_lost")

def _start_expiry_timer(directory: Path, operation: dict, authority_path: Path,
                        authority: dict, release_path: str):
    owner = authority["admission_token"]
    token = operation["token"]
    read_fd, write_fd = os.pipe()
    arguments = [sys.executable, "-S", "-m",
        "workflows.evals.hindsight_memory_probe.restore_post_snapshot_expiry",
        "--state", str(directory), "--token", token, "--authority", authority_path.name,
        "--container-id", authority["container_id"],
        "--started-at", json.loads((directory / f"restore-{token}-create.result.json").read_text())["started_at"],
        "--deadline", str(authority["deadline"]), "--authority-sha256", _sha(authority_path),
        "--owner-token", owner, "--gate-fd", str(read_fd)]
    child = None
    try:
        child = subprocess.Popen(arguments, cwd=release_path, pass_fds=(read_fd,), start_new_session=True,
            env={**os.environ, "ADE_PROBE_PROCESS_OWNER": owner},
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.close(read_fd)
        read_fd = -1
        identity = host_guard.registered_child_identity(child.pid, arguments, owner, child,
                                                        timeout=min(2.0, max(0.05, authority["deadline"] - time.time())))
        job = {"schema": 1, "token": owner, "operation_token": token,
               "operation": "post-restore-recovery-expiry", "identity": identity,
               "container_id": authority["container_id"],
               "deadline": authority["deadline"], "command_sha256": hashlib.sha256(
                   json.dumps(arguments).encode()).hexdigest(), "created_at": time.time()}
        ReceiptStore(directory).write(f"restore-{token}-{owner}-job.json", job)
        if (host_guard.registered_child_identity(child.pid, arguments, owner, child) != identity
                or time.time() >= authority["deadline"]):
            raise RuntimeError("restore_post_snapshot_recovery_expiry_registration_invalid")
        os.write(write_fd, b"1")
        os.close(write_fd)
        write_fd = -1
        ready_path = directory / f"restore-{token}-{owner}-expiry.ready.json"
        until = min(time.monotonic() + 3, time.monotonic() + max(0, authority["deadline"] - time.time()))
        while not ready_path.is_file() and child.poll() is None and time.monotonic() < until:
            time.sleep(0.01)
        if (ready_path.is_symlink() or not ready_path.is_file() or child.poll() is not None
                or json.loads(ready_path.read_text()) != {
                    "token": token, "expiry_token": owner, "deadline": authority["deadline"], "ready": True
                }):
            raise RuntimeError("restore_post_snapshot_recovery_expiry_not_ready")
        _require_expiry_guard(job, authority["deadline"])
        return child, job
    except Exception:
        for descriptor in (read_fd, write_fd):
            if descriptor >= 0:
                os.close(descriptor)
        if child is not None and child.poll() is None:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        raise

def _cancel_expiry_timer(directory: Path, operation: dict, child, job) -> None:
    token = operation["token"]
    if child.poll() is None:
        host_guard.stop_processes(job)
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            for identity in host_guard.tagged_processes(job["token"]):
                if host_guard.identity_matches(identity):
                    try:
                        os.kill(identity["pid"], signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            child.wait(timeout=5)
    if host_guard.tagged_processes(job["token"]):
        raise RuntimeError("restore_post_snapshot_recovery_expiry_still_active")
    result = directory / f"restore-{token}-{job['token']}-expiry.result.json"
    create = json.loads((directory / f"restore-{token}-create.result.json").read_text())
    if not result.is_file():
        raise RuntimeError("restore_post_snapshot_recovery_expiry_cancel_unproven")
    proof = json.loads(result.read_text())
    expected_status = ("cancelled_before_database_restart"
                       if proof.get("started_at") == create.get("started_at")
                       else "cancelled_after_database_stop")
    if (proof.get("status") != expected_status
            or proof.get("container_id") != job["container_id"]
            or proof.get("container_status") != "exited"
            or proof.get("oom_killed") is not False or proof.get("restart_count") != 0):
        raise RuntimeError("restore_post_snapshot_recovery_expiry_cancel_unproven")
