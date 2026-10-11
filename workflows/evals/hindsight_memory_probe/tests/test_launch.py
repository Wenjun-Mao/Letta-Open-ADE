import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from workflows.evals.hindsight_memory_probe import (
    epochs,
    host_guard as host,
    launch,
    supervisor,
)
from workflows.evals.hindsight_memory_probe.receipts import ReceiptStore

RELEASE = Path("/mnt/projects/apps/ade-hindsight-probe/releases/" + "a" * 40)
SAMPLE = {"memory_available": 10 * host.GIB, "cpus": 2, "disk_free": 30 * host.GIB}


@pytest.fixture
def supervised(tmp_path, monkeypatch):
    monkeypatch.setattr(supervisor.releases, "verify", lambda _: {})
    monkeypatch.setattr(host, "host_sample", lambda _: copy.deepcopy(SAMPLE))
    monkeypatch.setattr(host, "containers", lambda: [])
    monkeypatch.setattr(host, "identity_matches", lambda _: True)
    monkeypatch.setattr(host, "tagged_processes", lambda _: [])
    monkeypatch.setattr(launch.time, "time", lambda: supervisor.STARTED + 10)
    supervisor.initialize(tmp_path, RELEASE, now=supervisor.STARTED + 1)
    registry = supervisor.load_registry(tmp_path)
    epoch = epochs.active(tmp_path, registry)
    ReceiptStore(tmp_path).write(
        "one.controller.json",
        {
            "identity": {},
            "registry_sha256": registry["registry_sha256"],
            "epoch_sha256": epoch["sha256"],
        },
    )
    with supervisor.lease(tmp_path):
        yield tmp_path


@pytest.mark.parametrize(
    "kind,args,match",
    [
        ("work", ["build", "db"], "registered_as_build"),
        ("work", ["up", "-d"], "qualified_local_images"),
        ("work", ["run", "runner"], "qualified_local_images"),
        ("work", ["up", "--build"], "override_rejected"),
        ("work", ["up", "--env-file=/tmp/native.env"], "override_rejected"),
        ("work", ["run", "-v", "/var/run/docker.sock:/sock"], "override_rejected"),
        ("work", ["restart", "hindsight"], "pause_and_diagnosed_rearm"),
        ("dummy", ["any-command"], "no_command"),
    ],
)
def test_unsafe_command_contracts_fail_before_spawn(supervised, kind, args, match):
    with pytest.raises(RuntimeError, match=match):
        launch.launch(supervised, kind, 60, args)
    assert not list(supervised.glob("job-*.json"))


def test_launch_registers_identity_deadline_and_caps_before_gate(
    supervised, monkeypatch
):
    calls = []
    identity = {"pid": 123, "start_ticks": "42", "uid": 1000, "cmd_sha256": "gate"}
    monkeypatch.setattr(host, "proc_identity", lambda _: identity)

    def spawn(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(pid=123)

    def send_gate(fd, value):
        receipt = json.loads(next(supervised.glob("job-*.json")).read_text())
        assert (
            receipt["identity"] == identity
            and receipt["deadline"] == supervisor.STARTED + 70
        )
        assert value == b"1"
        return 1

    monkeypatch.setattr(launch.subprocess, "Popen", spawn)
    monkeypatch.setattr(launch.os, "write", send_gate)
    assert launch.launch(supervised, "build", 60, ["build", "db"]) == 123
    environment = calls[0][1]["env"]
    assert environment["PROBE_RELEASE_SHA"] == "a" * 40
    assert environment["COMPOSE_PARALLEL_LIMIT"] == "1"
    assert environment["PROBE_HINDSIGHT_MEMORY"] == str(6 * host.GIB)
    command = json.loads(calls[0][0][4])
    assert command[0:4] == ["docker", "compose", "--project-name", host.PROJECT]
    assert (
        str(RELEASE / "workflows/evals/hindsight_memory_probe/compose.yaml") in command
    )


def test_launch_rejects_deadline_margin_and_unregistered_controller(
    supervised, monkeypatch
):
    monkeypatch.setattr(launch.time, "time", lambda: supervisor.WORK_CUTOFF)
    with pytest.raises(RuntimeError, match="deadline"):
        launch.launch(supervised, "dummy", 60, [])
    monkeypatch.setattr(launch.time, "time", lambda: supervisor.STARTED + 10)
    monkeypatch.setattr(host, "identity_matches", lambda _: False)
    with pytest.raises(RuntimeError, match="detached_supervisor"):
        launch.launch(supervised, "dummy", 60, [])
