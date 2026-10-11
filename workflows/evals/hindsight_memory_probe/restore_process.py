"""Registered, finite host subprocesses for the disposable restore controller."""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from . import host_guard as host
from .receipts import ReceiptStore

IDENTITY_READBACK = "restore-identity-readback"
IDENTITY_LIST_READBACK = "restore-identity-list-readback"
OPERATOR_READBACK = "restore-operator-readback"
OPERATOR_LIST_READBACK = "restore-operator-list-readback"
POST_RESTORE_RECOVERY_READBACK = "post-restore-recovery-readback"
READ_ONLY_HOST_OPERATIONS = frozenset({
    IDENTITY_READBACK,
    IDENTITY_LIST_READBACK,
    OPERATOR_READBACK,
    OPERATOR_LIST_READBACK,
})
CLEANUP_RESERVE_OPERATIONS = frozenset({
    "cleanup-preserve-stop",
    "cleanup-stop",
    "cleanup-remove-container",
    "cleanup-remove-volume",
    OPERATOR_READBACK,
    OPERATOR_LIST_READBACK,
    "cleanup-recovery-readback",
    "cleanup-recovery-stop",
    "cleanup-recovery-remove-container",
    "cleanup-recovery-remove-volume",
    "post-restore-recovery-readback",
    "post-restore-recovery-start",
    "post-restore-recovery-snapshot-query",
    "post-restore-recovery-stop",
    "post-restore-recovery-remove-container",
    "post-restore-recovery-remove-volume",
})


def registered_jobs(directory: Path, operation_token: str) -> list[dict]:
    pattern = re.compile(rf"restore-{re.escape(operation_token)}-([a-f0-9]{{32}})-job\.json")
    jobs = []
    for path in sorted(directory.iterdir()):
        match = pattern.fullmatch(path.name)
        if match is None:
            continue
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("restore_process_registration_invalid")
        job = json.loads(path.read_text())
        if (not isinstance(job, dict) or job.get("schema") != 1
                or job.get("token") != match.group(1)
                or job.get("operation_token") != operation_token):
            raise RuntimeError("restore_process_registration_invalid")
        jobs.append(job)
    return jobs


def command_deadline(operation: dict, timeout: int, operation_label: str, now: float) -> float:
    uses_cleanup_reserve = operation_label in CLEANUP_RESERVE_OPERATIONS
    fixed_deadline = operation.get("cleanup_deadline", operation["deadline"]) if uses_cleanup_reserve else operation["deadline"]
    return min(now + timeout, fixed_deadline)


def _validate_command(operation: dict, command: list[str]) -> None:
    if not command or command[0] != "docker" or any(not isinstance(arg, str) or "\0" in arg for arg in command):
        raise RuntimeError("restore_command_invalid")
    recovered_id = operation.get("_cleanup_recovery_container_id")
    if recovered_id:
        volume = operation["compose"]["volume"]
        allowed = (
            command[1:] == ["ps", "-aq", "--no-trunc"]
            or command[1:2] == ["inspect"] and len(command) >= 3
            or command[1:] == ["volume", "ls", "-q", "--filter", "name=" + volume]
            or command[1:] == ["volume", "inspect", volume]
            or command[1:] == ["stop", "--time", "20", recovered_id]
            or command[1:] == ["rm", recovered_id]
            or command[1:] == ["ps", "-aq", "--no-trunc", "--filter", "volume=" + volume]
            or command[1:] == ["volume", "rm", volume]
            or operation.get("_post_restore_recovery") is True
            and command[1:] == ["start", recovered_id]
        )
        if operation.get("_post_restore_recovery") is True and command[1:2] == ["exec"]:
            from .restore_snapshot import allowed_queries

            allowed = (command[2:4] == ["-i", recovered_id]
                       and command[4:11] == ["psql", "-U", "hindsight_probe", "-d",
                                             "hindsight_probe", "-At", "-c"]
                       and len(command) == 12 and command[11] in allowed_queries())
        if not allowed:
            raise RuntimeError("restore_cleanup_recovery_command_not_allowed")
        return
    if command[1:2] == ["compose"]:
        prefix = ["docker", "compose", "--project-name", operation["compose"]["project"],
                  "-f", operation["compose"]["path"]]
        if command[:len(prefix)] != prefix or command[len(prefix):] not in (
            ["up", "-d", "--pull", "never", "db"], ["ps", "-aq", "--no-trunc"],
            ["stop", "--timeout", "20", "db"],
        ):
            raise RuntimeError("restore_compose_command_not_allowed")
        return
    if command[1:2] == ["exec"]:
        if len(command) < 5 or command[2] != "-i":
            raise RuntimeError("restore_exec_command_not_allowed")
        container_id = command[3]
        suffix = command[4:]
        allowed = (
            suffix == ["pg_restore", "--exit-on-error", "--single-transaction", "--no-owner", "--no-acl",
                       "-U", "hindsight_probe", "-d", "hindsight_probe"]
        )
        from .restore_snapshot import allowed_queries

        query_ok = (suffix[:1] == ["psql"] and suffix[1:]
                    and suffix[1:7] == ["-U", "hindsight_probe", "-d", "hindsight_probe", "-At", "-c"]
                    and len(suffix) == 8 and suffix[7] in allowed_queries())
        create_path = Path(operation["state_directory"]) / f"restore-{operation['token']}-create.result.json"
        created = json.loads(create_path.read_text()) if create_path.is_file() else {}
        if not container_id or container_id != created.get("container_id") or not (allowed or query_ok):
            raise RuntimeError("restore_exec_command_not_allowed")
        return
    if tuple(command[1:]) == ("ps", "-aq", "--no-trunc"):
        return
    if (command[1:4] == ["volume", "ls", "-q"] and len(command) == 6
            and command[4] == "--filter" and command[5] == "name=" + operation["compose"]["volume"]):
        return
    if command[1:2] == ["inspect"] and len(command) >= 3:
        return
    if (command[1:3] == ["image", "inspect"] and len(command) == 4
            and command[3] == operation["compose"]["source_image"]):
        return
    if (command[1:3] == ["volume", "inspect"] and len(command) == 4
            and command[3] == operation["compose"]["volume"]):
        return
    create_path = Path(operation["state_directory"]) / f"restore-{operation['token']}-create.result.json"
    created = json.loads(create_path.read_text()) if create_path.is_file() else {}
    if (command[1:2] == ["stop"] and len(command) == 5 and command[2:4] == ["--time", "20"]
            and command[4] == created.get("container_id")):
        return
    if command[1:2] == ["rm"] and len(command) == 3 and command[2] == created.get("container_id"):
        return
    if (command[1:3] == ["volume", "rm"] and len(command) == 4
            and command[3] == operation["compose"]["volume"]):
        return
    if (command[1:4] == ["ps", "-aq", "--no-trunc"] and len(command) == 6
            and command[4] == "--filter"
            and command[5] == "volume=" + operation["compose"]["volume"]):
        return
    raise RuntimeError("restore_host_command_not_allowed")


def run_command(directory: Path, operation: dict, command: list[str], timeout: int, *,
                operation_label: str, monitor, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL) -> int:
    _validate_command(operation, command)
    token = uuid.uuid4().hex
    deadline = command_deadline(operation, timeout, operation_label, time.time())
    if deadline <= time.time():
        raise RuntimeError("restore_process_deadline_unavailable")
    read_fd, write_fd = os.pipe()
    child = None
    job = None
    command_json = json.dumps(command)
    lifecycle_scope = None
    compose_prefix = ["docker", "compose", "--project-name", operation["compose"]["project"],
                      "-f", operation["compose"]["path"]]
    if command[:len(compose_prefix)] == compose_prefix and command[len(compose_prefix):] == [
            "up", "-d", "--pull", "never", "db"]:
        lifecycle_scope = json.dumps({"kind": "disposable_restore", "token": operation["token"],
                                      "project": operation["compose"]["project"],
                                      "compose_path": operation["compose"]["path"],
                                      "compose_sha256": operation["compose"]["sha256"]})
    arguments = [sys.executable, "-S", "-m", "workflows.evals.hindsight_memory_probe.process_child",
                 str(read_fd), command_json, str(directory), token]
    if lifecycle_scope is not None:
        arguments.append(lifecycle_scope)
    try:
        child = subprocess.Popen(
            arguments,
            cwd=operation["release_path"], pass_fds=(read_fd,), start_new_session=True,
            env={**os.environ, "ADE_PROBE_PROCESS_OWNER": token},
            stdin=stdin, stdout=stdout, stderr=stderr,
        )
        os.close(read_fd)
        read_fd = -1
        identity = host.registered_child_identity(child.pid, arguments, token, child)
        job = {"schema": 1, "token": token, "operation_token": operation["token"],
               "operation": operation_label, "identity": identity, "deadline": deadline,
               "command_sha256": hashlib.sha256(command_json.encode()).hexdigest(),
               "created_at": time.time()}
        if operation.get("_post_restore_recovery") is True:
            admission_token = operation.get("_post_restore_recovery_admission_token")
            authority_sha256 = operation.get("_post_restore_recovery_authority_sha256")
            if (not isinstance(admission_token, str) or not re.fullmatch(r"[a-f0-9]{32}", admission_token)
                    or not isinstance(authority_sha256, str)
                    or not re.fullmatch(r"[a-f0-9]{64}", authority_sha256)):
                raise RuntimeError("restore_post_snapshot_recovery_job_authority_missing")
            job["recovery_admission_token"] = admission_token
            job["recovery_authority_sha256"] = authority_sha256
        ReceiptStore(directory).write(f"restore-{operation['token']}-{token}-job.json", job)
        if host.registered_child_identity(child.pid, arguments, token, child) != identity:
            raise RuntimeError("restore_process_identity_changed")
        if time.time() >= deadline:
            raise RuntimeError("restore_process_deadline_elapsed")
        os.write(write_fd, b"1")
        os.close(write_fd)
        write_fd = -1
        while child.poll() is None:
            if not host.identity_matches(identity):
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise RuntimeError("restore_process_deadline_elapsed")
                if host.confirm_owned_child_exit(identity, token, child,
                                                 timeout=min(0.35, remaining)):
                    if time.time() >= deadline:
                        raise RuntimeError("restore_process_deadline_elapsed")
                    break
            if time.time() >= deadline:
                raise RuntimeError("restore_process_deadline_elapsed")
            monitor()
            try:
                child.wait(timeout=min(5, max(0.05, deadline - time.time())))
            except subprocess.TimeoutExpired:
                continue
        result_path = directory / f"job-{token}.result.json"
        if not result_path.is_file():
            raise RuntimeError("restore_process_result_missing")
        result = json.loads(result_path.read_text())
        if (not isinstance(result, dict) or type(result.get("exit_code")) is not int
                or result["exit_code"] != child.returncode):
            raise RuntimeError("restore_process_result_invalid")
        if host.tagged_processes(token):
            raise RuntimeError("restore_process_descendant_active")
        ReceiptStore(directory).write(f"restore-{operation['token']}-{token}-result.json", {
            "operation": operation_label, "exit_code": result["exit_code"], "completed_at": time.time(),
            "command_sha256": job["command_sha256"],
        })
        return result["exit_code"]
    except Exception:
        for descriptor in (read_fd, write_fd):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if job is not None:
            host.stop_processes(job)
        if child is not None and child.poll() is None:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if job is not None:
                    for identity in host.tagged_processes(token):
                        if host.identity_matches(identity):
                            try:
                                os.kill(identity["pid"], signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                else:
                    child.kill()
                child.wait(timeout=5)
        raise
