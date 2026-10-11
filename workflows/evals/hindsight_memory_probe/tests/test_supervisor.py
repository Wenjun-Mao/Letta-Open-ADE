import copy
import json
import os
import signal
from pathlib import Path

import pytest

from workflows.evals.hindsight_memory_probe import (
    epochs,
    host_guard as host,
    supervisor as sup,
)
from workflows.evals.hindsight_memory_probe.receipts import ReceiptStore

RELEASE = Path("/mnt/projects/apps/ade-hindsight-probe/releases/" + "a" * 40)
SAFE_SAMPLE = {"memory_available": 10 * host.GIB, "cpus": 2, "disk_free": 30 * host.GIB}


def container(
    identifier="existing", project="baseline", service="db", status="running"
):
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


def test_absolute_campaign_clock_and_registry_conflicts(registry):
    directory, value = registry
    assert (value["started"], value["target"], value["hard_deadline"]) == (
        1791694165,
        1791730165,
        1791737365,
    )
    value["hard_deadline"] += 1
    value["registry_sha256"] = sup.digest_registry(value)
    (directory / "registry.json").write_text(json.dumps(value))
    with pytest.raises(RuntimeError, match="immutable"):
        sup.load_registry(directory)


def test_expired_init_cannot_start(tmp_path):
    with pytest.raises(RuntimeError, match="elapsed"):
        sup.initialize(tmp_path, RELEASE, now=sup.DEADLINE)


def test_duplicate_lease_is_rejected(tmp_path):
    with sup.lease(tmp_path):
        with pytest.raises(BlockingIOError):
            with sup.lease(tmp_path):
                pass


def test_existing_registry_is_not_reinitialized(registry):
    directory, _ = registry
    with pytest.raises(RuntimeError, match="already_exists"):
        sup.initialize(directory, RELEASE, now=sup.STARTED + 2)


@pytest.mark.parametrize(
    "sample",
    [
        {"memory_available": 9 * host.GIB, "cpus": 2, "disk_free": 30 * host.GIB},
        {"memory_available": 10 * host.GIB, "cpus": 1, "disk_free": 30 * host.GIB},
        {"memory_available": 10 * host.GIB, "cpus": 2, "disk_free": 24 * host.GIB},
    ],
)
def test_preflight_headroom_is_prospective(tmp_path, monkeypatch, sample):
    monkeypatch.setattr(sup.releases, "verify", lambda _: {})
    monkeypatch.setattr(host, "host_sample", lambda _: sample)
    with pytest.raises(RuntimeError, match="insufficient"):
        sup.initialize(tmp_path, RELEASE, now=sup.STARTED + 1)


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


def write_proc(root, pid, token, start="42", command=b"owned\0"):
    directory = root / str(pid)
    directory.mkdir(exist_ok=True)
    fields = ["S", "1", *["0"] * 17, start, "0"]
    (directory / "stat").write_text(f"{pid} (space in name) " + " ".join(fields))
    (directory / "cmdline").write_bytes(command)
    (directory / "environ").write_bytes(
        ("ADE_PROBE_PROCESS_OWNER=" + token).encode() + b"\0"
    )


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


def test_rearm_requires_diagnosis_and_stopped_epoch(registry, monkeypatch):
    directory, value = registry
    monkeypatch.setattr(sup.time, "time", lambda: sup.STARTED + 100)
    epoch = epochs.active(directory, value)
    diagnosis = directory / "diagnosis.json"
    diagnosis.write_text('{"cause":"dummy_deadline","verified_safe":true}')
    with pytest.raises(RuntimeError, match="stopped"):
        sup.rearm_epoch(directory, "dummy_complete", diagnosis)
    ReceiptStore(directory).write(
        epochs.stopped_path(directory, epoch).name, {"reason": "dummy_job_deadline"}
    )
    next_epoch = sup.rearm_epoch(directory, "dummy_complete", diagnosis)
    assert next_epoch["index"] == 2 and next_epoch["previous_sha256"] == epoch["sha256"]
    assert sup.load_registry(directory)["hard_deadline"] == sup.DEADLINE
    assert (
        next_epoch["diagnosis_sha256"]
        and epochs.stopped_path(directory, epoch).exists()
    )


def test_rearm_allocation_is_audited_and_deadline_never_extended(registry, monkeypatch):
    directory, value = registry
    epoch = epochs.active(directory, value)
    ReceiptStore(directory).write(
        epochs.stopped_path(directory, epoch).name, {"reason": "pause"}
    )
    diagnosis = directory / "diagnosis.json"
    diagnosis.write_text('{"cause":"measured_retune"}')
    allocations = copy.deepcopy(epoch["allocations"])
    allocations["hindsight"]["memory"] = 5 * host.GIB
    changed = directory / "allocations.json"
    changed.write_text(json.dumps(allocations))
    monkeypatch.setattr(sup.time, "time", lambda: sup.STARTED + 200)
    new = sup.rearm_epoch(directory, "measured_retune", diagnosis, changed)
    assert new["allocations"]["hindsight"]["memory"] == 5 * host.GIB
    ReceiptStore(directory).write(
        epochs.stopped_path(directory, new).name, {"reason": "pause"}
    )
    monkeypatch.setattr(sup.time, "time", lambda: sup.WORK_CUTOFF)
    with pytest.raises(RuntimeError, match="cannot_rearm"):
        sup.rearm_epoch(directory, "late_restart", diagnosis)


def test_conflicting_epoch_chain_cannot_resume(registry):
    directory, value = registry
    path = directory / "epoch-0001.json"
    epoch = json.loads(path.read_text())
    epoch["allocations"]["db"]["memory"] += 1
    path.write_text(json.dumps(epoch))
    with pytest.raises(RuntimeError, match="chain_conflict"):
        epochs.active(directory, value)


def test_running_guard_stops_before_hard_cap_with_margin(registry, monkeypatch):
    directory, value = registry
    times = iter([sup.STARTED + 1, sup.WORK_CUTOFF])
    monkeypatch.setattr(sup.time, "time", lambda: next(times, sup.WORK_CUTOFF))
    monkeypatch.setattr(
        host,
        "proc_identity",
        lambda _: {
            "pid": 101,
            "start_ticks": "42",
            "uid": os.getuid(),
            "cmd_sha256": "x",
        },
    )
    stopped = []
    monkeypatch.setattr(sup, "stop_owned", lambda *args: stopped.append(args[-1]))
    sup.run(directory)
    assert stopped == ["hard_deadline_elapsed"]
    assert sup.WORK_CUTOFF <= sup.DEADLINE - 180


def test_loss_of_controller_resume_requires_readback_and_keeps_clock(
    registry, monkeypatch
):
    directory, value = registry
    epoch = epochs.active(directory, value)
    ReceiptStore(directory).write(
        "previous.controller.json", {"identity": {}, "epoch_sha256": epoch["sha256"]}
    )
    monkeypatch.setattr(sup.time, "time", lambda: sup.STARTED + 2)
    with pytest.raises(RuntimeError, match="resume_requires"):
        sup.run(directory)
    monkeypatch.setattr(
        host,
        "proc_identity",
        lambda _: {
            "pid": 101,
            "start_ticks": "42",
            "uid": os.getuid(),
            "cmd_sha256": "x",
        },
    )
    ReceiptStore(directory).write(
        "epoch-0001.pause-request.json", {"reason": "test_pause"}
    )
    monkeypatch.setattr(sup, "stop_owned", lambda *_: None)
    sup.run(directory, resume=True)
    events = [json.loads(p.read_text()) for p in directory.glob("*.event.json")]
    assert any(e["event"] == "resume_readback" for e in events)
    assert sup.load_registry(directory)["hard_deadline"] == value["hard_deadline"]


def test_diagnosed_new_clean_release_keeps_old_owned_containers_allowlisted(
    registry, monkeypatch
):
    directory, value = registry
    previous = epochs.active(directory, value)
    ReceiptStore(directory).write(
        epochs.stopped_path(directory, previous).name, {"reason": "repair"}
    )
    diagnosis = directory / "repair.json"
    diagnosis.write_text('{"cause":"qualified_code_repair"}')
    monkeypatch.setattr(sup.time, "time", lambda: sup.STARTED + 100)
    new_release = RELEASE.parent / ("b" * 40)
    next_epoch = sup.rearm_epoch(
        directory, "code_repair", diagnosis, release=new_release
    )
    assert next_epoch["release"] == str(new_release)
    effective = epochs.effective_registry(directory, value)
    assert effective["authorized_releases"] == [str(RELEASE), str(new_release)]
    old_container = container("old-owned", host.PROJECT)
    new_container = copy.deepcopy(old_container)
    labels = new_container["Config"]["Labels"]
    labels["com.docker.compose.project.working_dir"] = str(
        new_release / "workflows/evals/hindsight_memory_probe"
    )
    labels["com.docker.compose.project.config_files"] = str(
        new_release / "workflows/evals/hindsight_memory_probe/compose.yaml"
    )
    assert host.owned(old_container, effective) and host.owned(new_container, effective)
    assert value["release"] == str(RELEASE) and value["hard_deadline"] == sup.DEADLINE
    with pytest.raises(RuntimeError, match="path_required"):
        sup.releases.validate_path(Path("/mnt/unowned/" + "c" * 40))


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


def test_job_registration_selection_excludes_terminal_result_receipts(tmp_path):
    store = ReceiptStore(tmp_path)
    token = "a" * 32
    job = {"token": token, "identity": {"pid": 1}}
    store.write(f"job-{token}.json", job)
    store.write(f"job-{token}.result.json", {"exit_code": 0})
    assert sup.jobs(tmp_path) == [job]


def test_shutdown_requires_stopped_readback_not_stop_command_acceptance(registry):
    _, value = registry
    with pytest.raises(RuntimeError, match="shutdown_container"):
        host.ensure_stopped([container("owned", host.PROJECT)], value, [])
    host.ensure_stopped([container("owned", host.PROJECT, status="exited")], value, [])
