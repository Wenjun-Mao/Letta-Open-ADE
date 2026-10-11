"""Offline contracts for ordered P4 finalization and archive publication."""

import hashlib
import json

import pytest

from workflows.evals.hindsight_memory_probe import (
    candidate_database,
    finalization,
)
from workflows.evals.hindsight_memory_probe.receipts import ReceiptStore


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def test_finalization_failure_receipts_use_only_fixed_safe_diagnostic_codes():
    assert finalization.failure_code(RuntimeError("finalization_process_identity_changed")) == (
        "finalization_process_identity_changed")
    assert finalization.failure_code(RuntimeError("finalization_safety_candidate_unhealthy")) == (
        "finalization_safety_candidate_unhealthy")
    assert finalization.failure_code(RuntimeError("private text or argv")) == "finalization_stage_failed"
    assert finalization.failure_code(RuntimeError(["not", "a", "code"])) == "finalization_stage_failed"


def test_monitor_accepts_health_only_after_exact_clean_planned_stop(tmp_path, monkeypatch):
    from workflows.evals.hindsight_memory_probe import host_guard as host

    token = "0" * 32
    epoch = {
        "index": 1, "sha256": "epoch", "release": "/release",
        "allocations": {"db": {"memory": 100, "cpu": 1e-7}},
    }
    registry = {"registry_sha256": "registry", "release": "/release", "baseline": []}
    admitted = {
        "token": token, "containers": [], "jobs": [], "deadline": 200,
    }
    item = {
        "Id": "db-id", "Image": "image-id", "RestartCount": 0,
        "State": {
            "StartedAt": "started", "Status": "exited", "ExitCode": 0,
            "FinishedAt": "finished", "OOMKilled": False,
            "Health": {"Status": "unhealthy", "FailingStreak": 0, "Log": []},
        },
        "HostConfig": {"Memory": 100, "NanoCpus": 100},
        "Config": {"Labels": {
            "com.docker.compose.project": host.PROJECT,
            "com.docker.compose.service": "db",
            "com.docker.compose.project.working_dir": "/release/workflows/evals/hindsight_memory_probe",
            "com.docker.compose.project.config_files": "/release/workflows/evals/hindsight_memory_probe/compose.yaml",
        }},
    }
    admitted["containers"] = [finalization.identity_projection({
        **item, "State": {**item["State"], "Status": "running"}
    })]
    (tmp_path / "epoch-0001.finalize-admission.json").write_text(json.dumps(admitted))
    monkeypatch.setattr(finalization, "planned_ids", lambda *_: {"db-id"})
    monkeypatch.setattr(finalization, "jobs", lambda *_: [])
    monkeypatch.setattr(host, "containers", lambda: [item])
    monkeypatch.setattr(host, "host_sample", lambda *_: {
        "memory_available": 10 * host.GIB, "disk_free": 20 * host.GIB,
    })
    monkeypatch.setattr(finalization.epochs, "effective_registry", lambda _directory, value: value)
    monkeypatch.setattr(finalization.time, "time", lambda: 100)

    finalization.monitor(tmp_path, registry, epoch, admitted)
    safety_receipts = list(tmp_path.glob(f"finalize-{token}-safety-*.json"))
    assert len(safety_receipts) == 1


def test_failure_receipt_adds_safe_site_without_exception_contents(tmp_path, monkeypatch):
    store = ReceiptStore(tmp_path)
    token = "9" * 32
    epoch = {"index": 1, "sha256": "epoch", "release": "/release", "allocations": {}}
    registry = {"registry_sha256": "registry"}
    admitted = {
        "token": token, "registry_sha256": "registry", "epoch_sha256": "epoch",
        "containers": [], "jobs": [], "admitted_at": 1, "drain_timeout": 1,
        "deadline": 200, "restart_readback": {"status": "absent"},
    }
    (tmp_path / "epoch-0001.finalize-admission.json").write_text(json.dumps(admitted))
    (tmp_path / f"finalize-{token}-drain.result.json").write_text("{}")
    monkeypatch.setattr(finalization, "stop_service", lambda *_args: (_ for _ in ()).throw(
        RuntimeError("sensitive argv must not be persisted")
    ))
    with pytest.raises(RuntimeError):
        finalization.execute(tmp_path, registry, epoch, store)
    failure = json.loads((tmp_path / f"finalize-{token}-failure.json").read_text())
    assert failure["error_code"] == "finalization_stage_failed"
    assert failure["error_type"] == "RuntimeError"
    assert failure["error_site"].startswith("test_finalization.py:")
    assert "sensitive argv" not in json.dumps(failure)


def db_container():
    return {
        "Id": "candidate-db-id", "Image": "candidate-db-image",
        "Mounts": [{"Name": "ade-hindsight-probe_db-data", "Destination": "/var/lib/postgresql/data"}],
    }


def test_dump_keeps_binary_stdout_separate_from_stderr_and_publishes_hash(tmp_path, monkeypatch):
    state = tmp_path / "supervisor"
    store = ReceiptStore(state)
    token = "a" * 32
    admitted = {"token": token, "registry_sha256": "registry", "epoch_sha256": "epoch",
                "dump_timeout": 10, "restart_readback": {"status": "absent"}}
    root = state / "finalization" / token
    root.mkdir(parents=True, mode=0o700)
    monkeypatch.setattr(candidate_database, "db_container", lambda *_: db_container())
    monkeypatch.setattr(candidate_database, "psql_text", lambda *_: "hindsight_probe")
    monkeypatch.setattr(finalization.epochs, "active", lambda *_: {"sha256": "epoch", "index": 1})

    def monitored(_directory, _registry, _epoch, _admitted, command, _timeout, *, stdout, stderr, **kwargs):
        if "pg_dump" in command:
            stdout.write(b"PGDMP\x00ARCHIVE")
            stderr.write(b"diagnostic that must never enter the archive")
            return 0
        assert "pg_restore" in command
        return 0

    monkeypatch.setattr(finalization, "run_monitored", monitored)
    result = candidate_database.dump_database(tmp_path, {"release": "/release"}, admitted,
                                             {"volume": "ade-hindsight-probe_db-data", "database": "hindsight_probe"}, store, finalization.run_monitored)
    archive = root / result["archive"]
    assert archive.read_bytes() == b"PGDMP\x00ARCHIVE"
    assert result["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert result["toc_valid"] is True
    assert not list(root.glob("*.stderr.partial"))


@pytest.mark.parametrize("dump_status,toc_status,expected", [(1, 0, "candidate_dump_failed"), (0, 1, "candidate_dump_toc_invalid")])
def test_failed_dump_is_never_published(tmp_path, monkeypatch, dump_status, toc_status, expected):
    state = tmp_path / "supervisor"
    store = ReceiptStore(state)
    token = "b" * 32
    admitted = {"token": token, "registry_sha256": "registry", "epoch_sha256": "epoch",
                "dump_timeout": 10, "restart_readback": {"status": "absent"}}
    root = state / "finalization" / token
    root.mkdir(parents=True, mode=0o700)
    monkeypatch.setattr(candidate_database, "db_container", lambda *_: db_container())
    monkeypatch.setattr(candidate_database, "psql_text", lambda *_: "hindsight_probe")
    monkeypatch.setattr(finalization.epochs, "active", lambda *_: {"sha256": "epoch", "index": 1})

    def monitored(_directory, _registry, _epoch, _admitted, command, _timeout, *, stdout, stderr, **kwargs):
        if "pg_dump" in command:
            stdout.write(b"PGDMP partial")
            stderr.write(b"private diagnostic")
            return dump_status
        return toc_status

    monkeypatch.setattr(finalization, "run_monitored", monitored)
    with pytest.raises(RuntimeError, match=expected):
        candidate_database.dump_database(tmp_path, {"release": "/release"}, admitted,
                                         {"volume": "ade-hindsight-probe_db-data", "database": "hindsight_probe"}, store, finalization.run_monitored)
    assert not (root / "candidate.dump").exists()
    assert not (state / f"finalize-{token}-dump-result.json").exists()


def test_async_drain_counts_deferred_as_active_and_preserves_terminal_summary(monkeypatch):
    monkeypatch.setattr(candidate_database, "db_container", lambda *_: db_container())
    monkeypatch.setattr(candidate_database, "psql_text", lambda *_: json.dumps({
        "pending": 1, "processing": 2, "deferred": 3, "failed": 4, "cancelled": 5,
    }))
    counts = candidate_database.operation_status_counts(None, {}, {}, lambda *_: None)
    assert counts == {"pending": 1, "processing": 2, "deferred": 3, "failed": 4, "cancelled": 5}
    assert candidate_database.operation_count(None, {}, {}, lambda *_: None) == 6


def test_finalization_intent_cannot_authorize_an_unadmitted_container(tmp_path):
    epoch = {"index": 1}
    token = "c" * 32
    admitted = {"token": token, "containers": [{"id": "admitted-db", "service": "db"}]}
    (tmp_path / "epoch-0001.finalize-admission.json").write_text(json.dumps(admitted))
    (tmp_path / f"finalize-{token}-hindsight-stop.intent.json").write_text(json.dumps({
        "services": ["hindsight"], "container_ids": ["forged-container"],
    }))
    with pytest.raises(RuntimeError, match="identity_mismatch"):
        finalization.planned_ids(tmp_path, epoch)


def test_non_stop_stage_intents_do_not_become_planned_container_exits(tmp_path):
    token = "e" * 32
    epoch = {"index": 1}
    admitted = {"token": token, "containers": []}
    (tmp_path / "epoch-0001.finalize-admission.json").write_text(json.dumps(admitted))
    (tmp_path / f"finalize-{token}-canonical-snapshot.intent.json").write_text(json.dumps({
        "token": token, "started_at": 123,
    }))
    assert finalization.planned_ids(tmp_path, epoch) == set()


def test_runner_removal_requires_a_completed_registered_runner_run(tmp_path, monkeypatch):
    token = "f" * 32
    (tmp_path / f"job-{token}.result.json").write_text(json.dumps({"exit_code": 0}))
    monkeypatch.setattr(finalization.host, "tagged_processes", lambda _token: [])
    admitted = {"jobs": [{"token": token, "kind": "work", "operation": "run", "service": "runner"}]}
    row = {"service": "runner", "oneoff": True}
    assert finalization.runner_removal_proven(tmp_path, admitted, row)
    admitted["jobs"][0]["operation"] = "exec"
    assert not finalization.runner_removal_proven(tmp_path, admitted, row)


def test_emergency_stop_marker_preempts_a_pending_finalizer(tmp_path):
    from workflows.evals.hindsight_memory_probe import quiescence

    epoch = {"index": 7}
    store = ReceiptStore(tmp_path)
    store.write(quiescence.stop_path(tmp_path, epoch).name, {"reason": "safety"})
    with pytest.raises(RuntimeError, match="preempted"):
        finalization.monitor(tmp_path, {}, epoch, {})


def test_finalization_orders_worker_stop_snapshot_dump_then_router_database(tmp_path, monkeypatch):
    state = tmp_path / "supervisor"
    store = ReceiptStore(state)
    registry = {"registry_sha256": "registry", "release": "/release"}
    epoch = {"index": 1, "sha256": "epoch", "release": "/release", "allocations": {}}
    token = "d" * 32
    admitted = {"registry_sha256": "registry", "epoch_sha256": "epoch", "token": token,
                "jobs": [], "admitted_at": 1, "drain_timeout": 30, "deadline": 100,
                "restart_readback": {"status": "absent"}}
    store.write("epoch-0001.finalize-admission.json", admitted)
    actions = []
    monkeypatch.setattr(finalization, "wait_until", lambda *_args, **_kwargs: actions.append("drain-check"))
    monkeypatch.setattr(candidate_database, "operation_count", lambda *_args: 0)
    monkeypatch.setattr(candidate_database, "operation_status_counts", lambda *_args: {"completed": 2})
    monkeypatch.setattr(finalization, "stop_service", lambda _directory, _registry, _admitted, _epoch, _store, service: actions.append(f"stop-{service}"))
    monkeypatch.setattr(candidate_database, "snapshot_database", lambda *_args: actions.append("snapshot") or {"snapshot": True})
    monkeypatch.setattr(candidate_database, "dump_database", lambda *_args: actions.append("dump") or {"dump": True})
    finalization.execute(state, registry, epoch, store)
    assert actions == ["drain-check", "drain-check", "stop-runner", "stop-hindsight", "snapshot",
                       "dump", "stop-model-router", "stop-db"]


@pytest.mark.parametrize("planned,expected", [(True, None), (False, "candidate_service_exited")])
def test_only_exact_admitted_hindsight_exit_is_a_planned_lifecycle_exit(planned, expected):
    from workflows.evals.hindsight_memory_probe import host_guard as host

    item = {
        "Id": "hindsight-id", "Image": "image-id", "RestartCount": 0,
        "State": {"StartedAt": "start", "Status": "exited", "ExitCode": 0, "OOMKilled": False},
        "HostConfig": {"Memory": 1, "NanoCpus": 1},
        "Config": {"Labels": {
            "com.docker.compose.project": host.PROJECT,
            "com.docker.compose.service": "hindsight",
            "com.docker.compose.project.working_dir": "/release/workflows/evals/hindsight_memory_probe",
            "com.docker.compose.project.config_files": "/release/workflows/evals/hindsight_memory_probe/compose.yaml",
        }},
    }
    registry = {"baseline": [], "release": "/release"}
    lifecycle_view = {"containers": {"hindsight-id": "planned_stopped"} if planned else {}, "reason": None}
    reason, _ = host.guard_reason(
        registry, [item], 4 * host.GIB, 20 * host.GIB, None, 1,
        lifecycle_view=lifecycle_view,
    )
    assert reason == expected
