"""Terminal result and identity race contracts for registered P4 commands."""

import json
import subprocess
from contextlib import nullcontext

import pytest

from workflows.evals.hindsight_memory_probe import finalization_process


class FakeChild:
    pid = 43210

    def __init__(self):
        self.returncode = None

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            raise subprocess.TimeoutExpired("fake-child", timeout)
        return self.returncode


@pytest.mark.parametrize("receipt,returncode,expected", [
    ({"exit_code": 0}, 0, 0),
    ({"exit_code": 1}, 0, "finalization_process_result_invalid"),
    ({"exit_code": "0"}, 0, "finalization_process_result_invalid"),
    (None, 0, "finalization_process_result_missing"),
])
def test_identity_disappearance_after_monitor_means_check_terminal_receipt(
        tmp_path, monkeypatch, receipt, returncode, expected):
    child = FakeChild()
    monkeypatch.setattr(finalization_process.subprocess, "Popen", lambda *a, **k: child)
    monkeypatch.setattr(finalization_process.host, "proc_identity", lambda _pid: {
        "pid": child.pid, "start_ticks": "1", "uid": 1, "cmd_sha256": "x"})
    # Simulate the root exiting during a slow callback: procfs identity is gone,
    # but the root's wait status and durable process_child receipt are available.
    monkeypatch.setattr(finalization_process.host, "identity_matches", lambda _identity: False)
    monkeypatch.setattr(finalization_process.host, "tagged_processes", lambda _token: [])
    directory = tmp_path / "receipts" / "supervisor"
    directory.mkdir(parents=True)
    directory.chmod(0o700)
    monkeypatch.setattr(finalization_process.quiescence, "finalization_dispatch_admission",
                        lambda *_args: nullcontext())
    monkeypatch.setattr(finalization_process.host, "stop_processes", lambda *_args: [])
    monkeypatch.setattr(finalization_process.os, "write", lambda *_args: 1)

    def callback(_directory, _registry, _epoch, _admitted, token):
        child.returncode = returncode
        if receipt is not None:
            (directory / f"job-{token}.result.json").write_text(json.dumps(receipt))

    args = (directory, {"registry_sha256": "r"}, {"release": "/release/" + "a" * 40,
            "sha256": "e"}, {"deadline": finalization_process.time.time() + 30},
            ["echo", "ok"], 10)
    monkeypatch.setattr(finalization_process.uuid, "uuid4", lambda: type("Id", (), {"hex": "f" * 32})())
    monkeypatch.setattr(finalization_process.time, "time", lambda: 100.0)
    if expected == "finalization_process_result_missing":
        with pytest.raises(RuntimeError, match=expected):
            finalization_process.run_monitored(*args, monitor_callback=callback,
                                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif isinstance(expected, str):
        with pytest.raises(RuntimeError, match=expected):
            finalization_process.run_monitored(*args, monitor_callback=callback,
                                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        assert finalization_process.run_monitored(*args, monitor_callback=callback,
                                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == expected


def test_terminal_root_with_live_tagged_descendant_fails_closed(tmp_path, monkeypatch):
    child = FakeChild()
    monkeypatch.setattr(finalization_process.subprocess, "Popen", lambda *a, **k: child)
    monkeypatch.setattr(finalization_process.host, "proc_identity", lambda _pid: {
        "pid": child.pid, "start_ticks": "1", "uid": 1, "cmd_sha256": "x"})
    monkeypatch.setattr(finalization_process.host, "identity_matches", lambda _identity: False)
    monkeypatch.setattr(finalization_process.host, "tagged_processes", lambda _token: [{"pid": 9}])
    monkeypatch.setattr(finalization_process.quiescence, "finalization_dispatch_admission",
                        lambda *_args: nullcontext())
    monkeypatch.setattr(finalization_process.host, "stop_processes", lambda *_args: [])
    monkeypatch.setattr(finalization_process.os, "write", lambda *_args: 1)
    directory = tmp_path / "receipts" / "supervisor"
    directory.mkdir(parents=True)
    directory.chmod(0o700)

    def callback(_directory, _registry, _epoch, _admitted, token):
        child.returncode = 0
        (directory / f"job-{token}.result.json").write_text('{"exit_code":0}')

    monkeypatch.setattr(finalization_process.uuid, "uuid4", lambda: type("Id", (), {"hex": "a" * 32})())
    monkeypatch.setattr(finalization_process.time, "time", lambda: 100.0)
    with pytest.raises(RuntimeError, match="finalization_process_descendant_active"):
        finalization_process.run_monitored(
            directory, {"registry_sha256": "r"}, {"release": "/release/" + "a" * 40, "sha256": "e"},
            {"deadline": 200}, ["echo", "ok"], 10, monitor_callback=callback,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
