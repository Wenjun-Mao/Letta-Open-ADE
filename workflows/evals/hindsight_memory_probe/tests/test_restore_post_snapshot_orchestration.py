"""Exercise recovery orchestration and its registered readback receipts."""

import hashlib
import json
import os
from contextlib import nullcontext
from pathlib import Path

import pytest

from workflows.evals.hindsight_memory_probe import (
    restore_cleanup,
    restore_process,
    restore_post_snapshot_archive as archive,
    restore_post_snapshot_contract as contract,
    restore_post_snapshot_recovery as recovery,
)


def _write(path: Path, data: bytes, mode: int = 0o400) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)


def _active_failed_attempt(state: Path):
    token = "f" * 32
    container_id = "c" * 64
    volume = "restore-volume-failed-attempt"
    operation = {
        "token": token, "release_path": "/release/" + "1" * 40,
        "state_directory": str(state),
        "deadline": 1000.0, "cleanup_deadline": 1000.0,
        "compose": {"project": "restore-project", "path": "/compose.yaml", "volume": volume},
        "archive": {"path": "/source/archive.dump", "sha256": "a" * 64},
        "snapshot": {"path": "/source/snapshot.json", "root": "/source", "sha256": "b" * 64},
        "selection": {"path": "/source/selection.json", "sha256": "d" * 64},
        "restore_root": str(state / "restore" / token),
        "finalization": {"containers": []},
    }
    operation_path = state / "restore-operation.json"
    operation_path.write_text(json.dumps(operation, sort_keys=True))
    operation_path.chmod(0o400)
    operation_seal = state / "restore-operation-seal.json"
    operation_seal.write_text(json.dumps({"sha256": hashlib.sha256(operation_path.read_bytes()).hexdigest()}))
    operation_seal.chmod(0o400)
    (state / f"restore-{token}-failure.result.json").write_text(json.dumps({
        "token": token, "status": "failed", "stage": "snapshot",
        "reason": "restore_process_identity_changed", "time": 600.0,
    }))
    (state / f"restore-{token}-cleanup.result.json").write_text(json.dumps({
        "token": token, "status": "preserved_failed_state",
        "reason": "post_restore_snapshot_not_preserved", "removed": False, "time": 700.0,
    }))
    create_result = {"token": token, "container_id": container_id, "image_id": "image-id",
                     "volume": volume, "volume_identity": {
                         "Name": volume, "Driver": "local", "Scope": None, "Options": None,
                         "Mountpoint": None, "CreatedAt": None, "Labels": {},
                     }}
    (state / f"restore-{token}-create.result.json").write_text(json.dumps(create_result))
    (state / f"restore-{token}-restore.result.json").write_text(json.dumps({
        "token": token, "status": "completed", "container_id": container_id,
        "archive_sha256": operation["archive"]["sha256"],
    }))
    (state / f"restore-{token}-restore.intent.json").write_text(json.dumps({
        "container_id": container_id, "archive_sha256": operation["archive"]["sha256"],
    }))
    (state / "registry.json").write_text("{}")
    original_snapshot = state / "source-snapshot.json"
    original_snapshot.write_text('{"tables":{}}')
    return operation, create_result, original_snapshot


def _authority_for(state: Path, operation: dict, container_id: str, nonce: str) -> Path:
    token = operation["token"]
    path = state / f"restore-{token}-post-restore-authority-{nonce}.json"
    authority = {"schema": 1, "kind": "failed_post_restore_snapshot_recovery",
        "admission_token": nonce, "token": token,
        "operation_sha256": hashlib.sha256((state / "restore-operation.json").read_bytes()).hexdigest(),
        "failure_sha256": hashlib.sha256((state / f"restore-{token}-failure.result.json").read_bytes()).hexdigest(),
        "cleanup_sha256": hashlib.sha256((state / f"restore-{token}-cleanup.result.json").read_bytes()).hexdigest(),
        "container_id": container_id, "volume": operation["compose"]["volume"],
        "recovery_source_sha": "1" * 40, "issued_at": 800.0, "deadline": 900.0,
        "scopes": contract.SCOPES}
    _write(path, json.dumps(authority).encode())
    return path


def _wire_recovery_mocks(monkeypatch, *, interrupt_after_container=False):
    from workflows.evals.hindsight_memory_probe import (
        host_guard, restore_database, restore_process, restore_retirement,
    )

    container = {"Id": "c" * 64, "Image": "image-id", "Config": {"Labels": {}},
                 "State": {"Status": "exited", "StartedAt": "original-start", "OOMKilled": False},
                 "RestartCount": 0, "Mounts": []}
    volume = {"Name": "restore-volume-failed-attempt", "Driver": "local", "Labels": {}}
    resources = {"container": True, "volume": True, "commands": []}
    monkeypatch.setattr(restore_retirement, "admission_lease", lambda _directory: nullcontext())
    monkeypatch.setattr(recovery.restore, "_verify_host",
                        lambda *_args, **_kwargs: host_guard.containers())
    monkeypatch.setattr(recovery.restore, "_controller_present", lambda *_args: False)
    monkeypatch.setattr(restore_database, "verify_compose", lambda *_args: None)
    monkeypatch.setattr(restore_database, "restore_container",
                        lambda *_args, **_kwargs: container if resources["container"] else None)
    monkeypatch.setattr(restore_database, "verify_volume",
                        lambda *_args, **_kwargs: volume if resources["volume"] else None)
    monkeypatch.setattr(restore_database, "docker_json", lambda *_args: [])
    monkeypatch.setattr(restore_database, "docker_text", lambda *_args: [])
    monkeypatch.setattr(host_guard, "tagged_processes", lambda *_args: [])
    readback_counter = {"value": 0}

    def register_readback(directory, operation, command, timeout, *, operation_label,
                          monitor, stdout, stderr):
        restore_process._validate_command(operation, command)
        if command[1:] == ["ps", "-aq", "--no-trunc"]:
            output = (container["Id"] + "\n").encode()
        elif command[1:2] == ["inspect"]:
            output = json.dumps([container]).encode()
        elif command[1:] == ["volume", "ls", "-q", "--filter",
                              "name=" + volume["Name"]]:
            output = (volume["Name"] + "\n").encode()
        elif command[1:] == ["volume", "inspect", volume["Name"]]:
            output = json.dumps([volume]).encode()
        else:
            raise AssertionError(f"unexpected readback command: {command}")
        stdout.write(output)
        readback_counter["value"] += 1
        job_token = hashlib.sha256(f"readback-{readback_counter['value']}".encode()).hexdigest()[:32]
        job = {"schema": 1, "token": job_token, "operation_token": operation["token"],
               "operation": operation_label, "identity": {"pid": 1, "uid": os.getuid(),
                   "start_ticks": "1", "cmd_sha256": "a" * 64},
               "deadline": operation["cleanup_deadline"],
               "command_sha256": hashlib.sha256(json.dumps(command).encode()).hexdigest(),
               "created_at": 850.0,
               "recovery_admission_token": operation["_post_restore_recovery_admission_token"],
               "recovery_authority_sha256": operation["_post_restore_recovery_authority_sha256"]}
        restore_process.ReceiptStore(directory).write(
            f"restore-{operation['token']}-{job_token}-job.json", job)
        restore_process.ReceiptStore(directory).write(f"job-{job_token}.result.json", {"exit_code": 0})
        restore_process.ReceiptStore(directory).write(
            f"restore-{operation['token']}-{job_token}-result.json", {
                "operation": operation_label, "exit_code": 0,
                "command_sha256": job["command_sha256"]})
        return 0

    monkeypatch.setattr(restore_process, "run_command", register_readback)

    def run(directory, operation, deadline, label, command, _timeout, **_kwargs):
        restore_process._validate_command(operation, command)
        resources["commands"].append(command)
        operation_label = "post-restore-recovery-" + label
        job_token = hashlib.sha256(f"remove-{len(resources['commands'])}".encode()).hexdigest()[:32]
        job = {"schema": 1, "token": job_token, "operation_token": operation["token"],
               "operation": operation_label, "identity": {"pid": 1, "uid": os.getuid(),
                   "start_ticks": "1", "cmd_sha256": "b" * 64},
               "deadline": deadline,
               "command_sha256": hashlib.sha256(json.dumps(command).encode()).hexdigest(),
               "created_at": 850.0,
               "recovery_admission_token": operation["_post_restore_recovery_admission_token"],
               "recovery_authority_sha256": operation["_post_restore_recovery_authority_sha256"]}
        restore_process.ReceiptStore(directory).write(
            f"restore-{operation['token']}-{job_token}-job.json", job)
        restore_process.ReceiptStore(directory).write(f"job-{job_token}.result.json", {"exit_code": 0})
        restore_process.ReceiptStore(directory).write(
            f"restore-{operation['token']}-{job_token}-result.json", {
                "operation": operation_label, "exit_code": 0,
                "command_sha256": job["command_sha256"]})
        if command[1:2] == ["rm"]:
            resources["container"] = False
            if interrupt_after_container:
                raise RuntimeError("simulated interruption after container removal")
        elif command[1:3] == ["volume", "rm"]:
            resources["volume"] = False
        return 0

    monkeypatch.setattr(recovery, "_run", run)
    resources["container_row"] = container
    return resources


def _write_stopped_capture(recovery_module, session_root: Path, container: dict) -> None:
    container["State"]["Status"] = "exited"
    container["State"]["StartedAt"] = "recovery-start"
    identity_sha = contract._json_digest(recovery_module._container_identity(container))
    recovery_module._write_once(session_root, "start.result.json", {
        "recovery_started_at": "recovery-start", "identity_sha256": identity_sha})
    recovery_module._write_once(session_root, "stop.result.json", {
        "container_id": container["Id"], "status": "stopped",
        "started_at": "recovery-start", "container_identity_sha256": identity_sha})


def test_orchestrated_capture_archives_before_exact_container_and_volume_retirement(tmp_path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    operation, create_result, original_snapshot = _active_failed_attempt(state)
    authority_path = _authority_for(state, operation, create_result["container_id"], "1" * 32)
    resources = _wire_recovery_mocks(monkeypatch)
    monkeypatch.setattr(recovery.restore, "read_operation", lambda _directory: operation)
    monkeypatch.setattr(recovery, "_validate_original", lambda *_args: (
        {"create": create_result}, Path("/source/archive.dump"), original_snapshot))
    authority = {"admission_token": "1" * 32, "issued_at": 800.0, "deadline": 900.0,
                 "container_id": create_result["container_id"], "volume": operation["compose"]["volume"],
                 "operation_sha256": hashlib.sha256((state / "restore-operation.json").read_bytes()).hexdigest(),
                 "failure_sha256": hashlib.sha256((state / f"restore-{operation['token']}-failure.result.json").read_bytes()).hexdigest(),
                 "cleanup_sha256": hashlib.sha256((state / f"restore-{operation['token']}-cleanup.result.json").read_bytes()).hexdigest()}
    monkeypatch.setattr(recovery, "_authority", lambda *_args: (authority, "1" * 40, "/release"))

    def capture(*args):
        session_root = args[6]
        _write_stopped_capture(recovery, session_root, resources["container_row"])
        recovery._write_once(session_root, "capture-proof.json", {"state": "stable-synthetic-readback"})
        return {"tables": {"unit_entities": {"sha256": "e" * 64}}}

    monkeypatch.setattr(recovery, "_capture_and_stop", capture)
    failure_bytes = (state / f"restore-{operation['token']}-failure.result.json").read_bytes()
    cleanup_bytes = (state / f"restore-{operation['token']}-cleanup.result.json").read_bytes()
    result = recovery.recover(state, authority_path)

    retired = state / "restore-post-restore-retired" / operation["token"]
    manifest = archive.verify_archive(retired, operation["token"])
    closure = json.loads((retired / "closure" / "closure.json").read_text())
    assert result["status"] == "failed_post_restore_retired"
    assert manifest["status"] == "failed_post_restore_retired"
    assert closure["container_absent"] and closure["volume_absent"]
    assert not (state / "restore-operation.json").exists()
    assert not (state / f"restore-{operation['token']}-failure.result.json").exists()
    manifest_files = {row["path"]: row for row in manifest["files"]}
    closure_names = {row["path"] for row in closure["closure_receipts"]}
    closure_jobs = [json.loads((retired / "closure" / "evidence" / name).read_text())
                    for name in closure_names if name.endswith("-job.json")]
    readback_jobs = [job for job in closure_jobs
                     if job["operation"] == "post-restore-recovery-readback"]
    assert readback_jobs
    for job in readback_jobs:
        assert f"restore-{operation['token']}-{job['token']}-job.json" in closure_names
        assert f"restore-{operation['token']}-{job['token']}-result.json" in closure_names
        assert f"job-{job['token']}.result.json" in closure_names
    assert (retired / "evidence" / f"restore-{operation['token']}-failure.result.json").read_bytes() == failure_bytes
    assert (retired / "evidence" / f"restore-{operation['token']}-cleanup.result.json").read_bytes() == cleanup_bytes
    assert f"restore-{operation['token']}-snapshot.result.json" in manifest["absent_original_results"]
    assert resources["commands"] == [
        ["docker", "rm", create_result["container_id"]],
        ["docker", "volume", "rm", operation["compose"]["volume"]],
    ]
    assert "restore-operation.json" in manifest_files


def test_real_run_monitor_binds_readback_to_verified_recovery_started_at(tmp_path, monkeypatch):
    (tmp_path / "registry.json").write_text("{}")
    seen = {}
    operation = {"token": "f" * 32, "deadline": 100.0, "cleanup_deadline": 100.0,
        "compose": {"volume": "restore-volume-failed-attempt"},
        "finalization": {"containers": []},
        "_cleanup_recovery_container_id": "c" * 64,
        "_post_restore_recovery": True,
        "_post_restore_recovery_started_at": "new-recovery-start"}
    monkeypatch.setattr(restore_cleanup, "registered_host_readback", lambda *_args: nullcontext())
    monkeypatch.setattr(recovery.restore, "_verify_host",
        lambda *_args, **kwargs: seen.update(started_at=kwargs.get("post_restore_recovery_started_at")))

    def run_command(_directory, scoped, command, _timeout, *, monitor, **_kwargs):
        restore_process._validate_command(scoped, command)
        monitor()
        return 0

    monkeypatch.setattr(restore_process, "run_command", run_command)

    assert recovery._run(tmp_path, operation, 100.0, "remove-container",
                         ["docker", "rm", "c" * 64], 45) == 0
    assert seen["started_at"] == "new-recovery-start"


def test_retry_after_stopped_partial_capture_preserves_prior_session_before_retirement(tmp_path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    operation, create_result, original_snapshot = _active_failed_attempt(state)
    authority_path = _authority_for(state, operation, create_result["container_id"], "4" * 32)
    resources = _wire_recovery_mocks(monkeypatch)
    monkeypatch.setattr(recovery.restore, "read_operation", lambda _directory: operation)
    monkeypatch.setattr(recovery, "_validate_original", lambda *_args: (
        {"create": create_result}, Path("/source/archive.dump"), original_snapshot))
    authority = {"admission_token": "4" * 32, "issued_at": 800.0, "deadline": 900.0,
                 "container_id": create_result["container_id"], "volume": operation["compose"]["volume"],
                 "operation_sha256": hashlib.sha256((state / "restore-operation.json").read_bytes()).hexdigest(),
                 "failure_sha256": hashlib.sha256((state / f"restore-{operation['token']}-failure.result.json").read_bytes()).hexdigest(),
                 "cleanup_sha256": hashlib.sha256((state / f"restore-{operation['token']}-cleanup.result.json").read_bytes()).hexdigest()}
    monkeypatch.setattr(recovery, "_authority", lambda *_args: (authority, "1" * 40, "/release"))
    recovery_parent = state / "restore-post-restore-recovery"
    token_root = recovery_parent / operation["token"]
    prior_session = token_root / ("5" * 32)
    recovery_parent.mkdir(mode=0o700)
    token_root.mkdir(mode=0o700)
    _write(prior_session / "start.intent.json", b'{"status":"started_before_interruption"}')
    _write(prior_session / "capture" / "partial-table.jsonl", b'{"id":1}\n')

    def capture(*args):
        session_root = args[6]
        _write_stopped_capture(recovery, session_root, resources["container_row"])
        recovery._write_once(session_root, "capture-proof.json", {"state": "stable-synthetic-readback"})
        return {"tables": {"unit_entities": {"sha256": "e" * 64}}}

    monkeypatch.setattr(recovery, "_capture_and_stop", capture)

    result = recovery.recover(state, authority_path)

    retired = state / "restore-post-restore-retired" / operation["token"]
    manifest = archive.verify_archive(retired, operation["token"])
    files = {row["path"] for row in manifest["files"]}
    assert result["status"] == "failed_post_restore_retired"
    assert "post-restore-recovery/55555555555555555555555555555555/start.intent.json" in files
    assert "post-restore-recovery/55555555555555555555555555555555/capture/partial-table.jsonl" in files
    assert resources["commands"] == [
        ["docker", "rm", create_result["container_id"]],
        ["docker", "volume", "rm", operation["compose"]["volume"]],
    ]


def test_archive_resumption_finishes_volume_removal_after_container_was_removed(tmp_path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    operation, create_result, original_snapshot = _active_failed_attempt(state)
    first_authority_path = _authority_for(state, operation, create_result["container_id"], "2" * 32)
    resources = _wire_recovery_mocks(monkeypatch, interrupt_after_container=True)
    monkeypatch.setattr(recovery.restore, "read_operation", lambda _directory: operation)
    monkeypatch.setattr(recovery, "_validate_original", lambda *_args: (
        {"create": create_result}, Path("/source/archive.dump"), original_snapshot))

    def authority_for(path, *_args):
        nonce = path.stem[-32:]
        return ({"admission_token": nonce, "issued_at": 800.0, "deadline": 900.0,
                 "container_id": create_result["container_id"], "volume": operation["compose"]["volume"],
                 "operation_sha256": hashlib.sha256((state / "restore-operation.json").read_bytes()).hexdigest(),
                 "failure_sha256": hashlib.sha256((state / f"restore-{operation['token']}-failure.result.json").read_bytes()).hexdigest(),
                 "cleanup_sha256": hashlib.sha256((state / f"restore-{operation['token']}-cleanup.result.json").read_bytes()).hexdigest()},
                "1" * 40, "/release")

    monkeypatch.setattr(recovery, "_authority", authority_for)
    def capture(*args):
        _write_stopped_capture(recovery, args[6], resources["container_row"])
        return {"tables": {"unit_entities": {"sha256": "e" * 64}}}

    monkeypatch.setattr(recovery, "_capture_and_stop", capture)
    with pytest.raises(RuntimeError, match="simulated interruption"):
        recovery.recover(state, first_authority_path)

    assert not resources["container"] and resources["volume"]
    second_authority_path = _authority_for(state, operation, create_result["container_id"], "3" * 32)
    result = recovery.recover(state, second_authority_path)

    retired = state / "restore-post-restore-retired" / operation["token"]
    assert result["status"] == "failed_post_restore_retired"
    assert not resources["container"] and not resources["volume"]
    assert archive.verify_archive(retired, operation["token"])["status"] == "failed_post_restore_retired"
    assert (retired / "closure" / "closure-seal.json").is_file()
    assert (retired / "closure" / "evidence" /
            "resume-33333333333333333333333333333333-authority.json").is_file()
    closure = json.loads((retired / "closure" / "closure.json").read_text())
    closure_names = {row["path"] for row in closure["closure_receipts"]}
    assert any(name.endswith("-job.json") and json.loads(
        (retired / "closure" / "evidence" / name).read_text()).get("operation")
        == "post-restore-recovery-readback" for name in closure_names)
    assert resources["commands"] == [
        ["docker", "rm", create_result["container_id"]],
        ["docker", "volume", "rm", operation["compose"]["volume"]],
    ]
    assert not (state / "restore-operation.json").exists()
