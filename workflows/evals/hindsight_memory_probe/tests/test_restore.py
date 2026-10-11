"""Offline disposable-restore identity, persistence and scope contracts."""

import hashlib
import json
import os
import shlex
import subprocess
import sys
import threading
import textwrap
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

REPOSITORY = ROOT.parents[2]


def _hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _selection():
    return {
        "schema": 1,
        "release_sha": "a" * 40,
        "registry_sha256": "b" * 64,
        "before_epoch_sha256": "c" * 64,
        "banks": [{
            "bank_id": "public-bank-id", "workspace_id": "workspace-a", "subject_id": "subject-a",
            "scopes": [{
                "character_root_id": "root-a", "tags": ["character:root-a", "kind:profile"],
                "tags_match": "any_strict", "cohort_ids": ["fact-a", "fact-b", "fact-c", "fact-d"],
                "positive_ids": ["fact-a", "fact-b"], "exclusion_ids": ["fact-c", "fact-d"],
            }],
            "sources": [{
                "source_id": "source-a", "original_text_sha256": _hash("source text"),
                "context_sha256": _hash("retained context"), "content_hash": "sha-content-a",
                "curation_ids": ["fact-d"],
                "facts": {"valid": [
                    {"id": "fact-a", "text_sha256": _hash("profile with char tag")},
                    {"id": "fact-b", "text_sha256": _hash("profile tag only")},
                    {"id": "fact-c", "text_sha256": _hash("cross root observation")},
                ], "invalidated": [{"id": "fact-d", "text_sha256": _hash("invalidated profile")} ]},
            }],
        }],
    }


def _rows(selection, *, vector="[0.25,0.75]"):
    bank = selection["banks"][0]
    return {
        "banks": [{"bank_id": bank["bank_id"]}],
        "documents": [{"id": "source-a", "bank_id": bank["bank_id"],
                       "original_text": "source text", "content_hash": "sha-content-a",
                       "retain_params": {"context": "retained context"}}],
        "chunks": [{"id": "chunk-a", "embedding": vector}],
        "memory_units": [
            {"id": "fact-a", "document_id": "source-a", "text": "profile with char tag",
             "bank_id": bank["bank_id"], "tags": ["character:root-a", "kind:profile"], "fact_type": "world",
             "source_memory_ids": ["source-memory-a"], "embedding": vector},
            {"id": "fact-b", "document_id": "source-a", "text": "profile tag only",
             "bank_id": bank["bank_id"], "tags": ["kind:profile"], "fact_type": "world", "embedding": vector},
            {"id": "fact-c", "document_id": "source-a", "text": "cross root observation",
             "bank_id": bank["bank_id"], "fact_type": "observation", "tags": ["character:root-a", "character:root-b"],
             "embedding": vector},
        ],
        "invalidated_memory_units": [{"id": "fact-d", "document_id": "source-a",
             "text": "invalidated profile", "bank_id": bank["bank_id"], "fact_type": "world",
             "tags": ["kind:profile"], "source_memory_ids": ["fact-a"], "embedding": vector}],
        "observation_history": [{"id": "observation-history-a", "source_memory_ids": ["source-memory-a"],
                                 "memory_unit_id": "fact-c"}], "entities": [],
        "unit_entities": [], "entity_cooccurrences": [], "memory_links": [],
        "schema_extensions": [{"schemas": [{"name": "public", "owner": "postgres"}],
                               "extensions": [{"name": "vector", "version": "0.8.6"}],
                               "alembic": [{"version_num": "frozen"}] }],
    }


def _snapshot(root, values):
    root.mkdir()
    entries = {}
    for name, rows in values.items():
        content = (json.dumps(rows[0], sort_keys=True, separators=(",", ":"))
                   if name == "schema_extensions" else
                   "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows))
        filename = "schema-extensions.json" if name == "schema_extensions" else name + ".jsonl"
        (root / filename).write_text(content, encoding="utf-8")
        payload = (root / filename).read_bytes()
        entries[name] = {"file": filename, "sha256": hashlib.sha256(payload).hexdigest(),
                         "bytes": len(payload)}
    scope_file = root / "scope-eligibility.json"
    scope_content = json.dumps({"status": "absent"}, sort_keys=True, separators=(",", ":"))
    scope_file.write_text(scope_content, encoding="utf-8")
    scope_bytes = scope_file.read_bytes()
    entries["scope_eligibility"] = {"file": scope_file.name,
                                    "sha256": hashlib.sha256(scope_bytes).hexdigest(),
                                    "bytes": len(scope_bytes)}
    return {"schema": 1, "database": "hindsight_probe", "tables": entries}


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
    assert sorted(outcomes) == ["launched", "restore_controller_already_running"]


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


def test_full_restore_host_path_runs_under_python_no_site_with_real_docker_text(tmp_path):
    state = tmp_path / "private" / "receipts" / "supervisor"
    state.mkdir(parents=True, mode=0o700)
    restore_token = "1" * 32
    registry_sha = "b" * 64
    epoch_sha = "d" * 64
    release_sha = "a" * 40
    release = tmp_path / "release" / release_sha
    release.mkdir(parents=True)
    (release / "workflows").symlink_to(REPOSITORY / "workflows", target_is_directory=True)
    source_image = f"ade-hindsight-probe-db:{release_sha}"
    image_id = "sha256:" + "e" * 64
    workdir = str(release / "workflows/evals/hindsight_memory_probe")
    main_container = {
        "Id": "main-db", "Image": image_id,
        "State": {"StartedAt": "2026-10-11T06:00:00Z", "Status": "exited", "OOMKilled": False},
        "RestartCount": 0,
        "Config": {"Image": source_image, "Env": ["POSTGRES_DB=hindsight_probe"], "Labels": {
            "com.docker.compose.project": "ade-hindsight-probe", "com.docker.compose.service": "db",
            "com.docker.compose.project.working_dir": workdir,
            "com.docker.compose.project.config_files": workdir + "/compose.yaml",
            "com.docker.compose.oneoff": "False"}},
        "HostConfig": {"Memory": 1073741824, "NanoCpus": 250000000, "NetworkMode": "default"},
        "NetworkSettings": {"Ports": {}},
        "Mounts": [{"Name": "ade-hindsight-probe_db-data", "Destination": "/var/lib/postgresql/data", "RW": True}],
    }
    admission = {"release_path": str(release), "containers": [{
        "id": "main-db", "image_id": image_id, "started_at": "2026-10-11T06:00:00Z",
        "status": "running", "service": "db", "project": "ade-hindsight-probe",
        "working_dir": workdir, "config_files": workdir + "/compose.yaml", "oneoff": False,
    }]}
    registry = {"registry_sha256": registry_sha, "release": "/immutable/initial-release", "baseline": []}
    (state / "registry.json").write_text(json.dumps(registry))
    (state / "epoch-0001.finalize-admission.json").write_text(json.dumps(admission))
    finalized_path = state / "epoch-0001.finalized.json"
    finalized_path.write_text("{}")

    selection = _selection()
    selection["release_sha"] = release_sha
    selection["registry_sha256"] = registry_sha
    selection["before_epoch_sha256"] = "c" * 64
    selection_path = state.parent / "restart-selection.json"
    selection_path.write_text(json.dumps(selection, sort_keys=True))
    rows = _rows(selection)
    source_root = state / "finalization" / "final-token"
    source_root.parent.mkdir()
    original_snapshot = _snapshot(source_root, rows)
    scope_evidence = {"status": "public_readback_bound", "selection_sha256": "1" * 64,
        "selection_file_sha256": "2" * 64, "restart_readback_sha256": "3" * 64,
        "before_file_sha256": "4" * 64, "before_snapshot_sha256": "5" * 64,
        "after_file_sha256": "6" * 64, "after_snapshot_sha256": "7" * 64}
    scope_path = source_root / "scope-eligibility.json"
    scope_path.write_text(json.dumps(scope_evidence, sort_keys=True, separators=(",", ":")) + "\n")
    scope_bytes = scope_path.read_bytes()
    original_snapshot["tables"]["scope_eligibility"] = {
        "file": scope_path.name, "sha256": hashlib.sha256(scope_bytes).hexdigest(),
        "bytes": len(scope_bytes)}
    snapshot_path = state / "finalize-final-token-canonical-snapshot.json"
    snapshot_path.write_text(json.dumps(original_snapshot, sort_keys=True))
    archive = state / "finalization" / "final-token" / "candidate.dump"
    archive.write_bytes(b"PGDMP\x00synthetic-archive")
    compose = restore_database.write_compose(state / "restore" / restore_token, restore_token,
                                             source_image, image_id)
    now = time.time()
    operation = {
        "schema": 1, "status": "admitted", "token": restore_token,
        "registry_sha256": registry_sha, "epoch_sha256": epoch_sha,
        "parent_finalization_token": "final-token", "parent_stopped_epoch_sha256": epoch_sha,
        "release_path": str(release), "admitted_at": now, "deadline": now + 900,
        "cleanup_deadline": now + 1020, "hard_deadline": DEADLINE,
        "restore_memory_bytes": 1073741824, "restore_cpu": 0.25,
        "finalization": {"containers": admission["containers"], "release_path": str(release)},
        "archive": {"path": str(archive), "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                    "bytes": archive.stat().st_size, "dump_result_sha256": "f" * 64},
        "snapshot": {"path": str(snapshot_path), "sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
                     "root": str(source_root)},
        "selection": {"path": str(selection_path), "sha256": hashlib.sha256(selection_path.read_bytes()).hexdigest(),
                      "restart_proof_sha256": "a" * 64},
        "compose": compose, "restore_root": str(state / "restore" / restore_token),
        "state_directory": str(state),
    }
    operation_path = state / "restore-operation.json"
    operation_path.write_text(json.dumps(operation, sort_keys=True))
    (state / "restore-operation-seal.json").write_text(json.dumps({
        "schema": 1, "token": restore_token,
        "sha256": hashlib.sha256(operation_path.read_bytes()).hexdigest(),
    }))

    docker_state_path = tmp_path / "docker-state.json"
    docker_state_path.write_text(json.dumps({
        "containers": {"main-db": main_container}, "volumes": {}, "images": {source_image: image_id},
        "tables": rows,
    }))
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    fake_docker = tmp_path / "fake_docker.py"
    fake_docker.write_text(textwrap.dedent(r'''
        import json, os, re, sys
        from pathlib import Path
        state_path = Path(os.environ["FAKE_DOCKER_STATE"])
        state = json.loads(state_path.read_text())
        args = sys.argv[1:]
        with Path(str(state_path) + ".commands").open("a") as log: log.write(repr(args) + "\\n")
        def save(): state_path.write_text(json.dumps(state))
        def out(value): sys.stdout.write(value)
        def emit(value): out(json.dumps(value))
        if args[:2] == ["ps", "-aq"]:
            if "--filter" in args:
                volume = args[args.index("--filter") + 1].removeprefix("volume=")
                ids = [key for key, row in state["containers"].items()
                       if any(m.get("Name") == volume for m in row.get("Mounts", []))]
            else: ids = list(state["containers"])
            out("".join(identifier + "\n" for identifier in ids))
        elif args[:1] == ["inspect"]:
            emit([state["containers"][identifier] for identifier in args[1:]])
        elif args[:2] == ["image", "inspect"]:
            emit([{"Id": state["images"][args[2]]}])
        elif args[:3] == ["volume", "ls", "-q"]:
            out("".join(name + "\n" for name in state["volumes"]))
        elif args[:2] == ["volume", "inspect"]:
            emit([state["volumes"][args[2]]])
        elif args[:2] == ["compose", "--project-name"] and "up" in args:
            project, config = args[2], args[4]
            config_text = Path(config).read_text()
            token = re.search(r"ade\.hindsight\.restore\.token: ([0-9a-f]{32})", config_text).group(1)
            volume = re.search(r"(?m)^    name: ([^\n]+)$", config_text).group(1)
            image = re.search(r"    image: (.+)", config_text).group(1)
            state["volumes"][volume] = {"Name": volume, "Driver": "local", "Scope": "local", "Options": None,
                "Mountpoint": "/docker/volumes/"+volume, "CreatedAt": "2026-10-11T06:01:00Z",
                "Labels": {"com.docker.compose.project": project, "com.docker.compose.volume": "data",
                           "ade.hindsight.restore.token": token}}
            state["containers"]["restore-db"] = {"Id": "restore-db", "Image": state["images"][image],
                "RestartCount": 0, "State": {"StartedAt": "2026-10-11T06:01:01Z", "Status": "running", "OOMKilled": False},
                "Config": {"Image": image, "Env": ["POSTGRES_DB=hindsight_probe", "POSTGRES_USER=hindsight_probe"],
                    "Labels": {"ade.hindsight.restore.token": token, "com.docker.compose.project": project,
                        "com.docker.compose.service": "db", "com.docker.compose.project.config_files": config,
                        "com.docker.compose.project.working_dir": str(Path(config).parent)}},
                "HostConfig": {"NetworkMode": "none", "Memory": 1073741824, "NanoCpus": 250000000},
                "NetworkSettings": {"Ports": {}}, "Mounts": [{"Name": volume, "Destination": "/var/lib/postgresql/data", "RW": True}]}
            save()
        elif args[:2] == ["exec", "-i"]:
            command = args[3:]
            if command[0] == "pg_restore":
                assert sys.stdin.buffer.read().startswith(b"PGDMP")
            elif command[0] == "psql":
                query = command[-1]
                if query == "SELECT current_database()": out("hindsight_probe\n")
                elif " AS t" in query:
                    table = re.search(r"FROM public\.([a-z_]+) AS t", query).group(1)
                    for row in state["tables"][table]: out(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
                else: out(json.dumps(state["tables"]["schema_extensions"][0], separators=(",", ":")))
        elif args[:1] == ["stop"]:
            state["containers"][args[-1]]["State"]["Status"] = "exited"; save()
            out(args[-1] + "\n")
        elif args[:1] == ["rm"]:
            del state["containers"][args[-1]]; save(); out(args[-1] + "\n")
        elif args[:2] == ["volume", "rm"]:
            del state["volumes"][args[-1]]; save(); out(args[-1] + "\n")
        else:
            raise SystemExit("unsupported synthetic docker command: " + repr(args))
    '''), encoding="utf-8")
    docker_wrapper = fakebin / "docker"
    docker_wrapper.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " -S "
                              + shlex.quote(str(fake_docker)) + " \"$@\"\n")
    docker_wrapper.chmod(0o700)

    runner = tmp_path / "host_path.py"
    runner.write_text(textwrap.dedent(r'''
        import hashlib, json, os, sys
        from pathlib import Path
        sys.path.insert(0, sys.argv[2])
        from workflows.evals.hindsight_memory_probe import epochs, host_guard, restore, restore_controller, restore_process
        from workflows.evals.hindsight_memory_probe.host_guard import GIB
        state = Path(sys.argv[1]); token = "1" * 32
        epoch = {"index": 1, "sha256": "d" * 64, "release": json.loads((state/"restore-operation.json").read_text())["release_path"], "allocations": {}}
        epochs.active = lambda *_: epoch
        restore._verify_host = lambda *_args, **_kwargs: []
        host_guard.host_sample = lambda _release: {"memory_available": 8 * GIB, "disk_free": 50 * GIB, "cpus": 2}
        def identity(pid): return {"pid": pid, "start_ticks": "synthetic", "uid": os.getuid(), "cmd_sha256": "a" * 64}
        def alive(value, *_args):
            try: os.kill(value["pid"], 0); return True
            except OSError: return False
        host_guard.proc_identity = identity
        host_guard.identity_matches = alive
        host_guard.tagged_processes = lambda _token, *_args: []
        restore_process.host.proc_identity = identity
        restore_process.host.identity_matches = alive
        restore_process.host.tagged_processes = lambda _token, *_args: []
        os.environ["ADE_PROBE_PROCESS_OWNER"] = "controller-token"
        identity = host_guard.proc_identity(os.getpid())
        restore.ReceiptStore(state).write("restore-"+token+"-controller-controller-token.json", {
            "token": token, "controller_token": "controller-token", "identity": identity})
        code = restore_controller.Controller(state, token, "controller-token").run_guarded()
        if code:
            print(sorted(path.name for path in state.glob("restore-"+token+"-*.json")), file=sys.stderr)
            for path in state.glob("restore-"+token+"-*.json"):
                print(path.name + ":" + path.read_text(), file=sys.stderr)
            for path in state.glob("job-*.result.json"):
                print(path.name + ":" + path.read_text(), file=sys.stderr)
        assert code == 0
        result = json.loads((state/("restore-"+token+"-result.json")).read_text())
        cleanup = json.loads((state/("restore-"+token+"-cleanup.result.json")).read_text())
        comparison = json.loads((state/("restore-"+token+"-compare.result.json")).read_text())
        assert result["claim"] == "logical_persisted_state_restore_only"
        assert cleanup["status"] == "completed"
        assert comparison["scope_evidence"]["status"] == "public_readback_bound"
        assert comparison["table_counts"]["observation_history"] == {"before": 1, "after": 1}
        assert "httpx" not in sys.modules and "ade_api" not in sys.modules
        print("restore_host_path_stdlib_ok")
    '''), encoding="utf-8")
    environment = {**os.environ, "PATH": str(fakebin) + os.pathsep + os.environ["PATH"],
                   "FAKE_DOCKER_STATE": str(docker_state_path)}
    result = subprocess.run([sys.executable, "-S", str(runner), str(state), str(REPOSITORY)],
                            cwd=REPOSITORY, env=environment, capture_output=True, text=True,
                            timeout=120)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "restore_host_path_stdlib_ok"
