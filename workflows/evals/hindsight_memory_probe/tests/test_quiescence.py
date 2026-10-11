import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from workflows.evals.hindsight_memory_probe import (
    epochs,
    host_guard as host,
    launch,
    lifecycle,
    quiescence,
    supervisor as sup,
)
from workflows.evals.hindsight_memory_probe.receipts import ReceiptStore

RELEASE = Path("/mnt/projects/apps/ade-hindsight-probe/releases/" + "a" * 40)


@pytest.fixture
def state(tmp_path, monkeypatch):
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
    monkeypatch.setattr(host, "tagged_processes", lambda _: [])
    monkeypatch.setattr(host, "identity_matches", lambda _: True)
    monkeypatch.setattr(
        host,
        "proc_identity",
        lambda _: {"pid": 123, "uid": 1000, "start_ticks": "42", "cmd_sha256": "test"},
    )
    monkeypatch.setattr(sup.time, "time", lambda: sup.STARTED + 10)
    sup.initialize(tmp_path, RELEASE, now=sup.STARTED + 1)
    registry = sup.load_registry(tmp_path)
    epoch = epochs.active(tmp_path, registry)
    ReceiptStore(tmp_path).write(
        "one.controller.json",
        {
            "identity": {},
            "registry_sha256": registry["registry_sha256"],
            "epoch_sha256": epoch["sha256"],
        },
    )
    return tmp_path, registry, epoch


def test_contended_registration_stop_publishes_barrier_then_completes_cleanup(
    state, monkeypatch
):
    directory, registry, epoch = state
    failures, stopped, spawned = [], [], []
    monkeypatch.setattr(host, "stop_containers", lambda *_: stopped.append(True))
    monkeypatch.setattr(
        launch.subprocess, "Popen", lambda *_a, **_kw: spawned.append(True)
    )

    def stopper():
        try:
            sup.stop_owned(
                directory, registry, ReceiptStore(directory), "safety_failure"
            )
        except Exception as exc:
            failures.append(exc)

    with sup.lease(directory):
        with sup.lease(directory, "jobs.lock"):
            thread = threading.Thread(target=stopper)
            thread.start()
            until = time.monotonic() + 2
            while (
                not quiescence.stop_path(directory, epoch).exists()
                and time.monotonic() < until
            ):
                time.sleep(0.01)
            assert quiescence.stop_path(directory, epoch).exists(), (
                "stop admission precedes waiting for registration"
            )
            assert not stopped
            with pytest.raises(BlockingIOError):
                launch.launch(directory, "dummy", 60, [])
        thread.join(timeout=2)
    assert (
        not thread.is_alive() and not failures and stopped == [True] and spawned == []
    )
    assert epochs.stopped_path(directory, epoch).exists()


def test_stop_arriving_during_registration_denies_final_execution_handshake(
    state, monkeypatch
):
    directory, registry, epoch = state
    monkeypatch.setattr(
        launch.subprocess, "Popen", lambda *_a, **_kw: SimpleNamespace(pid=123)
    )
    gates = []
    monkeypatch.setattr(launch.os, "write", lambda *_: gates.append(True))
    prepare = lifecycle.prepare

    def stop_after_registration(*args):
        prepare(*args)
        quiescence.admit_stop(directory, epoch, "test_safety_stop")

    monkeypatch.setattr(lifecycle, "prepare", stop_after_registration)
    with sup.lease(directory), pytest.raises(RuntimeError, match="stopping"):
        launch.launch(directory, "dummy", 60, [])
    assert not gates
    assert list(directory.glob("job-" + "?" * 32 + ".json")), (
        "registered gated child never dispatched"
    )


def test_deadline_rechecked_at_execution_handshake(state, monkeypatch):
    directory, _, _ = state
    monkeypatch.setattr(
        launch.subprocess, "Popen", lambda *_a, **_kw: SimpleNamespace(pid=123)
    )
    gates = []
    monkeypatch.setattr(launch.os, "write", lambda *_: gates.append(True))
    monkeypatch.setattr(
        lifecycle,
        "prepare",
        lambda *_: monkeypatch.setattr(sup.time, "time", lambda: sup.WORK_CUTOFF),
    )
    with sup.lease(directory), pytest.raises(RuntimeError, match="deadline"):
        launch.launch(directory, "dummy", 60, [])
    assert not gates


def test_registration_lock_timeout_does_not_skip_owned_cleanup(state, monkeypatch):
    directory, registry, epoch = state
    calls, stopped_jobs = [], []
    monkeypatch.setattr(host, "stop_containers", lambda *_: calls.append("owned-stop"))
    monkeypatch.setattr(
        host, "stop_processes", lambda job: stopped_jobs.append(job["token"])
    )
    original = quiescence.bounded_lease

    def short_bound(directory, name, seconds, required=True):
        return original(
            directory, name, 0.02 if name == "jobs.lock" else seconds, required
        )

    monkeypatch.setattr(quiescence, "bounded_lease", short_bound)
    with sup.lease(directory, "jobs.lock"):
        with pytest.raises(RuntimeError, match="registration_quiescence_unproven"):
            sup.stop_owned(directory, registry, ReceiptStore(directory), "safety_stop")
        assert calls == ["owned-stop"]
        assert not epochs.stopped_path(directory, epoch).exists()
        unproven = json.loads(
            next(directory.glob("*.quiescence-unproven.json")).read_text()
        )
        assert unproven["reason"] == "registration_quiescence_unproven"
        # A still-registering gated child can publish after the stop's process snapshot.
        ReceiptStore(directory).write(
            "job-" + "b" * 32 + ".json",
            {"token": "b" * 32, "identity": {"pid": 123}, "deadline": sup.STARTED + 60},
        )
        with pytest.raises(RuntimeError, match="stopping"):
            with quiescence.dispatch_admission(directory, registry, epoch):
                pytest.fail("late gated child must never dispatch")
    assert not epochs.stopped_path(directory, epoch).exists()
    diagnosis = directory / "diagnosis.json"
    diagnosis.write_text('{"cause":"registration_timeout"}')
    with pytest.raises(RuntimeError, match="requires_stopped_epoch"):
        sup.rearm_epoch(directory, "registration_timeout", diagnosis)
    # A later exclusive registration lease and fresh process/container readback can prove stop.
    sup.stop_owned(directory, registry, ReceiptStore(directory), "safety_stop_retry")
    assert calls == ["owned-stop", "owned-stop"]
    assert stopped_jobs == ["b" * 32], (
        "fresh exclusive cleanup includes the late registration"
    )
    assert epochs.stopped_path(directory, epoch).exists()


def test_receipt_publication_never_exposes_partial_registration_json(
    tmp_path, monkeypatch
):
    store = ReceiptStore(tmp_path)
    original = __import__("os").link
    checked = []

    def publish(source, destination):
        assert not Path(destination).exists()
        assert json.loads(Path(source).read_text()) == {"complete": True}
        checked.append(True)
        original(source, destination)

    monkeypatch.setattr(
        "workflows.evals.hindsight_memory_probe.receipts.os.link", publish
    )
    store.write("job-" + "a" * 32 + ".json", {"complete": True})
    assert checked == [True] and not list(tmp_path.glob(".*.partial"))
