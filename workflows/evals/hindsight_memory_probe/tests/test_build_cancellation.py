"""Offline observer mechanics; synthetic process views never qualify OCI execution."""

import copy
from pathlib import Path

import pytest

from workflows.evals.hindsight_memory_probe import (
    build_cancellation as probe,
    epochs,
    host_guard as host,
    supervisor as sup,
)
from workflows.evals.hindsight_memory_probe.receipts import ReceiptStore

RELEASE = Path("/mnt/projects/apps/ade-hindsight-probe/releases/" + "a" * 40)


@pytest.fixture
def registered(tmp_path, monkeypatch):
    monkeypatch.setattr(sup.releases, "verify", lambda _: {})
    monkeypatch.setattr(
        host,
        "host_sample",
        lambda _: {
            "memory_available": 10 * host.GIB,
            "cpus": 2,
            "disk_free": 30 * host.GIB,
        },
    )
    monkeypatch.setattr(host, "containers", lambda: [])
    sup.initialize(tmp_path, RELEASE, now=sup.STARTED + 1)
    registry = sup.load_registry(tmp_path)
    epoch = epochs.active(tmp_path, registry)
    token = "a" * 32
    ReceiptStore(tmp_path).write(
        f"job-{token}.json",
        {
            "kind": "build-cancel",
            "identity": {"pid": 123},
            "build_sentinel": token,
            "token": token,
            "deadline": sup.STARTED + 20,
            "epoch_sha256": epoch["sha256"],
        },
    )
    return tmp_path, epoch, token


def clock(monkeypatch):
    value = [sup.STARTED + 18]
    monkeypatch.setattr(probe.time, "time", lambda: value[0])
    monkeypatch.setattr(
        probe.time, "sleep", lambda duration: value.__setitem__(0, value[0] + duration)
    )
    return value


def test_actual_observer_requires_positive_run_then_deadline_stop_and_absence(
    registered, monkeypatch
):
    directory, epoch, token = registered
    now = clock(monkeypatch)
    identity = {"pid": 987, "uid": 0, "start_ticks": "42", "cmd_sha256": "synthetic"}
    monkeypatch.setattr(
        probe,
        "sentinel_processes",
        lambda _: [copy.deepcopy(identity)] if now[0] < sup.STARTED + 20 else [],
    )
    monkeypatch.setattr(
        host,
        "tagged_processes",
        lambda _: [identity] if now[0] < sup.STARTED + 20 else [],
    )
    ReceiptStore(directory).write(
        epochs.stopped_path(directory, epoch).name,
        {
            "reason": "owned_process_deadline_elapsed",
            "time": sup.STARTED + 20,
            "epoch_sha256": epoch["sha256"],
        },
    )
    result = probe.observe(directory, 123)
    assert result["observed_sentinel"] == [identity]
    assert (
        result["no_sentinel_samples"] == 3 and result["outcome"] == "daemon_cancelled"
    )
    assert (
        len(result["samples"]) >= 5
        and result["registered_deadline"] == sup.STARTED + 20
    )
    assert (directory / f"build-cancel-{token}.seen.json").is_file()


@pytest.mark.parametrize("failure", ["never_seen", "daemon_survives", "operator_stop"])
def test_client_exit_alone_never_qualifies_daemon_cancellation(
    registered, monkeypatch, failure
):
    directory, epoch, token = registered
    now = clock(monkeypatch)
    identity = {"pid": 987, "uid": 0, "start_ticks": "42", "cmd_sha256": "synthetic"}
    monkeypatch.setattr(
        probe,
        "sentinel_processes",
        lambda _: (
            []
            if failure == "never_seen"
            else [identity]
            if failure == "daemon_survives" or now[0] < sup.STARTED + 20
            else []
        ),
    )
    monkeypatch.setattr(
        host,
        "tagged_processes",
        lambda _: [] if now[0] >= sup.STARTED + 20 else [identity],
    )
    ReceiptStore(directory).write(
        epochs.stopped_path(directory, epoch).name,
        {
            "reason": "operator_stop"
            if failure == "operator_stop"
            else "owned_process_deadline_elapsed",
            "time": sup.STARTED + 20,
            "epoch_sha256": epoch["sha256"],
        },
    )
    with pytest.raises(RuntimeError, match="not_qualified|not_observed"):
        probe.observe(directory, 123)
    assert not (directory / f"build-cancel-{token}.proof.json").exists()


def test_host_sentinel_scan_matches_actual_standalone_argv_not_docker_arguments(
    tmp_path, monkeypatch
):
    token = "a" * 32
    for pid, argv in [
        (123, ["docker", "build", f"PROBE_CANCELLATION_TOKEN={token}"]),
        (987, ["python3", "-u", "/probe-cancellation.py", probe.SENTINEL, token]),
    ]:
        path = tmp_path / str(pid)
        path.mkdir()
        (path / "cmdline").write_bytes(b"\0".join(x.encode() for x in argv) + b"\0")
    monkeypatch.setattr(
        host,
        "proc_identity",
        lambda pid, *_: {"pid": pid, "start_ticks": "42", "uid": 0},
    )
    assert probe.sentinel_processes(token, tmp_path) == [
        {"pid": 987, "start_ticks": "42", "uid": 0}
    ]
