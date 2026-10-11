"""The restore command runner may accept only an owned terminal procfs transition."""

import subprocess
import time

from workflows.evals.hindsight_memory_probe import restore_process


def test_restore_command_accepts_empty_cmdline_only_after_exact_child_exit(tmp_path, monkeypatch):
    token = "d" * 32
    proc_root = tmp_path / "proc"
    proc_directory = proc_root / "43212"
    proc_directory.mkdir(parents=True)
    (proc_directory / "environ").write_bytes(f"ADE_PROBE_PROCESS_OWNER={token}\0".encode())
    state = tmp_path / "receipts"
    state.mkdir(mode=0o700)
    identity = {"pid": 43212, "start_ticks": "42", "uid": 1, "cmd_sha256": "registered"}

    class ExitingChild:
        pid = 43212

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
            (state / f"job-{token}.result.json").write_text('{"exit_code":0}')
            return self.returncode

    child = ExitingChild()
    monkeypatch.setattr(restore_process.uuid, "uuid4", lambda: type("Id", (), {"hex": token})())
    monkeypatch.setattr(restore_process.subprocess, "Popen", lambda *_args, **_kwargs: child)
    monkeypatch.setattr(restore_process, "_validate_command", lambda *_args: None)
    monkeypatch.setattr(restore_process.host, "registered_child_identity", lambda *_args: identity)
    monkeypatch.setattr(restore_process.host, "identity_matches", lambda *_args: False)
    monkeypatch.setattr(restore_process.host, "proc_identity", lambda *_args: {
        **identity, "cmd_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    })
    monkeypatch.setattr(restore_process.host, "tagged_processes", lambda *_args: [])
    monkeypatch.setattr(restore_process.os, "write", lambda *_args: 1)
    confirm = restore_process.host.confirm_owned_child_exit
    monkeypatch.setattr(restore_process.host, "confirm_owned_child_exit",
                        lambda owned_identity, owner_token, process, **kwargs: confirm(
                            owned_identity, owner_token, process, proc_root=proc_root,
                            timeout=min(kwargs.get("timeout", 0.1), 0.1)))
    operation = {"token": "e" * 32, "state_directory": str(state),
                 "release_path": "/release", "deadline": time.time() + 30,
                 "cleanup_deadline": time.time() + 30,
                 "compose": {"project": "project", "path": "/compose.yaml", "volume": "volume"}}

    assert restore_process.run_command(
        state, operation, ["docker", "inspect", "container"], 10,
        operation_label="post-restore-recovery-stop", monitor=lambda: None) == 0
    assert child.waits == 2
