"""Persisted launch handshake and terminal exit receipt; stdlib only."""

import json
import os
import sys
import select
from pathlib import Path

from .receipts import ReceiptStore

if __name__ == "__main__":
    descriptor = int(sys.argv[1])
    # A registration that stalls before durable publication cannot leave a gated child forever.
    if not select.select([descriptor], [], [], 20)[0] or os.read(descriptor, 1) != b"1":
        raise SystemExit(1)
    os.close(descriptor)
    command = json.loads(sys.argv[2])
    # Keep a small root reaper: a gone PID alone cannot prove command success.
    child = os.fork()
    if child == 0:
        os.execvpe(command[0], command, os.environ)
    _, status = os.waitpid(child, 0)
    code = os.waitstatus_to_exitcode(status)
    if command[0:2] == ["docker", "compose"] and "up" in command:
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
