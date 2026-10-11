"""Persisted launch handshake and terminal exit receipt; stdlib only."""

import json
import os
import sys
import select
from pathlib import Path

from .receipts import ReceiptStore


def _validate_completion_scope(completion_scope, command, directory):
    if completion_scope == {"kind": "candidate_epoch"}:
        return
    if not isinstance(completion_scope, dict) or completion_scope.get("kind") != "disposable_restore":
        raise SystemExit("process_lifecycle_scope_invalid")
    from . import restore

    operation = restore.read_operation(directory)
    expected = {"kind": "disposable_restore", "token": operation["token"],
                "project": operation["compose"]["project"],
                "compose_path": operation["compose"]["path"],
                "compose_sha256": operation["compose"]["sha256"]}
    command_prefix = ["docker", "compose", "--project-name", expected["project"],
                      "-f", expected["compose_path"]]
    if (completion_scope != expected or command[:len(command_prefix)] != command_prefix
            or command[len(command_prefix):] != ["up", "-d", "--pull", "never", "db"]):
        raise SystemExit("restore_lifecycle_scope_invalid")


if __name__ == "__main__":
    descriptor = int(sys.argv[1])
    # A registration that stalls before durable publication cannot leave a gated child forever.
    if not select.select([descriptor], [], [], 20)[0] or os.read(descriptor, 1) != b"1":
        raise SystemExit(1)
    os.close(descriptor)
    command = json.loads(sys.argv[2])
    completion_scope = json.loads(sys.argv[5]) if len(sys.argv) > 5 else {"kind": "candidate_epoch"}
    _validate_completion_scope(completion_scope, command, Path(sys.argv[3]))
    # Keep a small root reaper: a gone PID alone cannot prove command success.
    child = os.fork()
    if child == 0:
        os.execvpe(command[0], command, os.environ)
    _, status = os.waitpid(child, 0)
    code = os.waitstatus_to_exitcode(status)
    if (command[0:2] == ["docker", "compose"] and "up" in command
            and completion_scope.get("kind") == "candidate_epoch"):
        try:
            from .lifecycle import complete

            complete(Path(sys.argv[3]), sys.argv[4])
        except Exception:
            os.write(2, b"probe_startup_readback_failed\n")
            code = code or 1
    ReceiptStore(Path(sys.argv[3])).write(
        f"job-{sys.argv[4]}.result.json", {"exit_code": code}
    )
    raise SystemExit(code if code >= 0 else 128 - code)
