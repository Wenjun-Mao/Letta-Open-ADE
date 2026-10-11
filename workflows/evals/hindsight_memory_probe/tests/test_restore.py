"""Offline disposable-restore identity, persistence and scope contracts."""

import json
import fcntl
import hashlib
import os
import threading
import time

import pytest

from workflows.evals.hindsight_memory_probe import (
    epochs,
    restore,
    restore_compare,
    restore_database,
    restore_process,
    restart_selection,
)
from workflows.evals.hindsight_memory_probe.campaign_clock import DEADLINE
from workflows.evals.hindsight_memory_probe.validate import ROOT
from workflows.evals.hindsight_memory_probe.tests.restore_test_support import _rows, _selection, _snapshot

REPOSITORY = ROOT.parents[2]


def test_canonical_rows_and_frozen_scope_compare(tmp_path):
    selection = _selection()
    restart_selection.validate_selection(selection)
    before_rows = _rows(selection)
    after_rows = _rows(selection)
    before = _snapshot(tmp_path / "before", before_rows)
    after = _snapshot(tmp_path / "after", after_rows)

    result = restore_compare.compare(before, tmp_path / "before", after, tmp_path / "after", selection)

    assert result["status"] == "completed"
    assert result["claim"] == "logical_persisted_state_restore_only"
    assert result["scope_before"][0]["scopes"][0]["positive_ids"] == ["fact-a", "fact-b"]
    assert result["scope_before"][0]["scopes"][0]["exclusion_ids"] == ["fact-c", "fact-d"]
    assert "vector_rows" in result["compared_categories"]


def test_vector_data_difference_is_a_table_mismatch(tmp_path):
    selection = _selection()
    before = _snapshot(tmp_path / "before", _rows(selection))
    after = _snapshot(tmp_path / "after", _rows(selection, vector="[0.25,0.76]"))

    result = restore_compare.compare(before, tmp_path / "before", after, tmp_path / "after", selection)

    assert result["status"] == "mismatch"
    assert any(row["table"] in {"chunks", "memory_units"} for row in result["table_mismatches"])


def test_scope_mismatch_is_recorded_even_when_raw_rows_are_present(tmp_path):
    selection = _selection()
    before = _snapshot(tmp_path / "before", _rows(selection))
    after_rows = _rows(selection)
    after_rows["memory_units"][1]["tags"] = ["kind:unrelated"]
    after = _snapshot(tmp_path / "after", after_rows)

    result = restore_compare.compare(before, tmp_path / "before", after, tmp_path / "after", selection)

    assert result["status"] == "mismatch"
    assert not result["scope_matches"]
    assert result["scope_after"][0]["scopes"][0]["eligibility_matches"] is False


def test_snapshot_file_tampering_fails_before_comparison(tmp_path):
    selection = _selection()
    before = _snapshot(tmp_path / "before", _rows(selection))
    after = _snapshot(tmp_path / "after", _rows(selection))
    (tmp_path / "after" / "chunks.jsonl").write_text("{}\n")

    with pytest.raises(RuntimeError, match="hash_mismatch"):
        restore_compare.compare(before, tmp_path / "before", after, tmp_path / "after", selection)


def test_blank_line_in_table_jsonl_remains_malformed(tmp_path):
    content = b'{"id":"row-a"}\n\n{"id":"row-b"}\n'
    (tmp_path / "banks.jsonl").write_bytes(content)
    snapshot = {"tables": {"banks": {
        "file": "banks.jsonl", "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
    }}}

    with pytest.raises(RuntimeError, match="restore_table_snapshot_invalid"):
        restore_compare._table_rows(snapshot, tmp_path)


def test_compose_is_one_private_networkless_db_service(tmp_path):
    token = "d" * 32
    operation = {"token": token, "state_directory": str(tmp_path), "compose": restore_database.write_compose(
        tmp_path / "restore" / token, token, "ade-hindsight-probe-db:" + "a" * 40, "sha256:" + "e" * 64)}
    restore_database.verify_compose(operation)
    text = (tmp_path / "restore" / token / "compose.yaml").read_text()
    assert "network_mode: none" in text
    assert "ports:" not in text and "build:" not in text and "env_file:" not in text
    assert "/var/lib/postgresql/data" in text
    assert (tmp_path / "restore" / token / "compose.yaml").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("token", ["1" * 32, "1e" + "0" * 30, "a" * 32])
def test_compose_render_preserves_restore_token_labels_as_strings(tmp_path, token):
    import shutil
    import subprocess

    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("Docker Compose CLI unavailable; restore token rendering is unverified")
    compose = restore_database.write_compose(
        tmp_path / token, token, "ade-hindsight-probe-db:" + "b" * 40,
        "sha256:" + "e" * 64)

    rendered = subprocess.run([docker, "compose", "-f", compose["path"], "config", "--format", "json"],
        check=True, capture_output=True, text=True, timeout=15)
    value = json.loads(rendered.stdout)

    assert value["services"]["db"]["labels"]["ade.hindsight.restore.token"] == token
    assert value["volumes"]["data"]["labels"]["ade.hindsight.restore.token"] == token


def test_rearm_is_blocked_until_exact_restore_cleanup_is_complete(tmp_path):
    (tmp_path / "restore-operation.json").write_text(json.dumps({"token": "e" * 32}))
    with pytest.raises(RuntimeError, match="rearm_blocked_by_disposable_restore"):
        epochs.append(tmp_path, {}, {}, {}, "test", now=epochs.WORK_CUTOFF - 1)


def test_operation_seal_rejects_forged_or_interrupted_publication(tmp_path):
    token = "f" * 32
    operation = {"schema": 1, "token": token, "deadline": epochs.WORK_CUTOFF,
                 "hard_deadline": DEADLINE,
                 "compose": {"project": "ade-hindsight-restore-" + token[:16]}}
    (tmp_path / "restore-operation.json").write_text(json.dumps(operation))

    with pytest.raises(RuntimeError, match="seal_invalid"):
        restore.read_operation(tmp_path)


def test_expired_restore_deadline_keeps_bounded_cleanup_reserve():
    operation = {"deadline": 200.0, "cleanup_deadline": 300.0}
    assert restore_process.command_deadline(operation, 45, "pg-restore", 190.0) == 200.0
    assert restore_process.command_deadline(operation, 45, "cleanup-stop", 250.0) == 295.0
    assert restore_process.command_deadline(operation, 45, "restore-operator-readback", 290.0) == 300.0


def test_controller_lease_allows_only_one_concurrent_resume(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    operation = {"token": "c" * 32}
    first_inside_launch = threading.Event()
    release_first = threading.Event()
    outcomes = []

    def fake_launch(directory, _operation, *, resume=False):
        first_inside_launch.set()
        assert release_first.wait(timeout=5)
        restore.ReceiptStore(directory).write(
            f"restore-{operation['token']}-controller-first.json",
            {"token": operation["token"], "identity": {"pid": 1}})

    monkeypatch.setattr(restore, "_launch", fake_launch)
    monkeypatch.setattr(restore.host, "identity_matches", lambda _identity: True)

    def attempt():
        try:
            restore._launch_exclusive(tmp_path, operation, resume=True)
            outcomes.append("launched")
        except RuntimeError as exc:
            outcomes.append(str(exc))

    first = threading.Thread(target=attempt)
    second = threading.Thread(target=attempt)
    first.start()
    assert first_inside_launch.wait(timeout=5)
    second.start()
    release_first.set()
    first.join(timeout=5)
    second.join(timeout=5)

    assert not first.is_alive() and not second.is_alive()
    assert sorted(outcomes) == ["launched", "restore_controller_lease_busy"]


def test_stuck_controller_lease_fails_closed_without_waiting(tmp_path):
    lock_fd = os.open(tmp_path / "restore-controller.lock", os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    try:
        with pytest.raises(RuntimeError, match="restore_controller_lease_busy"):
            restore._launch_exclusive(tmp_path, {"token": "c" * 32})
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def test_stop_intent_preempts_controller_check_before_next_docker_action(tmp_path, monkeypatch):
    from workflows.evals.hindsight_memory_probe import restore_controller
    token = "d" * 32
    operation = {"token": token, "registry_sha256": "a" * 64, "epoch_sha256": "b" * 64,
                 "deadline": time.time() + 60}
    operation_path = tmp_path / "restore-operation.json"
    operation_path.write_text(json.dumps(operation))
    stop_path = tmp_path / f"restore-{token}-stop.intent.json"
    stop_path.write_text(json.dumps({"schema": 1, "token": token,
        "registry_sha256": operation["registry_sha256"], "epoch_sha256": operation["epoch_sha256"],
        "kind": "emergency_restore_preemption", "requested_at": time.time()}))
    controller = restore_controller.Controller.__new__(restore_controller.Controller)
    controller.directory, controller.token, controller.operation = tmp_path, token, operation
    controller.operation_hash = hashlib.sha256(operation_path.read_bytes()).hexdigest()
    monkeypatch.setattr(restore_controller.host, "host_sample", lambda _release: {
        "memory_available": 8 * 1024**3, "cpus": 2, "disk_free": 50 * 1024**3})

    with pytest.raises(RuntimeError, match="restore_stop_requested"):
        controller.check_basic()


def test_cleanup_preserves_volume_when_restored_state_mismatches(tmp_path, monkeypatch):
    import contextlib

    from workflows.evals.hindsight_memory_probe import restore_cleanup

    tmp_path.chmod(0o700)
    token = "e" * 32
    selection = _selection()
    original_root = tmp_path / "original"
    original = _snapshot(original_root, _rows(selection))
    snapshot_path = tmp_path / "source-snapshot.json"
    snapshot_path.write_text(json.dumps(original, sort_keys=True))
    archive = tmp_path / "candidate.dump"
    archive.write_bytes(b"PGDMP synthetic")
    restore_root = tmp_path / "restore" / token
    restore_root.parent.mkdir()
    restored = _snapshot(restore_root, _rows(selection))
    (restore_root / "canonical-snapshot.json").write_text(json.dumps(restored))
    (tmp_path / "restart-selection.json").write_text(json.dumps(selection))
    operation = {"schema": 1, "token": token, "deadline": time.time() + 30,
        "cleanup_deadline": time.time() + 60, "hard_deadline": DEADLINE,
        "registry_sha256": "a" * 64, "epoch_sha256": "b" * 64,
        "compose": {"project": restore_database.project_for(token), "volume": "restore-volume"},
        "archive": {"path": str(archive), "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()},
        "snapshot": {"path": str(snapshot_path), "sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest()},
        "selection": {"path": str(tmp_path / "restart-selection.json")},
        "restore_root": str(restore_root), "finalization": {"containers": []}}
    operation_path = tmp_path / "restore-operation.json"
    operation_path.write_text(json.dumps(operation))
    restore.ReceiptStore(tmp_path).write("restore-operation-seal.json", {
        "sha256": hashlib.sha256(operation_path.read_bytes()).hexdigest()})
    restore.ReceiptStore(tmp_path).write(f"restore-{token}-restore.intent.json", {"token": token})
    restore.ReceiptStore(tmp_path).write(f"restore-{token}-failure.result.json", {"status": "failed"})
    restore.ReceiptStore(tmp_path).write(f"restore-{token}-compare.result.json", {"status": "mismatch"})
    monkeypatch.setattr(restore_cleanup, "registered_host_readback", lambda *_args: contextlib.nullcontext())
    monkeypatch.setattr(restore_cleanup, "_docker_cleanup_command",
                        lambda *_args: None)
    monkeypatch.setattr(restore_cleanup.db, "restore_container", lambda *_args, **_kwargs: {
        "Id": "restore-db", "State": {"Status": "exited"}})
    monkeypatch.setattr(restore_cleanup.db, "verify_volume",
                        lambda *_args, **_kwargs: pytest.fail("mismatched volume must be preserved"))

    result = restore_cleanup.cleanup(tmp_path)

    assert result["status"] == "preserved_failed_state"
    assert result["reason"] == "restore_comparison_mismatch"
    assert result["removed"] is False


@pytest.mark.parametrize(("state", "restart_count", "oom", "reason"), [
    ("exited", 0, False, "restore_unexpected_container_exit"),
    ("running", 1, False, "restore_container_restart_or_oom"),
    ("running", 0, True, "restore_container_restart_or_oom"),
])
def test_controller_rejects_unexpected_restore_exit_restart_and_oom(
        tmp_path, monkeypatch, state, restart_count, oom, reason):
    from workflows.evals.hindsight_memory_probe import restore_controller

    tmp_path.chmod(0o700)
    token = "f" * 32
    operation = {"token": token, "deadline": time.time() + 60,
        "registry_sha256": "a" * 64, "epoch_sha256": "b" * 64,
        "state_directory": str(tmp_path), "compose": {"path": "compose.yaml"},
        "finalization": {"containers": []}}
    operation_path = tmp_path / "restore-operation.json"
    operation_path.write_text(json.dumps(operation))
    finalized = tmp_path / "epoch-0001.finalized.json"
    finalized.write_text("{}")
    registry = {"registry_sha256": operation["registry_sha256"]}
    (tmp_path / "registry.json").write_text(json.dumps(registry))
    epoch = {"index": 1, "sha256": operation["epoch_sha256"], "release": str(tmp_path)}
    (tmp_path / f"restore-{token}-create.result.json").write_text("{}")
    compose_hash = hashlib.sha256(operation_path.read_bytes()).hexdigest()
    controller = restore_controller.Controller.__new__(restore_controller.Controller)
    controller.directory, controller.token, controller.operation = tmp_path, token, operation
    controller.operation_hash = compose_hash
    controller.finalized_hash = hashlib.sha256(finalized.read_bytes()).hexdigest()
    controller.registry, controller.epoch = registry, epoch
    controller.admission, controller.stage = {"containers": []}, "test"
    controller.check_basic = lambda: None
    container = {"State": {"Status": state, "OOMKilled": oom}, "RestartCount": restart_count}
    monkeypatch.setattr(restore_controller.epochs, "active", lambda *_args: epoch)
    monkeypatch.setattr(restore_controller.restore, "_verify_host", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(restore_controller.db, "verify_compose", lambda *_args: None)
    monkeypatch.setattr(restore_controller.db, "restore_container", lambda *_args, **_kwargs: container)

    with pytest.raises(RuntimeError, match=reason):
        controller.check_safe()


def test_restore_exec_allowlist_rejects_multistatement_sql_and_wrong_container(tmp_path):
    token = "a" * 32
    operation = {"token": token, "state_directory": str(tmp_path),
        "compose": {"project": restore_database.project_for(token),
                    "path": str(tmp_path / "compose.yaml"), "volume": restore_database.volume_for(
                        restore_database.project_for(token)),
                    "source_image": "ade-hindsight-probe-db:" + "b" * 40}}
    (tmp_path / f"restore-{token}-create.result.json").write_text(
        json.dumps({"container_id": "restore-db"}))
    command = ["docker", "exec", "-i", "restore-db", "psql", "-U", "hindsight_probe",
               "-d", "hindsight_probe", "-At", "-c",
               "SELECT current_database(); DROP TABLE public.banks"]

    with pytest.raises(RuntimeError, match="exec_command_not_allowed"):
        restore_process._validate_command(operation, command)
    command[3] = "unrelated-container"
    command[-1] = "SELECT current_database()"
    with pytest.raises(RuntimeError, match="exec_command_not_allowed"):
        restore_process._validate_command(operation, command)


def test_process_child_rejects_unregistered_lifecycle_scope_before_command_dispatch(tmp_path):
    import shlex
    import subprocess
    import sys

    sentinel = tmp_path / "command-ran"
    docker = tmp_path / "docker"
    docker.write_text(f"#!/bin/sh\ntouch {shlex.quote(str(sentinel))}\n")
    docker.chmod(0o700)
    read_fd, write_fd = os.pipe()
    command = json.dumps(["docker", "compose", "up", "-d"])
    scope = json.dumps({"kind": "disposable_restore", "token": "forged"})
    environment = {**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"]}
    try:
        child = subprocess.Popen([sys.executable, "-S", "-m",
            "workflows.evals.hindsight_memory_probe.process_child", str(read_fd), command,
            str(tmp_path), "child-token", scope], cwd=REPOSITORY, env=environment,
            pass_fds=(read_fd,), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        os.close(read_fd)
        read_fd = -1
        os.write(write_fd, b"1")
        os.close(write_fd)
        write_fd = -1
        stdout, stderr = child.communicate(timeout=10)
    finally:
        if read_fd >= 0:
            os.close(read_fd)
        if write_fd >= 0:
            os.close(write_fd)

    assert child.returncode != 0
    assert not sentinel.exists()
    assert "restore_operation_missing" in stderr
