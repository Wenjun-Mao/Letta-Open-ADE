"""Real lifecycle functions with synthetic Docker/process I/O; no OCI qualification claims."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from workflows.evals.hindsight_memory_probe import (
    epochs,
    guard_evidence,
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


def stop_and_rearm(directory, items, retune=False, release=None, prior_unhealthy=False):
    item = candidate()
    if prior_unhealthy:
        item["State"]["Health"] = {"Status": "unhealthy"}
    items.append(item)
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
        directory, "persistence_restart", diagnosis, allocation_file, release
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


def test_stopped_prior_release_removal_is_bounded_by_replacement_intent(campaign):
    directory, items = campaign
    next_release = Path("/mnt/projects/apps/ade-hindsight-probe/releases/" + "b" * 40)
    _, epoch = stop_and_rearm(
        directory, items, retune=True, release=next_release, prior_unhealthy=True
    )
    lifecycle.prepare(
        directory,
        epoch,
        items,
        ["db"],
        "b" * 32,
        sup.STARTED + 160,
        sup.STARTED + 100,
    )
    items[0]["State"]["Status"] = "removing"

    view = lifecycle.classify(directory, epoch, items, sup.STARTED + 101)
    assert view == {
        "containers": {"owned-db": "replacement_pending"},
        "reason": None,
    }
    assert guard(directory, epoch, items) is None

    replacement = candidate("new-db", status="created")
    replacement["State"]["StartedAt"] = "0001-01-01T00:00:00Z"
    replacement["Config"]["Labels"][
        "com.docker.compose.project.working_dir"
    ] = str(next_release / "workflows/evals/hindsight_memory_probe")
    replacement["Config"]["Labels"][
        "com.docker.compose.project.config_files"
    ] = str(next_release / "workflows/evals/hindsight_memory_probe/compose.yaml")
    replacement["HostConfig"].update(
        Memory=epoch["allocations"]["db"]["memory"],
        NanoCpus=int(epoch["allocations"]["db"]["cpu"] * 1e9),
    )
    items.append(replacement)
    view = lifecycle.classify(directory, epoch, items, sup.STARTED + 102)
    assert view == {
        "containers": {
            "owned-db": "replacement_pending",
            "new-db": "startup_pending",
        },
        "reason": None,
    }
    replacement["State"].update(
        Status="running", StartedAt="replacement-start", FinishedAt=""
    )
    lifecycle.write_record(
        directory,
        epoch,
        "db",
        "started",
        {
            "identity": lifecycle.identity(replacement),
            "job_token": "b" * 32,
            "observed_time": sup.STARTED + 103,
        },
    )
    view = lifecycle.classify(directory, epoch, items, sup.STARTED + 161)
    assert view["reason"] == "candidate_predecessor_removal_not_observed"
    items.remove(items[0])
    lifecycle.complete(directory, "b" * 32)
    items.remove(replacement)
    view = lifecycle.classify(directory, epoch, items, sup.STARTED + 103)
    assert view["reason"] == "candidate_active_identity_missing"


def test_prior_release_removal_without_matching_intent_fails_closed(campaign):
    directory, items = campaign
    next_release = Path("/mnt/projects/apps/ade-hindsight-probe/releases/" + "b" * 40)
    _, epoch = stop_and_rearm(directory, items, release=next_release)
    items[0]["State"]["Status"] = "removing"

    view = lifecycle.classify(directory, epoch, items, sup.STARTED + 100)
    assert view["reason"] == "candidate_startup_not_admitted"


@pytest.mark.parametrize(
    "changed_field",
    [
        "id",
        "image",
        "started",
        "finished",
        "restarts",
        "oom_killed",
        "health",
        "memory",
        "nano_cpus",
        "service",
        "release_directory",
    ],
)
def test_unproven_removing_identity_fails_closed_during_replacement(
    campaign, changed_field
):
    directory, items = campaign
    next_release = Path("/mnt/projects/apps/ade-hindsight-probe/releases/" + "b" * 40)
    _, epoch = stop_and_rearm(directory, items, release=next_release)
    lifecycle.prepare(
        directory,
        epoch,
        items,
        ["db"],
        "b" * 32,
        sup.STARTED + 160,
        sup.STARTED + 100,
    )
    items[0]["State"]["Status"] = "removing"
    candidate_item = items[0]
    if changed_field == "id":
        candidate_item["Id"] = "unknown-container"
    elif changed_field == "image":
        candidate_item["Image"] = "sha256:changed-after-stop"
    elif changed_field == "started":
        candidate_item["State"]["StartedAt"] = "unrecorded-start"
    elif changed_field == "finished":
        candidate_item["State"]["FinishedAt"] = "unrecorded-finish"
    elif changed_field == "restarts":
        candidate_item["RestartCount"] += 1
    elif changed_field == "oom_killed":
        candidate_item["State"]["OOMKilled"] = True
    elif changed_field == "health":
        candidate_item["State"]["Health"] = {"Status": "unhealthy"}
    elif changed_field == "memory":
        candidate_item["HostConfig"]["Memory"] += 1
    elif changed_field == "nano_cpus":
        candidate_item["HostConfig"]["NanoCpus"] += 1
    elif changed_field == "service":
        candidate_item["Config"]["Labels"]["com.docker.compose.service"] = "model-router"
    elif changed_field == "release_directory":
        candidate_item["Config"]["Labels"][
            "com.docker.compose.project.working_dir"
        ] = "/unadmitted/release/workflows/evals/hindsight_memory_probe"

    view = lifecycle.classify(directory, epoch, items, sup.STARTED + 101)
    assert view["reason"] == "candidate_startup_not_admitted"


def test_removing_predecessor_does_not_extend_startup_deadline(campaign):
    directory, items = campaign
    next_release = Path("/mnt/projects/apps/ade-hindsight-probe/releases/" + "b" * 40)
    _, epoch = stop_and_rearm(directory, items, release=next_release)
    deadline = sup.STARTED + 160
    lifecycle.prepare(
        directory, epoch, items, ["db"], "b" * 32, deadline, sup.STARTED + 100
    )
    items[0]["State"]["Status"] = "removing"

    view = lifecycle.classify(directory, epoch, items, deadline + 1)
    assert view["reason"] == "candidate_predecessor_removal_not_observed"


def test_current_observation_cannot_pair_stale_docker_items_with_new_receipts(campaign):
    directory, items = campaign
    next_release = Path("/mnt/projects/apps/ade-hindsight-probe/releases/" + "b" * 40)
    _, epoch = stop_and_rearm(directory, items, release=next_release)
    token = "b" * 32
    lifecycle.prepare(
        directory, epoch, items, ["db"], token, sup.STARTED + 160, sup.STARTED + 100
    )
    stale_items = copy.deepcopy(items)
    items.clear()
    replacement = candidate("new-db", status="running")
    replacement["State"].update(
        StartedAt="replacement-start", FinishedAt=""
    )
    replacement["Config"]["Labels"][
        "com.docker.compose.project.working_dir"
    ] = str(next_release / "workflows/evals/hindsight_memory_probe")
    replacement["Config"]["Labels"][
        "com.docker.compose.project.config_files"
    ] = str(next_release / "workflows/evals/hindsight_memory_probe/compose.yaml")
    items.append(replacement)
    lifecycle.complete(directory, token)

    stale = lifecycle.observe(
        directory,
        epoch,
        host.candidate_containers(
            stale_items, epochs.effective_registry(directory, sup.load_registry(directory))
        ),
        sup.STARTED + 101,
    )
    assert stale["view"]["reason"] == "candidate_active_identity_missing"

    current = lifecycle.observe_current(
        directory,
        epoch,
        epochs.effective_registry(directory, sup.load_registry(directory)),
        sup.STARTED + 101,
    )
    assert current["items"] == items
    assert current["view"] == {"containers": {"new-db": "active"}, "reason": None}


def test_guard_failure_receipt_is_redacted_exact_and_immutable(campaign):
    directory, items = campaign
    _, epoch = stop_and_rearm(directory, items)
    lifecycle.prepare(
        directory, epoch, items, ["db"], "b" * 32, sup.STARTED + 160, sup.STARTED + 100
    )
    items[0]["Config"]["Env"] = ["TOKEN=private-value"]
    candidates = host.candidate_containers(
        items, epochs.effective_registry(directory, sup.load_registry(directory))
    )
    observation = lifecycle.observe(directory, epoch, candidates, sup.STARTED + 101)
    assert observation["admissions"]["db"]["job_token"] == "b" * 32
    assert guard_evidence.publish(
        directory,
        sup.load_registry(directory),
        epoch,
        candidates,
        observation,
        "candidate_startup_not_admitted",
        sup.STARTED + 101,
    )

    path = directory / "epoch-0002-guard-failure.json"
    before = path.read_text()
    assert "private-value" not in before
    assert '"Env"' not in before
    evidence = json.loads(before)
    assert evidence["lifecycle"] == observation["view"]
    assert evidence["guard_reason"] == "candidate_startup_not_admitted"
    assert evidence["candidates"][0]["dormant"] == lifecycle.dormant_projection(
        candidates[0]
    )
    assert not guard_evidence.publish(
        directory,
        sup.load_registry(directory),
        epoch,
        candidates,
        observation,
        "replacement_reason_must_not_overwrite",
        sup.STARTED + 102,
    )
    assert path.read_text() == before


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
