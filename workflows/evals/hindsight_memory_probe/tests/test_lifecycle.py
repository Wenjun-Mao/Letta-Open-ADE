"""Real lifecycle functions with synthetic Docker/process I/O; no OCI qualification claims."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from workflows.evals.hindsight_memory_probe import (
    epochs,
    host_guard as host,
    lifecycle,
    launch,
    supervisor as sup,
)
from workflows.evals.hindsight_memory_probe.receipts import ReceiptStore

RELEASE = Path("/mnt/projects/apps/ade-hindsight-probe/releases/" + "a" * 40)
SAMPLE = {"memory_available": 10 * host.GIB, "cpus": 2, "disk_free": 30 * host.GIB}


def candidate(identifier="owned-db", status="running"):
    return {
        "Id": identifier,
        "Image": "sha256:synthetic",
        "RestartCount": 0,
        "State": {
            "StartedAt": "first-start",
            "FinishedAt": "",
            "Status": status,
            "OOMKilled": False,
        },
        "HostConfig": {"Memory": host.GIB, "NanoCpus": 250000000},
        "Config": {
            "Labels": {
                "com.docker.compose.project": host.PROJECT,
                "com.docker.compose.service": "db",
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
def campaign(tmp_path, monkeypatch):
    monkeypatch.setattr(sup.releases, "verify", lambda _: {})
    monkeypatch.setattr(host, "host_sample", lambda _: copy.deepcopy(SAMPLE))
    items = []
    monkeypatch.setattr(host, "containers", lambda: copy.deepcopy(items))
    monkeypatch.setattr(host, "tagged_processes", lambda _: [])
    monkeypatch.setattr(host, "stop_processes", lambda _: [])
    monkeypatch.setattr(sup.time, "time", lambda: sup.STARTED + 100)
    monkeypatch.setattr(
        host,
        "proc_identity",
        lambda _: {
            "pid": 123,
            "start_ticks": "42",
            "uid": 1000,
            "cmd_sha256": "synthetic",
        },
    )
    monkeypatch.setattr(host, "identity_matches", lambda _: True)
    sup.initialize(tmp_path, RELEASE, now=sup.STARTED + 1)

    def stop_owned(_items, _registry):
        for c in items:
            c["State"].update(Status="exited", FinishedAt="intentional-stop")

    monkeypatch.setattr(host, "stop_containers", stop_owned)
    yield tmp_path, items


def stop_and_rearm(directory, items, retune=False):
    items.append(candidate())
    registry = sup.load_registry(directory)
    sup.stop_owned(directory, registry, ReceiptStore(directory), "planned_pause")
    diagnosis = directory / "diagnosis.json"
    diagnosis.write_text(
        '{"cause":"intentional_persistence_restart","safe_readback":true}'
    )
    allocation_file = None
    if retune:
        allocations = copy.deepcopy(epochs.INITIAL_ALLOCATIONS)
        allocations["db"] = {"memory": 3 * host.GIB // 4, "cpu": 0.2}
        allocation_file = directory / "retune.json"
        allocation_file.write_text(json.dumps(allocations))
    epoch = sup.rearm_epoch(
        directory, "persistence_restart", diagnosis, allocation_file
    )
    return registry, epoch


def guard(directory, epoch, items):
    registry = epochs.effective_registry(directory, sup.load_registry(directory))
    view = lifecycle.classify(
        directory, epoch, host.candidate_containers(items, registry), sup.STARTED + 100
    )
    return host.guard_reason(
        registry,
        items,
        SAMPLE["memory_available"],
        SAMPLE["disk_free"],
        None,
        sup.STARTED + 100,
        epoch["allocations"],
        view,
    )[0]


@pytest.mark.parametrize("retune", [False, True])
def test_proven_stop_rearm_controller_launch_up_and_retuned_caps(
    campaign, monkeypatch, retune
):
    directory, items = campaign
    registry, epoch = stop_and_rearm(directory, items, retune)
    assert epoch["dormant_containers"] == [lifecycle.dormant_projection(items[0])]
    assert guard(directory, epoch, items) is None
    assert sup.readback(directory)["lifecycle"]["containers"] == {"owned-db": "dormant"}
    calls = []
    monkeypatch.setattr(
        launch.subprocess, "Popen", lambda *a, **kw: SimpleNamespace(pid=123)
    )

    def gate(_fd, value):
        assert value == b"1"
        job = json.loads(next(directory.glob("job-" + "?" * 32 + ".json")).read_text())
        intent = lifecycle.read_record(directory, epoch, "db", "activation")
        assert intent["job_token"] == job["token"], (
            "admission precedes command execution"
        )
        items[0]["State"].update(Status="running", StartedAt="new-start", FinishedAt="")
        caps = epoch["allocations"]["db"]
        items[0]["HostConfig"].update(
            Memory=caps["memory"], NanoCpus=int(caps["cpu"] * 1e9)
        )
        lifecycle.complete(directory, job["token"])
        ReceiptStore(directory).write(
            f"job-{job['token']}.result.json", {"exit_code": 0}
        )
        calls.append("started")
        return 1

    monkeypatch.setattr(launch.os, "write", gate)

    def sample_interval(_seconds):
        if not calls:
            launch.launch(
                directory,
                "work",
                60,
                ["up", "-d", "--no-build", "--pull", "never", "db"],
            )
        else:
            assert guard(directory, epoch, items) is None
            assert (
                sup.readback(directory)["lifecycle"]["containers"]["owned-db"]
                == "active"
            )
            ReceiptStore(directory).write(
                "epoch-0002.pause-request.json", {"reason": "test_finished"}
            )

    monkeypatch.setattr(sup.time, "sleep", sample_interval)
    sup.run(directory)
    assert calls == ["started"]
    assert epochs.stopped_path(directory, epoch).exists()
    assert sup.load_registry(directory)["hard_deadline"] == registry["hard_deadline"]
    assert items[0]["State"]["Status"] == "exited"


def activate(directory, epoch, items):
    token = "b" * 32
    lifecycle.prepare(
        directory, epoch, items, ["db"], token, sup.STARTED + 160, sup.STARTED + 100
    )
    items[0]["State"].update(
        Status="running", StartedAt="activated-start", FinishedAt=""
    )
    lifecycle.complete(directory, token)
    return token


def test_unexpected_exit_before_first_monitor_sample_and_resume_is_fatal(campaign):
    directory, items = campaign
    _, epoch = stop_and_rearm(directory, items)
    token = "b" * 32
    lifecycle.prepare(
        directory, epoch, items, ["db"], token, sup.STARTED + 160, sup.STARTED + 100
    )
    items[0]["State"].update(
        Status="exited", StartedAt="started-then-crashed", FinishedAt="crash"
    )
    with pytest.raises(RuntimeError, match="candidate_service_exited"):
        lifecycle.complete(directory, token)
    assert (
        lifecycle.read_record(directory, epoch, "db", "started")["identity"]["started"]
        == "started-then-crashed"
    )
    assert guard(directory, epoch, items) == "candidate_service_exited"
    assert sup.readback(directory)["lifecycle"]["containers"]["owned-db"] == "active"
    assert guard(directory, epoch, items) == "candidate_service_exited"


def test_active_identity_change_or_disappearance_remains_fatal(campaign):
    directory, items = campaign
    _, epoch = stop_and_rearm(directory, items)
    activate(directory, epoch, items)
    assert guard(directory, epoch, items) is None
    items[0]["Id"] = "unannounced-replacement"
    assert guard(directory, epoch, items) == "candidate_identity_changed_without_rearm"
    items.clear()
    assert guard(directory, epoch, items) == "candidate_active_identity_missing"


def test_dormant_resurrection_without_authorized_startup_is_fatal(campaign):
    directory, items = campaign
    _, epoch = stop_and_rearm(directory, items)
    items[0]["State"].update(Status="running", StartedAt="unauthorized-start")
    assert guard(directory, epoch, items) == "candidate_startup_not_admitted"


def test_rearm_rejects_unproven_or_changed_stopped_identity(campaign):
    directory, items = campaign
    items.append(candidate())
    sup.stop_owned(
        directory, sup.load_registry(directory), ReceiptStore(directory), "pause"
    )
    items[0]["Image"] = "changed-after-stop"
    diagnosis = directory / "diagnosis.json"
    diagnosis.write_text('{"cause":"test"}')
    with pytest.raises(RuntimeError, match="not_proven"):
        sup.rearm_epoch(directory, "changed", diagnosis)


def test_pending_startup_does_not_allow_indefinite_dormancy(campaign):
    directory, items = campaign
    _, epoch = stop_and_rearm(directory, items)
    lifecycle.prepare(
        directory, epoch, items, ["db"], "b" * 32, sup.STARTED + 160, sup.STARTED + 100
    )
    view = lifecycle.classify(directory, epoch, items, sup.STARTED + 161)
    assert view["reason"] == "candidate_startup_not_observed"
