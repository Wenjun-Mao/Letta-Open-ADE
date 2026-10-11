"""Terminal result and identity race contracts for registered P4 commands."""

import json
import subprocess
import time
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

    def kill(self):
        self.returncode = -9


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
    monkeypatch.setattr(finalization_process.host, "registered_child_identity", lambda *_args: {
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
    monkeypatch.setattr(finalization_process.host, "registered_child_identity", lambda *_args: {
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


def test_finalization_deadline_is_rechecked_after_registration_before_gate(tmp_path, monkeypatch):
    child = FakeChild()
    directory = tmp_path / "receipts" / "supervisor"
    directory.mkdir(parents=True)
    directory.chmod(0o700)
    clock = [90.0]
    identity = {"pid": child.pid, "start_ticks": "42", "uid": 1, "cmd_sha256": "exact"}
    monkeypatch.setattr(finalization_process.time, "time", lambda: clock[0])
    monkeypatch.setattr(finalization_process.uuid, "uuid4", lambda: type("Id", (), {"hex": "b" * 32})())
    monkeypatch.setattr(finalization_process.subprocess, "Popen", lambda *_args, **_kwargs: child)
    monkeypatch.setattr(finalization_process.host, "registered_child_identity",
                        lambda *_args: (clock.__setitem__(0, 100.0) or identity))
    monkeypatch.setattr(finalization_process.host, "stop_processes",
                        lambda *_args: setattr(child, "returncode", -15))
    monkeypatch.setattr(finalization_process.host, "tagged_processes", lambda *_args: [])
    monkeypatch.setattr(finalization_process.quiescence, "finalization_dispatch_admission",
                        lambda *_args: nullcontext())
    monkeypatch.setattr(finalization_process.os, "write", lambda *_args: 1)
    dispatched = []
    monkeypatch.setattr(finalization_process.os, "write", lambda *_args: dispatched.append(True))

    with pytest.raises(RuntimeError, match="deadline_elapsed"):
        finalization_process.run_monitored(
            directory, {"registry_sha256": "r"},
            {"release": "/release/" + "a" * 40, "sha256": "e"},
            {"deadline": 1000}, ["echo", "ok"], 10, monitor_callback=lambda *_args: None,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert dispatched == []
    assert child.returncode == -15


def test_finalization_accepts_empty_cmdline_only_when_owned_child_exits(tmp_path, monkeypatch):
    token = "c" * 32
    proc_root = tmp_path / "proc"
    proc_directory = proc_root / "43211"
    proc_directory.mkdir(parents=True)
    (proc_directory / "environ").write_bytes(f"ADE_PROBE_PROCESS_OWNER={token}\0".encode())
    directory = tmp_path / "receipts" / "supervisor"
    directory.mkdir(parents=True)
    directory.chmod(0o700)
    identity = {"pid": 43211, "start_ticks": "42", "uid": 1, "cmd_sha256": "registered"}

    class ExitingChild:
        pid = 43211

        def __init__(self):
            self.returncode = None
            self.waits = 0

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            self.waits += 1
            if self.waits < 2:
                raise subprocess.TimeoutExpired("registered-child", timeout)
            self.returncode = 0
            (directory / f"job-{token}.result.json").write_text('{"exit_code":0}')
            return self.returncode

    child = ExitingChild()
    monkeypatch.setattr(finalization_process.uuid, "uuid4", lambda: type("Id", (), {"hex": token})())
    monkeypatch.setattr(finalization_process.subprocess, "Popen", lambda *_args, **_kwargs: child)
    monkeypatch.setattr(finalization_process.host, "registered_child_identity", lambda *_args: identity)
    monkeypatch.setattr(finalization_process.host, "identity_matches", lambda *_args: False)
    monkeypatch.setattr(finalization_process.host, "proc_identity", lambda *_args: {
        **identity, "cmd_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    })
    confirm = finalization_process.host.confirm_owned_child_exit
    monkeypatch.setattr(finalization_process.host, "confirm_owned_child_exit",
                        lambda owned_identity, owner_token, process, **kwargs: confirm(
                            owned_identity, owner_token, process, proc_root=proc_root,
                            timeout=min(kwargs.get("timeout", 0.1), 0.1)))
    monkeypatch.setattr(finalization_process.host, "tagged_processes", lambda *_args: [])
    monkeypatch.setattr(finalization_process.quiescence, "finalization_dispatch_admission",
                        lambda *_args: nullcontext())
    monkeypatch.setattr(finalization_process.os, "write", lambda *_args: 1)

    assert finalization_process.run_monitored(
        directory, {"registry_sha256": "r"}, {"release": "/release/" + "a" * 40, "sha256": "e"},
        {"deadline": time.time() + 30}, ["echo", "ok"], 10, monitor_callback=lambda *_args: None,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    assert child.waits == 2
