"""Host health, ownership, lifecycle, and safe-stop guard contracts."""

import copy
import signal
import os
import subprocess
import sys
from pathlib import Path

import pytest

from workflows.evals.hindsight_memory_probe import (
    epochs,
    host_guard as host,
    supervisor as sup,
)

RELEASE = Path("/mnt/projects/apps/ade-hindsight-probe/releases/" + "a" * 40)
SAFE_SAMPLE = {"memory_available": 10 * host.GIB, "cpus": 2, "disk_free": 30 * host.GIB}


def container(identifier="existing", project="baseline", service="db", status="running"):
    return {
        "Id": identifier,
        "Image": "sha256:synthetic",
        "RestartCount": 0,
        "State": {
            "StartedAt": "synthetic-start",
            "Status": status,
            "OOMKilled": False,
            "Health": {"Status": "healthy"},
        },
        "HostConfig": {"Memory": host.GIB, "NanoCpus": 250000000},
        "Config": {
            "Labels": {
                "com.docker.compose.project": project,
                "com.docker.compose.service": service,
                "com.docker.compose.project.working_dir": str(
                    RELEASE / "workflows/evals/hindsight_memory_probe"
                ),
                "com.docker.compose.project.config_files": str(
                    RELEASE / "workflows/evals/hindsight_memory_probe/compose.yaml"
                ),
            }
        },
    }


@pytest.fixture
def registry(tmp_path, monkeypatch):
    monkeypatch.setattr(sup.releases, "verify", lambda _: {"source_sha": "a" * 40})
    monkeypatch.setattr(host, "host_sample", lambda _: copy.deepcopy(SAFE_SAMPLE))
    monkeypatch.setattr(host, "containers", lambda: [container()])
    sup.initialize(tmp_path, RELEASE, now=sup.STARTED + 1)
    return tmp_path, sup.load_registry(tmp_path)


def write_proc(root, pid, token, start="42", command=b"owned\0"):
    directory = root / str(pid)
    directory.mkdir(exist_ok=True)
    fields = ["S", "1", *["0"] * 17, start, "0"]
    (directory / "stat").write_text(f"{pid} (space in name) " + " ".join(fields))
    (directory / "cmdline").write_bytes(command)
    (directory / "environ").write_bytes(
        ("ADE_PROBE_PROCESS_OWNER=" + token).encode() + b"\0"
    )


def test_memory_floor_requires_thirty_seconds(registry):
    _, value = registry
    reason, low = host.guard_reason(
        value, [container()], host.GIB, 20 * host.GIB, None, 100
    )
    assert reason is None and low == 100
    assert (
        host.guard_reason(value, [container()], host.GIB, 20 * host.GIB, low, 129)[0]
        is None
    )
    assert (
        host.guard_reason(value, [container()], host.GIB, 20 * host.GIB, low, 130)[0]
        == "memory_below_floor_30_seconds"
    )
    assert host.guard_reason(
        value, [container()], 2 * host.GIB, 20 * host.GIB, low, 129
    ) == (None, None)
@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c["State"].update(StartedAt="changed"),
        lambda c: c["State"]["Health"].update(Status="unhealthy"),
        lambda c: c.update(Image="different"),
        lambda c: c.update(RestartCount=1),
    ],
)
def test_baseline_identity_and_health_changes_stop(registry, mutate):
    _, value = registry
    item = container()
    mutate(item)
    assert (
        host.guard_reason(value, [item], 10 * host.GIB, 20 * host.GIB, None, 100)[0]
        == "baseline_identity_or_health_changed"
    )
def test_candidate_oom_and_restart_stop(registry):
    _, value = registry
    candidate = container("owned", host.PROJECT)
    candidate["State"]["OOMKilled"] = True
    assert (
        host.guard_reason(
            value, [container(), candidate], 10 * host.GIB, 20 * host.GIB, None, 100
        )[0]
        == "candidate_oom_or_restart"
    )
    candidate["State"]["OOMKilled"] = False
    candidate["RestartCount"] = 1
    assert (
        host.guard_reason(
            value, [container(), candidate], 10 * host.GIB, 20 * host.GIB, None, 100
        )[0]
        == "candidate_oom_or_restart"
    )
@pytest.mark.parametrize(
    "lifecycle_state,status,exit_code,oom,restarts,health,expected",
    [
        ("planned_stopped", "exited", 0, False, 0, "unhealthy", None),
        ("planned_stopped", "running", 0, False, 0, "unhealthy", "candidate_unhealthy"),
        ("planned_stopped", "exited", 1, False, 0, "unhealthy", "candidate_service_exited"),
        ("planned_stopped", "exited", 0, True, 0, "unhealthy", "candidate_oom_or_restart"),
        ("planned_stopped", "exited", 0, False, 1, "unhealthy", "candidate_oom_or_restart"),
        (None, "exited", 0, False, 0, "unhealthy", "candidate_service_exited"),
        ("planned_stopped", "dead", 0, False, 0, "unhealthy", "candidate_service_exited"),
    ],
)
def test_running_health_is_not_required_after_only_an_exact_clean_planned_stop(
    registry, lifecycle_state, status, exit_code, oom, restarts, health, expected
):
    _, value = registry
    candidate = container("planned-db", host.PROJECT, "db", status)
    candidate["State"].update(ExitCode=exit_code, OOMKilled=oom)
    candidate["State"]["Health"]["Status"] = health
    candidate["RestartCount"] = restarts
    lifecycle_view = {
        "containers": {"planned-db": lifecycle_state} if lifecycle_state else {},
        "reason": None,
    }
    reason, _ = host.guard_reason(
        value, [container(), candidate], 10 * host.GIB, 20 * host.GIB, None, 100,
        lifecycle_view=lifecycle_view,
    )
    assert reason == expected
@pytest.mark.parametrize(
    "lifecycle_view",
    [
        [],
        {},
        {"containers": {}},
        {"containers": None, "reason": None},
        {"containers": {}, "reason": ""},
        {"containers": {"candidate": []}, "reason": None},
    ],
)
def test_malformed_lifecycle_views_fail_closed(registry, lifecycle_view):
    _, value = registry
    candidate = container("owned", host.PROJECT, "db", "exited")
    reason, _ = host.guard_reason(
        value, [container(), candidate], 10 * host.GIB, 20 * host.GIB, None, 100,
        lifecycle_view=lifecycle_view,
    )
    assert reason == "candidate_lifecycle_view_invalid"
def test_planned_stop_for_another_identity_does_not_exempt_exit(registry):
    _, value = registry
    candidate = container("candidate-db", host.PROJECT, "db", "exited")
    candidate["State"]["ExitCode"] = 0
    reason, _ = host.guard_reason(
        value, [container(), candidate], 10 * host.GIB, 20 * host.GIB, None, 100,
        lifecycle_view={"containers": {"different-db": "planned_stopped"}, "reason": None},
    )
    assert reason == "candidate_service_exited"
def test_effective_container_caps_are_checked(registry):
    _, value = registry
    candidate = container("owned", host.PROJECT)
    candidate["HostConfig"]["Memory"] = 0
    assert (
        host.guard_reason(
            value,
            [container(), candidate],
            10 * host.GIB,
            20 * host.GIB,
            None,
            100,
            epochs.INITIAL_ALLOCATIONS,
        )[0]
        == "candidate_resource_limits_drift"
    )
def test_disk_floor_stops_new_work(registry):
    _, value = registry
    assert (
        host.guard_reason(
            value, [container()], 10 * host.GIB, 14 * host.GIB, None, 100
        )[0]
        == "project_disk_below_floor"
    )
def test_conflicting_ownership_never_adopted(registry):
    _, value = registry
    item = container("conflict", host.PROJECT)
    item["Config"]["Labels"]["com.docker.compose.project.working_dir"] = "/elsewhere"
    with pytest.raises(RuntimeError, match="conflicting"):
        host.candidate_containers([item], value)
    assert host.candidate_containers([container()], value) == []
def test_pid_reuse_and_unrelated_process_are_never_signaled(tmp_path):
    write_proc(tmp_path, 101, "owned-token")
    original = host.proc_identity(101, tmp_path)
    assert original["start_ticks"] == "42"
    write_proc(tmp_path, 101, "unrelated-token", start="43")
    write_proc(tmp_path, 102, "owned-token", command=b"owned-child\0")
    calls = []
    host.stop_processes(
        {"identity": original, "token": "owned-token"},
        tmp_path,
        lambda pid, sig: calls.append((pid, sig)),
    )
    assert calls == [(102, signal.SIGTERM)]
    assert not host.identity_matches(original, tmp_path)
def test_registered_process_must_have_positive_token(tmp_path):
    write_proc(tmp_path, 101, "wrong-token")
    identity = host.proc_identity(101, tmp_path)
    with pytest.raises(RuntimeError, match="ownership"):
        host.stop_processes(
            {"identity": identity, "token": "expected-token"}, tmp_path, lambda *_: None
        )


def test_child_registration_retries_empty_and_partial_proc_argv(tmp_path, monkeypatch):
    token = "register-token"
    arguments = [sys.executable, "-m", "worker", "42"]
    directory = tmp_path / "4242"
    directory.mkdir()
    start = ["S", "1", *["0"] * 17, "99", "0"]
    (directory / "stat").write_text("4242 (worker) " + " ".join(start))
    (directory / "environ").write_bytes(("ADE_PROBE_PROCESS_OWNER=" + token).encode() + b"\0")
    (directory / "cmdline").write_bytes(b"")
    child = type("Child", (), {"poll": lambda self: None})()
    expected = b"\0".join(argument.encode() for argument in arguments) + b"\0"
    states = iter((b"", expected[:12], expected))
    def read_bytes(path):
        if path.name != "cmdline":
            return path.open("rb").read()
        try:
            return next(states)
        except StopIteration:
            return expected
    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setattr(host.time, "sleep", lambda _seconds: None)
    identity = host.registered_child_identity(4242, arguments, token, child, proc_root=tmp_path)
    assert identity["pid"] == 4242
    assert identity["start_ticks"] == "99"
    assert identity["cmd_sha256"] == __import__("hashlib").sha256(expected).hexdigest()


def test_child_registration_rejects_unexpected_nonempty_command(tmp_path):
    token = "register-token"
    directory = tmp_path / "4242"
    directory.mkdir()
    (directory / "cmdline").write_bytes(b"/tmp/unexpected\0")
    child = type("Child", (), {"poll": lambda self: None})()
    with pytest.raises(RuntimeError, match="unexpected_command"):
        host.registered_child_identity(4242, [sys.executable, "-m", "worker"], token,
                                       child, proc_root=tmp_path)


def test_child_registration_rejects_start_tick_change_before_publication(tmp_path, monkeypatch):
    token = "register-token"
    arguments = [sys.executable, "-m", "worker"]
    directory = tmp_path / "4242"
    directory.mkdir()
    (directory / "cmdline").write_bytes(b"\0".join(arg.encode() for arg in arguments) + b"\0")
    (directory / "environ").write_bytes(("ADE_PROBE_PROCESS_OWNER=" + token).encode() + b"\0")
    child = type("Child", (), {"poll": lambda self: None})()
    identity = {"pid": 4242, "start_ticks": "42", "uid": os.getuid(),
                "cmd_sha256": __import__("hashlib").sha256(
                    b"\0".join(arg.encode() for arg in arguments) + b"\0").hexdigest()}
    changed = {**identity, "start_ticks": "43"}
    seen = iter((identity, changed))
    monkeypatch.setattr(host, "proc_identity", lambda *_args: next(seen))
    with pytest.raises(RuntimeError, match="registration_changed"):
        host.registered_child_identity(4242, arguments, token, child, proc_root=tmp_path)


@pytest.mark.skipif(not Path("/proc/self/cmdline").exists(), reason="Linux /proc identity contract")
def test_real_linux_popen_registration_binds_pid_start_uid_command_and_owner():
    token = "linux-owner-token"
    arguments = [sys.executable, "-c", "import time; time.sleep(0.2)"]
    child = subprocess.Popen(arguments, env={**os.environ, "ADE_PROBE_PROCESS_OWNER": token})
    try:
        identity = host.registered_child_identity(child.pid, arguments, token, child)
        assert identity["pid"] == child.pid
        assert identity["start_ticks"]
        assert identity["uid"] == os.getuid()
        assert host.identity_matches(identity)
    finally:
        child.terminate()
        child.wait(timeout=5)
def test_stop_only_explicit_owned_ids_preserves_volume(registry, monkeypatch):
    _, value = registry
    owned = container("owned", host.PROJECT)
    commands = []
    monkeypatch.setattr(host, "command_json", lambda args: [owned])
    monkeypatch.setattr(host.subprocess, "run", lambda args, **_: commands.append(args))
    host.stop_containers([container(), owned], value)
    assert commands == [["docker", "stop", "--time", "10", "owned"]]
    assert all(
        "prune" not in cmd and "-v" not in cmd and "baseline" not in cmd
        for cmd in commands
    )
def test_authorized_exec_transition_is_live_via_start_uid_and_unique_token(tmp_path):
    write_proc(tmp_path, 101, "owned-token", command=b"python3\0process_child\0")
    original = host.proc_identity(101, tmp_path)
    write_proc(tmp_path, 101, "owned-token", command=b"docker\0compose\0build\0")
    current = host.proc_identity(101, tmp_path)
    assert (
        current["start_ticks"] == original["start_ticks"]
        and current["uid"] == original["uid"]
    )
    assert current["cmd_sha256"] != original["cmd_sha256"]
    assert host.tagged_processes("owned-token", tmp_path) == [current]
    write_proc(tmp_path, 101, "other-token", start="43", command=b"unrelated\0")
    assert not host.tagged_processes("owned-token", tmp_path)
def test_owned_oneshot_terminal_state_is_not_an_unexpected_service_crash(registry):
    _, value = registry
    oneoff = container(
        "qualified-script", host.PROJECT, service="hindsight", status="exited"
    )
    oneoff["Config"]["Labels"]["com.docker.compose.oneoff"] = "True"
    assert (
        host.guard_reason(
            value, [container(), oneoff], 10 * host.GIB, 20 * host.GIB, None, 100
        )[0]
        is None
    )
def test_shutdown_requires_stopped_readback_not_stop_command_acceptance(registry):
    _, value = registry
    with pytest.raises(RuntimeError, match="shutdown_container"):
        host.ensure_stopped([container("owned", host.PROJECT)], value, [])
    host.ensure_stopped([container("owned", host.PROJECT, status="exited")], value, [])
def test_pinned_hindsight_gets_compatible_bounded_grace(registry, monkeypatch):
    _, value = registry
    owned = container("owned-hindsight", host.PROJECT, service="hindsight")
    calls = []
    monkeypatch.setattr(host, "command_json", lambda _: [owned])
    monkeypatch.setattr(
        host.subprocess, "run", lambda args, **kw: calls.append((args, kw))
    )
    host.stop_containers([owned], value)
    assert calls[0][0] == ["docker", "stop", "--time", "35", "owned-hindsight"]
    assert calls[0][1]["timeout"] == 45


class TerminalTransitionChild:
    pid = 81

    def __init__(self, exit_after_waits=None):
        self.returncode = None
        self.exit_after_waits = exit_after_waits
        self.waits = 0

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.waits += 1
        if self.exit_after_waits is not None and self.waits >= self.exit_after_waits:
            self.returncode = 0
            return 0
        raise subprocess.TimeoutExpired("registered-child", timeout)


def test_owned_empty_cmdline_is_accepted_only_when_same_child_exits(tmp_path, monkeypatch):
    token = "terminal-owner"
    child = TerminalTransitionChild(exit_after_waits=3)
    proc_directory = tmp_path / str(child.pid)
    proc_directory.mkdir()
    # Linux may expose both proc files as readable but empty during exit_mm.
    (proc_directory / "environ").write_bytes(b"")
    identity = {"pid": child.pid, "start_ticks": "42", "uid": os.getuid(), "cmd_sha256": "registered"}
    empty_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    monkeypatch.setattr(host, "proc_identity", lambda *_args: {**identity, "cmd_sha256": empty_hash})

    assert host.confirm_owned_child_exit(identity, token, child, proc_root=tmp_path, timeout=0.1)
    assert child.returncode == 0


def test_wrong_nonempty_cmdline_during_terminal_check_is_fatal(tmp_path, monkeypatch):
    child = TerminalTransitionChild(exit_after_waits=2)
    identity = {"pid": child.pid, "start_ticks": "42", "uid": os.getuid(), "cmd_sha256": "registered"}
    monkeypatch.setattr(host, "proc_identity", lambda *_args: {**identity, "cmd_sha256": "wrong"})
    with pytest.raises(RuntimeError, match="command_changed"):
        host.confirm_owned_child_exit(identity, "owner", child, proc_root=tmp_path, timeout=0.1)


def test_empty_cmdline_that_remains_live_is_fatal(tmp_path, monkeypatch):
    child = TerminalTransitionChild()
    identity = {"pid": child.pid, "start_ticks": "42", "uid": os.getuid(), "cmd_sha256": "registered"}
    monkeypatch.setattr(host, "proc_identity", lambda *_args: {
        **identity, "cmd_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    })
    with pytest.raises(RuntimeError, match="transition_still_live"):
        host.confirm_owned_child_exit(identity, "owner", child, proc_root=tmp_path, timeout=0.05)


def test_empty_cmdline_and_empty_environ_that_remain_live_are_fatal(tmp_path, monkeypatch):
    child = TerminalTransitionChild()
    proc_directory = tmp_path / str(child.pid)
    proc_directory.mkdir()
    (proc_directory / "cmdline").write_bytes(b"")
    (proc_directory / "environ").write_bytes(b"")
    identity = {"pid": child.pid, "start_ticks": "42", "uid": os.getuid(), "cmd_sha256": "registered"}
    empty_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    monkeypatch.setattr(host, "proc_identity", lambda *_args: {**identity, "cmd_sha256": empty_hash})

    with pytest.raises(RuntimeError, match="transition_still_live"):
        host.confirm_owned_child_exit(identity, "owner", child, proc_root=tmp_path, timeout=0.05)


def test_empty_cmdline_with_nonempty_environment_without_owner_is_fatal(tmp_path, monkeypatch):
    child = TerminalTransitionChild()
    proc_directory = tmp_path / str(child.pid)
    proc_directory.mkdir()
    (proc_directory / "environ").write_bytes(b"OTHER=value\0")
    identity = {"pid": child.pid, "start_ticks": "42", "uid": os.getuid(), "cmd_sha256": "registered"}
    empty_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    monkeypatch.setattr(host, "proc_identity", lambda *_args: {**identity, "cmd_sha256": empty_hash})

    with pytest.raises(RuntimeError, match="owner_changed"):
        host.confirm_owned_child_exit(identity, "owner", child, proc_root=tmp_path, timeout=0.05)
