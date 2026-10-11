import copy
import json
import shlex
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
        ("work", ["up", "-d"], "compose_service_required"),
        ("work", ["run", "runner"], "qualified_local_images"),
        ("work", ["up", "--build"], "override_rejected"),
        ("work", ["up", "--env-file=/tmp/native.env"], "override_rejected"),
        ("work", ["run", "-v", "/var/run/docker.sock:/sock"], "override_rejected"),
        ("work", ["up", "-f", "/tmp/other-compose.yaml", "db"], "override_rejected"),
        ("work", ["up", "db", "--file", "/tmp/other-compose.yaml"], "override_rejected"),
        ("work", ["exec", "--project-name=other", "db", "psql"], "override_rejected"),
        ("work", ["run", "--privileged", "--pull", "never", "runner"], "option_unrecognized"),
        ("work", ["run", "--device", "/dev/sda", "--pull", "never", "runner"], "option_unrecognized"),
        ("work", ["run", "--pull", "never", "--rm", "--no-deps", "-e", "API_KEY=secret", "runner"], "environment_override_rejected"),
        ("work", ["run", "--pull", "never", "--rm", "--no-deps", "--user", "0", "runner"], "user_override_rejected"),
        ("work", ["up", "--pull", "never", "--pull", "always", "db"], "qualified_local_images"),
        ("work", ["up", "db", "--scale", "runner=2"], "option_unrecognized"),
        ("build", ["build", "db", "--parallel"], "option_unrecognized"),
        ("work", ["restart", "hindsight"], "pause_and_diagnosed_rearm"),
        ("dummy", ["any-command"], "no_command"),
    ],
)
def test_unsafe_command_contracts_fail_before_spawn(supervised, kind, args, match):
    with pytest.raises(RuntimeError, match=match):
        launch.launch(supervised, kind, 60, args)
    assert not list(supervised.glob("job-*.json"))


@pytest.mark.parametrize(
    "change,timeout",
    [
        (lambda args: args.__setitem__(-2, "runner"), 1800),
        (lambda args: args.__setitem__(-1, "/probe/providers.py"), 1800),
        (lambda args: args.__setitem__(args.index("HF_HUB_OFFLINE=0"), "HF_HUB_OFFLINE=1"), 1800),
        (lambda args: args.__setitem__(args.index("python3"), "python"), 1800),
        (lambda args: args.append("--unexpected"), 1800),
        (lambda args: None, 1799),
    ],
)
def test_root_is_rejected_for_every_noncanonical_run(supervised, change, timeout):
    arguments = list(launch.CACHE_PROVISIONING_RUN)
    change(arguments)
    with pytest.raises(RuntimeError, match="compose_user_override_rejected"):
        launch.launch(supervised, "work", timeout, arguments)
    assert not list(supervised.glob("job-*.json"))


def test_exact_operator_runbook_cache_provisioning_recipe_is_admitted(supervised, monkeypatch):
    lines = (Path(launch.__file__).with_name("operator-runbook.md")).read_text().splitlines()
    start = next(index for index, line in enumerate(lines)
                 if line.strip().startswith("--kind work --timeout 1800 -- run --rm"))
    recipe_lines = []
    for line in lines[start:]:
        part = line.strip()
        continues = part.endswith("\\")
        recipe_lines.append(part[:-1].rstrip() if continues else part)
        if not continues:
            break
    recipe = shlex.split(" ".join(recipe_lines))
    assert recipe[:4] == ["--kind", "work", "--timeout", "1800"]
    delimiter = recipe.index("--")
    arguments = recipe[delimiter + 1:]
    assert tuple(arguments) == launch.CACHE_PROVISIONING_RUN

    calls = []
    monkeypatch.setattr(host, "registered_child_identity", lambda *_args: {
        "pid": 123, "start_ticks": "42", "uid": 1000, "cmd_sha256": "gate"
    })
    monkeypatch.setattr(launch.subprocess, "Popen", lambda command, **kwargs: (
        calls.append((command, kwargs)) or SimpleNamespace(pid=123)))
    monkeypatch.setattr(launch.os, "write", lambda *_args: 1)
    assert launch.launch(supervised, "work", 1800, arguments) == 123

    compose_command = json.loads(calls[0][0][4])
    assert compose_command[-len(arguments):] == arguments
    assert "--user" in compose_command and compose_command[compose_command.index("--user") + 1] == "0"
    assert compose_command[compose_command.index("hindsight") + 1:] == ["/probe/cache_model.py"]


def test_launch_registers_identity_deadline_and_caps_before_gate(
    supervised, monkeypatch
):
    monkeypatch.setenv("PROBE_RECEIPTS_DIR", "/tmp/unapproved-receipts")
    registry = supervisor.load_registry(supervised)
    epoch = epochs.active(supervised, registry)
    calls = []
    identity = {"pid": 123, "start_ticks": "42", "uid": 1000, "cmd_sha256": "gate"}
    monkeypatch.setattr(host, "registered_child_identity", lambda *_args: identity)

    def spawn(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(pid=123)

    def send_gate(fd, value):
        receipt = json.loads(next(supervised.glob("job-*.json")).read_text())
        assert (
            receipt["identity"] == identity
            and receipt["deadline"] == supervisor.STARTED + 70
            and receipt["operation"] == "build"
            and receipt["service"] == ["db"]
        )
        assert value == b"1"
        return 1

    monkeypatch.setattr(launch.subprocess, "Popen", spawn)
    monkeypatch.setattr(launch.os, "write", send_gate)
    assert launch.launch(supervised, "build", 60, ["build", "db"]) == 123
    environment = calls[0][1]["env"]
    assert environment["PROBE_RELEASE_SHA"] == "a" * 40
    assert environment["ADE_PROBE_REGISTRY_SHA256"] == registry["registry_sha256"]
    assert environment["ADE_PROBE_EPOCH_SHA256"] == epoch["sha256"]
    assert environment["COMPOSE_PARALLEL_LIMIT"] == "1"
    assert environment["PROBE_HINDSIGHT_MEMORY"] == str(6 * host.GIB)
    assert environment["PROBE_RECEIPTS_DIR"] == supervisor.load_registry(supervised)["activation_namespace"]["receipts_root"]
    assert environment["PROBE_RECEIPTS_DIR"] != "/tmp/unapproved-receipts"
    command = json.loads(calls[0][0][4])
    assert command[0:4] == ["docker", "compose", "--project-name", host.PROJECT]
    assert (
        str(RELEASE / "workflows/evals/hindsight_memory_probe/compose.yaml") in command
    )


@pytest.mark.parametrize("fail_after_publication", [False, True])
def test_registration_failure_closes_gate_and_reaps_owned_child(
    supervised, monkeypatch, fail_after_publication
):
    class Child:
        pid = 123
        returncode = None
        waited = False

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            self.waited = True
            self.returncode = 0
            return 0

    child = Child()
    monkeypatch.setattr(launch.subprocess, "Popen", lambda *_args, **_kwargs: child)
    identity = {"pid": 123, "start_ticks": "42", "uid": 1000, "cmd_sha256": "gate"}
    calls = 0

    def readiness(*_args):
        nonlocal calls
        calls += 1
        if calls == (2 if fail_after_publication else 1):
            raise RuntimeError("process_child_registration_unready")
        return identity

    monkeypatch.setattr(host, "registered_child_identity", readiness)
    dispatched = []
    monkeypatch.setattr(launch.os, "write", lambda *_args: dispatched.append(True))
    with pytest.raises(RuntimeError, match="registration_unready"):
        launch.launch(supervised, "dummy", 60, [])
    assert child.waited
    assert dispatched == []
    registrations = list(supervised.glob("job-" + "?" * 32 + ".json"))
    assert bool(registrations) is fail_after_publication


@pytest.mark.parametrize(
    "arguments,expected_child",
    [
        (["exec", "-T", "db", "psql", "-v", "ON_ERROR_STOP=1", "-c", "SELECT 1"],
         ["docker", "compose", "exec", "-T", "db", "psql", "-v", "ON_ERROR_STOP=1", "-c", "SELECT 1"]),
        (["run", "--rm", "--no-deps", "--pull", "never", "runner", "python", "-m", "sample", "-v"],
         ["docker", "compose", "run", "--rm", "--no-deps", "--pull", "never", "runner", "python", "-m", "sample", "-v"]),
    ],
)
def test_compose_child_flags_after_service_are_not_scanned_as_compose_overrides(
    supervised, monkeypatch, arguments, expected_child
):
    calls = []
    monkeypatch.setattr(host, "registered_child_identity", lambda *_args: {"pid": 123, "start_ticks": "42", "uid": 1000, "cmd_sha256": "gate"})
    monkeypatch.setattr(launch.subprocess, "Popen", lambda command, **kwargs: calls.append((command, kwargs)) or SimpleNamespace(pid=123))
    monkeypatch.setattr(launch.os, "write", lambda *_: 1)
    launch.launch(supervised, "work", 60, arguments)
    command = json.loads(calls[0][0][4])
    assert command[0:2] == expected_child[0:2]
    assert command[-len(expected_child[2:]):] == expected_child[2:]


def test_up_options_after_service_are_still_validated_as_compose_options():
    options, boundary, services = launch.compose_service_options(
        ["up", "db", "-d", "--no-build", "--pull", "never"]
    )
    assert services == ["db"]
    assert boundary is None
    assert options == ["-d", "--no-build", "--pull", "never"]


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


def test_build_cancellation_mode_uses_only_owned_pinned_fixture_and_unique_tag(
    supervised, monkeypatch
):
    calls = []
    monkeypatch.setattr(
        host,
        "registered_child_identity",
        lambda *_args: {"pid": 123, "uid": 1000, "start_ticks": "42", "cmd_sha256": "test"},
    )
    monkeypatch.setattr(
        launch.subprocess,
        "Popen",
        lambda args, **kw: calls.append((args, kw)) or SimpleNamespace(pid=123),
    )
    monkeypatch.setattr(launch.os, "write", lambda *_: 1)
    assert launch.launch(supervised, "build-cancel", 90, []) == 123
    command = json.loads(calls[0][0][4])
    job = json.loads(next(supervised.glob("job-" + "?" * 32 + ".json")).read_text())
    assert command[:2] == ["docker", "build"]
    assert (
        command[command.index("--tag") + 1]
        == "ade-hindsight-probe-cancel:" + job["token"]
    )
    assert "--network" in command and command[command.index("--network") + 1] == "none"
    assert command[-1] == str(
        RELEASE / "workflows/evals/hindsight_memory_probe/docker/cancellation"
    )
    assert (
        job["build_sentinel"] == job["token"]
        and calls[0][1]["env"]["DOCKER_BUILDKIT"] == "1"
    )


def test_cancellation_fixture_cannot_be_extended_past_its_finite_sentinel(supervised):
    with pytest.raises(RuntimeError, match="bounded_cancellation"):
        launch.launch(supervised, "build-cancel", 121, [])
