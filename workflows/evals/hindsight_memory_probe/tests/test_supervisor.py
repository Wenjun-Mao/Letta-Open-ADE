import copy
import json
import os
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
        1791749563,
        1791767563,
        1791771163,
    )
    assert value["clock"]["activation_id"] == "hindsight-semantic-follow-up-2026-10-11"
    value["hard_deadline"] += 1
    value["registry_sha256"] = sup.digest_registry(value)
    (directory / "registry.json").write_text(json.dumps(value))
    with pytest.raises(RuntimeError, match="immutable"):
        sup.load_registry(directory)


def test_revision_four_registry_is_not_adopted_or_renewed(tmp_path, registry):
    directory, current = registry
    old = copy.deepcopy(current)
    old.update({
        "started": 1791694165,
        "target": 1791730165,
        "hard_deadline": 1791737365,
        "created": 1791694166,
    })
    old.pop("clock", None)
    old["registry_sha256"] = sup.digest_registry(old)
    (directory / "registry.json").write_text(json.dumps(old))
    with pytest.raises(RuntimeError, match="immutable"):
        sup.load_registry(directory)


def test_registry_clock_binding_cannot_be_extended_with_new_digest(registry):
    directory, value = registry
    value["clock"]["work_cutoff"] += 3600
    value["registry_sha256"] = sup.digest_registry(value)
    (directory / "registry.json").write_text(json.dumps(value))
    with pytest.raises(RuntimeError, match="immutable"):
        sup.load_registry(directory)


def test_expired_init_cannot_start(tmp_path):
    with pytest.raises(RuntimeError, match="elapsed"):
        sup.initialize(tmp_path, RELEASE, now=sup.DEADLINE)


def test_campaign_cannot_start_before_approved_activation(tmp_path):
    with pytest.raises(RuntimeError, match="not_activated"):
        sup.initialize(tmp_path, RELEASE, now=sup.STARTED - 1)


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




















def write_proc(root, pid, token, start="42", command=b"owned\0"):
    directory = root / str(pid)
    directory.mkdir(exist_ok=True)
    fields = ["S", "1", *["0"] * 17, start, "0"]
    (directory / "stat").write_text(f"{pid} (space in name) " + " ".join(fields))
    (directory / "cmdline").write_bytes(command)
    (directory / "environ").write_bytes(
        ("ADE_PROBE_PROCESS_OWNER=" + token).encode() + b"\0"
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
        epochs.stopped_path(directory, epoch).name,
        {"reason": "dummy_job_deadline", "epoch_sha256": epoch["sha256"]},
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
        epochs.stopped_path(directory, epoch).name,
        {"reason": "pause", "epoch_sha256": epoch["sha256"]},
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
        epochs.stopped_path(directory, new).name,
        {"reason": "pause", "epoch_sha256": new["sha256"]},
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
        epochs.stopped_path(directory, previous).name,
        {"reason": "repair", "epoch_sha256": previous["sha256"]},
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






def test_job_registration_selection_excludes_terminal_result_receipts(tmp_path):
    store = ReceiptStore(tmp_path)
    token = "a" * 32
    job = {"token": token, "identity": {"pid": 1}}
    store.write(f"job-{token}.json", job)
    store.write(f"job-{token}.result.json", {"exit_code": 0})
    assert sup.jobs(tmp_path) == [job]
