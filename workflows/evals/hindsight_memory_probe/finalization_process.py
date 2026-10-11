"""Registered subprocess supervision used by ordered finalization."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from . import host_guard as host, quiescence
from .campaign_clock import WORK_CUTOFF
from .receipts import ReceiptStore


def run_monitored(directory: Path, registry: dict, epoch: dict, admitted: dict,
                  command: list[str], timeout: int, *, monitor_callback,
                  stdout, stderr, stdin=subprocess.DEVNULL) -> int:
    token = uuid.uuid4().hex
    deadline = min(time.time() + timeout, admitted["deadline"], WORK_CUTOFF)
    read_fd, write_fd = os.pipe()
    command_json = json.dumps(command)
    operation = (
        "pg_dump" if "pg_dump" in command else
        "pg_restore" if "pg_restore" in command else
        "psql" if "psql" in command else "docker_stop"
    )
    child = None
    identity = None
    job = None
    try:
        child = subprocess.Popen(
            [sys.executable, "-m", "workflows.evals.hindsight_memory_probe.process_child",
             str(read_fd), command_json, str(directory), token],
            cwd=epoch["release"], pass_fds=(read_fd,), start_new_session=True,
            env={**os.environ, "ADE_PROBE_PROCESS_OWNER": token,
                 "PROBE_RELEASE_SHA": Path(epoch["release"]).name,
                 "ADE_PROBE_REGISTRY_SHA256": registry["registry_sha256"],
                 "ADE_PROBE_EPOCH_SHA256": epoch["sha256"]},
            stdin=stdin, stdout=stdout, stderr=stderr,
        )
        os.close(read_fd)
        read_fd = -1
        identity = host.proc_identity(child.pid)
        job = {
            "kind": "p4-finalization", "operation": operation, "token": token,
            "identity": identity, "deadline": deadline,
            "epoch_sha256": epoch["sha256"], "registry_sha256": registry["registry_sha256"],
            "command_sha256": hashlib.sha256(command_json.encode()).hexdigest(),
            "created": time.time(),
        }
        if identity is None:
            raise RuntimeError("finalization_process_identity_missing")
        with quiescence.finalization_dispatch_admission(directory, registry, epoch, admitted):
            ReceiptStore(directory).write(f"job-{token}.json", job)
            os.write(write_fd, b"1")
        os.close(write_fd)
        write_fd = -1
        while child.poll() is None:
            monitor_callback(directory, registry, epoch, admitted, token)
            if not host.identity_matches(identity):
                # The monitor callback can outlast a short, successful command.
                # Only treat identity loss as a violation while the registered
                # root is still alive; a terminal result is checked below.
                if child.poll() is None:
                    raise RuntimeError("finalization_process_identity_changed")
            remaining = deadline - time.time()
            if remaining <= 0:
                raise RuntimeError("finalization_process_deadline_elapsed")
            try:
                child.wait(timeout=min(5, remaining))
            except subprocess.TimeoutExpired:
                continue
        result_path = directory / f"job-{token}.result.json"
        if not result_path.is_file():
            raise RuntimeError("finalization_process_result_missing")
        result = json.loads(result_path.read_text())
        if (not isinstance(result, dict) or type(result.get("exit_code")) is not int
                or result["exit_code"] != child.returncode):
            raise RuntimeError("finalization_process_result_invalid")
        if host.tagged_processes(token):
            raise RuntimeError("finalization_process_descendant_active")
        return result["exit_code"]
    except Exception:
        for descriptor in (read_fd, write_fd):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if job is not None and identity is not None:
            host.stop_processes(job)
        if child is not None and child.poll() is None:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if job is not None and identity is not None:
                    for proc in host.tagged_processes(token):
                        if host.identity_matches(proc):
                            try:
                                os.kill(proc["pid"], signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                else:
                    child.kill()
                child.wait(timeout=5)
        raise
