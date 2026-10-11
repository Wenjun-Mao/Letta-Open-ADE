import hashlib
import json
import time
import uuid
from pathlib import Path

import pytest

from workflows.evals.hindsight_memory_probe import (
    host_guard,
    restore,
    restore_cleanup_recovery,
    restore_cleanup_recovery_history,
    restore_database,
    restore_process,
    restore_retirement_archive,
)
from workflows.evals.hindsight_memory_probe.campaign_clock import DEADLINE
from workflows.evals.hindsight_memory_probe.receipts import ReceiptStore
from workflows.evals.hindsight_memory_probe.restore_retirement_archive import digest_file


def test_cleanup_recovery_command_allowlist_is_bound_to_exact_container_and_volume():
    operation = {"token": "a" * 32, "compose": {"volume": "ade-hindsight-restore-aaaaaaaaaaaaaaaa_data"},
                 "_cleanup_recovery_container_id": "b" * 64}
    restore_process._validate_command(operation, ["docker", "stop", "--time", "20", "b" * 64])
    restore_process._validate_command(operation, ["docker", "volume", "rm", operation["compose"]["volume"]])
    with pytest.raises(RuntimeError, match="cleanup_recovery_command_not_allowed"):
        restore_process._validate_command(operation, ["docker", "stop", "--time", "20", "c" * 64])
    with pytest.raises(RuntimeError, match="cleanup_recovery_command_not_allowed"):
        restore_process._validate_command(operation, ["docker", "compose", "up", "-d"])
    with pytest.raises(RuntimeError, match="cleanup_recovery_command_not_allowed"):
        restore_process._validate_command(operation, ["docker", "exec", "-i", "b" * 64, "pg_restore"])


def test_failed_create_history_requires_sealed_byte_exact_files(tmp_path):
    token = "d" * 32
    tmp_path.chmod(0o700)
    root = tmp_path / "restore-cleanup-recovered" / token
    (root / "evidence").mkdir(parents=True)
    for directory in (root.parent, root, root / "evidence"):
        directory.chmod(0o700)
    evidence = root / "evidence" / "original-failure.json"
    evidence.write_bytes(b'{"original":true}\n')
    manifest = {"schema": 1, "kind": "failed_create_cleaned", "token": token,
                "operation_sha256": "e" * 64, "files": [{"path": "original-failure.json",
                "sha256": digest_file(evidence), "bytes": evidence.stat().st_size}], "created_at": 1}
    ReceiptStore(root).write("recovery.json", manifest)
    (root / "recovery.json").chmod(0o400)
    ReceiptStore(root).write("recovery-seal.json", {"schema": 1, "token": token,
        "sha256": digest_file(root / "recovery.json")})
    (root / "recovery-seal.json").chmod(0o400)

    with pytest.raises(RuntimeError):
        restore_cleanup_recovery_history.validate_history(tmp_path)
    with pytest.raises(RuntimeError):
        restore_cleanup_recovery.prepare_next_attempt(tmp_path)


def _public_recovery_case(tmp_path, monkeypatch):
    state = tmp_path / "receipts"
    state.mkdir(mode=0o700)
    token, parent, create_job_token = "a" * 32, "b" * 32, "c" * 32
    release = "/immutable/release-" + "d" * 40
    source_root = state / "finalization" / parent
    source_root.mkdir(parents=True)
    archive_path = source_root / "candidate.dump"
    archive_path.write_bytes(b"PGDMP synthetic candidate")
    snapshot_path = source_root / "canonical-snapshot.json"
    snapshot_path.write_text('{"canonical":"snapshot"}\n')
    selection_path = state / "selection.json"
    selection_path.write_text('{"selection":"frozen"}\n')
    dump_result_path = state / f"finalize-{parent}-dump-result.json"
    dump_result_path.write_text('{"dump":"result"}\n')
    registry = {"registry_sha256": "1" * 64, "release": release, "baseline": []}
    (state / "registry.json").write_text(json.dumps(registry) + "\n")
    epoch = {"sha256": "2" * 64, "release": release}
    restart_selection = {"sha256": "3" * 64, "ref": "frozen"}
    restart_readback = {"sha256": "4" * 64, "ref": "completed"}
    main_admission = {"token": parent, "containers": [], "restart_selection": restart_selection,
                      "restart_readback": restart_readback}
    evidence = {"archive": archive_path, "dump": {"bytes": archive_path.stat().st_size},
                "snapshot_path": snapshot_path, "selection_path": selection_path,
                "finalized": {"dump_result": dump_result_path.name}}
    image = "ade-hindsight-probe-db:" + "d" * 40
    image_id = "sha256:" + "e" * 64
    compose = restore_database.write_compose(state / "restore" / token, token, image, image_id)
    volume_name = compose["volume"]
    container = {
        "Id": "f" * 64, "Image": image_id, "RestartCount": 0,
        "State": {"StartedAt": "2026-10-11T12:51:11Z", "Status": "running", "OOMKilled": False},
        "Config": {"Image": image, "Env": ["POSTGRES_DB=hindsight_probe", "POSTGRES_USER=hindsight_probe"],
                   "Labels": {"ade.hindsight.restore.token": token,
                              "com.docker.compose.project": compose["project"],
                              "com.docker.compose.service": "db",
                              "com.docker.compose.project.config_files": compose["path"],
                              "com.docker.compose.project.working_dir": str(Path(compose["path"]).parent)}},
        "HostConfig": {"NetworkMode": "none", "Memory": restore_database.RESTORE_MEMORY,
                       "NanoCpus": int(restore_database.RESTORE_CPU * 1_000_000_000)},
        "NetworkSettings": {"Ports": {}},
        "Mounts": [{"Type": "volume", "Name": volume_name, "Source": "/docker/volumes/" + volume_name,
                    "Destination": restore_database.DATA_PATH, "Driver": "local", "Mode": "z", "RW": True,
                    "Propagation": ""}],
    }
    volume = {"Name": volume_name, "Driver": "local", "Scope": "local", "Options": None,
              "Mountpoint": "/docker/volumes/" + volume_name, "CreatedAt": "2026-10-11T12:51:10Z",
              "Labels": {"com.docker.compose.project": compose["project"],
                         "com.docker.compose.volume": "data", "ade.hindsight.restore.token": token}}
    operation = {
        "schema": 1, "status": "admitted", "token": token,
        "registry_sha256": registry["registry_sha256"], "epoch_sha256": epoch["sha256"],
        "parent_finalization_token": parent, "parent_stopped_epoch_sha256": epoch["sha256"],
        "release_path": release, "deadline": time.time() - 120,
        "cleanup_deadline": time.time() - 60, "hard_deadline": DEADLINE,
        "finalization": {"containers": [], "restart_selection": restart_selection,
                         "restart_readback": restart_readback},
        "archive": {"path": str(archive_path), "sha256": restore_retirement_archive.digest_file(archive_path),
                    "bytes": archive_path.stat().st_size,
                    "dump_result_sha256": restore_retirement_archive.digest_file(dump_result_path)},
        "snapshot": {"path": str(snapshot_path), "sha256": restore_retirement_archive.digest_file(snapshot_path),
                     "root": str(source_root)},
        "selection": {"path": str(selection_path), "sha256": restore_retirement_archive.digest_file(selection_path),
                      "restart_proof_sha256": restart_readback["sha256"]},
        "compose": compose, "restore_root": str(state / "restore" / token), "state_directory": str(state),
    }
    operation_path = state / "restore-operation.json"
    operation_path.write_text(json.dumps(operation, sort_keys=True) + "\n")
    operation_path.chmod(0o600)
    ReceiptStore(state).write("restore-operation-seal.json", {
        "schema": 1, "token": token, "sha256": restore_retirement_archive.digest_file(operation_path)})
    failure_path = state / f"restore-{token}-failure.result.json"
    failure = {"token": token, "status": "failed", "stage": "create",
               "reason": "restore_unowned_container_detected"}
    ReceiptStore(state).write(failure_path.name, failure)
    (state / f"restore-{token}-create.intent.json").write_text(json.dumps({
        "token": token, "compose_sha256": compose["sha256"], "project": compose["project"],
        "volume": volume_name}) + "\n")
    (state / f"restore-{token}-create.intent.json").chmod(0o600)
    (state / f"restore-{token}-controller-{"9" * 32}.json").write_text(
        json.dumps({"token": token, "identity": {"pid": 99999}}))
    create_command = ["docker", "compose", "--project-name", compose["project"], "-f", compose["path"],
                      "up", "-d", "--pull", "never", "db"]
    create_registration = {"schema": 1, "token": create_job_token, "operation_token": token,
                           "operation": "compose-create", "command_sha256": hashlib.sha256(
                               json.dumps(create_command).encode()).hexdigest(),
                           "identity": {"pid": 88888}}
    (state / f"restore-{token}-{create_job_token}-job.json").write_text(json.dumps(create_registration) + "\n")
    (state / f"job-{create_job_token}.result.json").write_text('{"exit_code":0}\n')
    # The real failure shape has no wrapper result and no create.result receipt.
    diagnosis = {
        "schema": 1, "kind": "created_but_unpublished_cleanup_only", "token": token,
        "operation_sha256": restore_retirement_archive.digest_file(operation_path),
        "failure_sha256": restore_retirement_archive.digest_file(failure_path),
        "create_intent_sha256": restore_retirement_archive.digest_file(state / f"restore-{token}-create.intent.json"),
        "create_job_token": create_job_token,
        "create_job_registration_sha256": restore_retirement_archive.digest_file(
            state / f"restore-{token}-{create_job_token}-job.json"),
        "create_child_result_sha256": restore_retirement_archive.digest_file(state / f"job-{create_job_token}.result.json"),
        "create_wrapper_result_absent": True, "container_id": container["Id"],
        "container_started_at": container["State"]["StartedAt"], "image_id": container["Image"],
        "container_identity_sha256": restore_cleanup_recovery._digest(
            restore_cleanup_recovery._container_identity(container)),
        "volume": volume_name,
        "volume_identity_sha256": hashlib.sha256(json.dumps(
            restore_cleanup_recovery._volume_identity(volume), sort_keys=True).encode()).hexdigest(),
        "controller_gone": True, "processes_gone": True, "main_stopped": True,
        "baseline_unchanged": True,
    }
    diagnosis_path = tmp_path / "diagnosis.json"
    diagnosis_path.write_text(json.dumps(diagnosis, sort_keys=True) + "\n")
    diagnosis_path.chmod(0o400)
    host_state = {"container": container, "volume": volume}
    monkeypatch.setattr(restore, "_load_main", lambda _state: (registry, epoch, main_admission, evidence))
    monkeypatch.setattr(restore.epochs, "effective_registry", lambda _directory, value: value)
    monkeypatch.setattr(host_guard, "containers", lambda: [host_state["container"]] if host_state["container"] else [])
    monkeypatch.setattr(host_guard, "host_sample", lambda *_args: {
        "memory_available": 8 * host_guard.GIB, "cpus": 2, "disk_free": 50 * host_guard.GIB})
    monkeypatch.setattr(host_guard, "identity_matches", lambda _identity: False)
    monkeypatch.setattr(host_guard, "tagged_processes", lambda *_args: [])

    real_verify_compose = restore_database.verify_compose
    monkeypatch.setattr(restore_database, "verify_compose", lambda _operation: None)
    interrupted = {"stop": True}

    def run_registered(directory, operation_arg, command, timeout, *, operation_label, monitor,
                       stdout=None, **_kwargs):
        process_token = uuid.uuid4().hex
        deadline = restore_process.command_deadline(operation_arg, timeout, operation_label, time.time())
        registration = {"schema": 1, "token": process_token, "operation_token": token,
                       "operation": operation_label,
                       "command_sha256": hashlib.sha256(json.dumps(command).encode()).hexdigest(),
                       "identity": {"pid": 77777}, "deadline": deadline, "created_at": time.time()}
        (directory / f"restore-{token}-{process_token}-job.json").write_text(json.dumps(registration) + "\n")
        if operation_label in restore_process.READ_ONLY_HOST_OPERATIONS:
            assert operation_arg["cleanup_deadline"] > operation_arg["deadline"]
            assert operation_arg["cleanup_deadline"] > time.time()
        output = b""
        if command == ["docker", "ps", "-aq", "--no-trunc"]:
            output = ((host_state["container"]["Id"] + "\n").encode()
                      if host_state["container"] else b"")
        elif command[:3] == ["docker", "volume", "ls"]:
            output = ((volume_name + "\n").encode() if host_state["volume"] else b"")
        elif "volume=" in " ".join(command):
            output = b""
        elif command[1:3] == ["volume", "inspect"]:
            output = json.dumps([host_state["volume"]]).encode()
        elif command[1:2] == ["inspect"]:
            output = json.dumps([host_state["container"]]).encode()
        if stdout is not None:
            stdout.write(output)
        if command[1] == "stop":
            host_state["container"]["State"]["Status"] = "exited"
        elif command[1] == "rm":
            host_state["container"] = None
        elif command[1:3] == ["volume", "rm"]:
            host_state["volume"] = None
        (directory / f"job-{process_token}.result.json").write_text('{"exit_code":0}\n')
        (directory / f"restore-{token}-{process_token}-result.json").write_text(json.dumps({
            "operation": operation_label, "exit_code": 0,
            "command_sha256": registration["command_sha256"]}) + "\n")
        if operation_label == "cleanup-recovery-stop" and interrupted["stop"]:
            interrupted["stop"] = False
            raise RuntimeError("synthetic interruption after Docker success")
        return 0

    monkeypatch.setattr(restore_process, "run_command", run_registered)
    main_admission["release_path"] = release
    return (state, diagnosis_path, host_state, operation_path, failure_path, diagnosis, main_admission,
            real_verify_compose, interrupted)


def test_public_recovery_resumes_exact_child_success_with_missing_wrapper_and_preserves_history(tmp_path, monkeypatch):
    state, diagnosis, host_state, operation_path, failure_path, original_diagnosis, _main, _verify_compose, _interrupt = (
        _public_recovery_case(tmp_path, monkeypatch))
    original = {path.name: path.read_bytes() for path in
                (operation_path, failure_path, state / ("restore-" + "a" * 32 + "-create.intent.json"),
                 state / ("restore-" + "a" * 32 + "-" + "c" * 32 + "-job.json"),
                 state / ("job-" + "c" * 32 + ".result.json"))}

    with pytest.raises(RuntimeError, match="synthetic interruption"):
        restore_cleanup_recovery.recover(state, diagnosis)
    assert host_state["container"]["State"]["Status"] == "exited"
    assert not (state / ("restore-" + "a" * 32 + "-" + "c" * 32 + "-result.json")).exists()

    result = restore_cleanup_recovery.recover(state, diagnosis)

    assert result["status"] == "failed_create_cleaned"
    assert host_state == {"container": None, "volume": None}
    root = state / "restore-cleanup-recovered" / ("a" * 32)
    restore_cleanup_recovery_history.validate_history(state)
    evidence = root / "evidence"
    assert (evidence / "diagnosis.json").read_bytes() == diagnosis.read_bytes()
    for name, content in original.items():
        assert (evidence / name).read_bytes() == content
    assert original_diagnosis["create_wrapper_result_absent"] is True
    assert not (state / "restore-operation.json").exists()


@pytest.mark.parametrize("mutation, expected", [
    ("active-controller", "restore_cleanup_recovery_controller_active"),
    ("active-process", "restore_cleanup_recovery_job_set_invalid"),
    ("foreign-container", "restore_container_identity_ambiguous"),
    ("success-receipt", "restore_cleanup_recovery_successful_result_rejected"),
    ("create-job-hash", "restore_cleanup_recovery_create_proof_invalid"),
    ("compose-hash", "restore_compose_config_changed"),
    ("source-bytes", "restore_operation_archive_source_mismatch"),
    ("container-image", "restore_container_identity_changed"),
    ("volume-identity", "restore_cleanup_recovery_resource_identity_invalid"),
])
def test_public_recovery_rejects_unproven_or_changed_state(tmp_path, monkeypatch, mutation, expected):
    state, diagnosis, host_state, operation_path, _failure, _diagnosis, _main, verify_compose, _interrupt = (
        _public_recovery_case(tmp_path, monkeypatch))
    token = "a" * 32
    if mutation == "active-controller":
        monkeypatch.setattr(host_guard, "identity_matches", lambda _identity: True)
    elif mutation == "active-process":
        monkeypatch.setattr(host_guard, "tagged_processes", lambda _token: [{"pid": 77777}])
    elif mutation == "foreign-container":
        foreign = dict(host_state["container"])
        foreign["Id"] = "9" * 64
        monkeypatch.setattr(host_guard, "containers", lambda: [host_state["container"], foreign])
    elif mutation == "success-receipt":
        (state / f"restore-{token}-result.json").write_text('{"status":"success"}\n')
    elif mutation == "create-job-hash":
        path = state / f"restore-{token}-{'c' * 32}-job.json"
        job = json.loads(path.read_text())
        job["command_sha256"] = "0" * 64
        path.write_text(json.dumps(job) + "\n")
    elif mutation == "compose-hash":
        compose = json.loads(operation_path.read_text())["compose"]
        Path(compose["path"]).write_text("services: {}\n")
        monkeypatch.setattr(restore_database, "verify_compose", verify_compose)
    elif mutation == "source-bytes":
        operation = json.loads(operation_path.read_text())
        Path(operation["archive"]["path"]).write_bytes(b"changed source")
    elif mutation == "container-image":
        host_state["container"]["Image"] = "sha256:" + "0" * 64
    elif mutation == "volume-identity":
        host_state["volume"]["CreatedAt"] = "2026-10-11T12:52:10Z"

    with pytest.raises(RuntimeError, match=expected):
        restore_cleanup_recovery.recover(state, diagnosis)


@pytest.mark.parametrize("kind", ["readback", "cleanup"])
def test_public_recovery_rejects_expired_recovery_admission(tmp_path, monkeypatch, kind):
    state, diagnosis_path, host_state, operation_path, _failure, diagnosis, _main, _verify_compose, _interrupt = (
        _public_recovery_case(tmp_path, monkeypatch))
    token = diagnosis["token"]
    now = time.time()
    operation_hash = digest_file(operation_path)
    diagnosis_hash = digest_file(diagnosis_path)
    if kind == "readback":
        name = f"restore-{token}-cleanup-recovery-readback-admission"
        value = {"schema": 1, "kind": "read_only_restore_cleanup_recovery", "token": token,
                 "operation_sha256": operation_hash, "diagnosis_sha256": diagnosis_hash,
                 "deadline": now - 1, "commands": ["docker ps", "docker inspect", "docker volume ls",
                                                        "docker volume inspect"],
                 "created_at": now - 601}
    else:
        name = f"restore-{token}-cleanup-recovery-admission"
        value = {"schema": 1, "kind": "restore_cleanup_only_recovery", "token": token,
                 "operation_sha256": operation_hash, "diagnosis_sha256": diagnosis_hash,
                 "container_identity": restore_cleanup_recovery._container_identity(host_state["container"]),
                 "volume_identity": restore_cleanup_recovery._volume_identity(host_state["volume"]),
                 "deadline": now - 1, "created_at": now - 601}
    admission_path = state / f"{name}.json"
    ReceiptStore(state).write(admission_path.name, value)
    admission_path.chmod(0o400)
    seal_path = state / f"{name}.seal.json"
    ReceiptStore(state).write(seal_path.name, {"schema": 1, "token": token,
                                               "sha256": digest_file(admission_path)})
    seal_path.chmod(0o400)
    expected = ("restore_cleanup_recovery_readback_deadline_elapsed" if kind == "readback"
                else "restore_cleanup_recovery_deadline_elapsed")
    with pytest.raises(RuntimeError, match=expected):
        restore_cleanup_recovery.recover(state, diagnosis_path)


@pytest.mark.parametrize("kind, deadline, created_at", [
    ("readback", float("nan"), time.time()),
    ("cleanup", float("inf"), time.time()),
    ("readback", time.time() + 1000, time.time()),
    ("cleanup", time.time() + 1000, time.time()),
])
def test_public_recovery_rejects_nonfinite_or_oversized_admission(tmp_path, monkeypatch, kind, deadline, created_at):
    state, diagnosis_path, host_state, operation_path, _failure, diagnosis, _main, _verify_compose, _interrupt = (
        _public_recovery_case(tmp_path, monkeypatch))
    token = diagnosis["token"]
    operation_hash, diagnosis_hash = digest_file(operation_path), digest_file(diagnosis_path)
    if kind == "readback":
        name = f"restore-{token}-cleanup-recovery-readback-admission"
        value = {"schema": 1, "kind": "read_only_restore_cleanup_recovery", "token": token,
                 "operation_sha256": operation_hash, "diagnosis_sha256": diagnosis_hash,
                 "deadline": deadline, "commands": ["docker ps", "docker inspect", "docker volume ls",
                                                       "docker volume inspect"], "created_at": created_at}
    else:
        name = f"restore-{token}-cleanup-recovery-admission"
        value = {"schema": 1, "kind": "restore_cleanup_only_recovery", "token": token,
                 "operation_sha256": operation_hash, "diagnosis_sha256": diagnosis_hash,
                 "container_identity": restore_cleanup_recovery._container_identity(host_state["container"]),
                 "volume_identity": restore_cleanup_recovery._volume_identity(host_state["volume"]),
                 "deadline": deadline, "created_at": created_at}
    admission_path = state / f"{name}.json"
    admission_path.write_text(json.dumps(value, allow_nan=True, sort_keys=True) + "\n")
    admission_path.chmod(0o400)
    seal_path = state / f"{name}.seal.json"
    ReceiptStore(state).write(seal_path.name, {"schema": 1, "token": token,
                                               "sha256": digest_file(admission_path)})
    seal_path.chmod(0o400)
    error = ("restore_cleanup_recovery_readback_admission_invalid" if kind == "readback"
             else "restore_cleanup_recovery_admission_invalid")
    with pytest.raises(RuntimeError, match=error):
        restore_cleanup_recovery.recover(state, diagnosis_path)


@pytest.mark.parametrize("stage", ["restore", "snapshot", "compare"])
def test_public_recovery_rejects_later_progress_intent(tmp_path, monkeypatch, stage):
    state, diagnosis_path, *_ = _public_recovery_case(tmp_path, monkeypatch)
    (state / f"restore-{'a' * 32}-{stage}.intent.json").write_text("{}\n")
    with pytest.raises(RuntimeError, match="restore_cleanup_recovery_after_create_progress_rejected"):
        restore_cleanup_recovery.recover(state, diagnosis_path)


def test_public_recovery_resumes_after_archive_seal_before_control_removal(tmp_path, monkeypatch):
    state, diagnosis_path, host_state, _operation, _failure, _diagnosis, _main, _verify_compose, stop_interrupt = (
        _public_recovery_case(tmp_path, monkeypatch))
    stop_interrupt["stop"] = False
    remove_controls = restore_cleanup_recovery_history._remove_active_sources
    monkeypatch.setattr(restore_cleanup_recovery_history, "_remove_active_sources",
                        lambda *_args: (_ for _ in ()).throw(RuntimeError("interrupted before control removal")))
    with pytest.raises(RuntimeError, match="interrupted before control removal"):
        restore_cleanup_recovery.recover(state, diagnosis_path)
    root = state / "restore-cleanup-recovered" / ("a" * 32)
    assert (root / "recovery-seal.json").is_file()
    assert (state / "restore-operation.json").is_file()
    monkeypatch.setattr(restore_cleanup_recovery_history, "_remove_active_sources", remove_controls)
    result = restore_cleanup_recovery.recover(state, diagnosis_path)
    assert result["status"] == "failed_create_cleaned"
    assert host_state == {"container": None, "volume": None}
    assert not (state / "restore-operation.json").exists()
    restore_cleanup_recovery.prepare_next_attempt(state)


def test_public_recovery_archives_already_exited_container(tmp_path, monkeypatch):
    state, diagnosis_path, host_state, _operation, _failure, _diagnosis, _main, _verify_compose, stop_interrupt = (
        _public_recovery_case(tmp_path, monkeypatch))
    stop_interrupt["stop"] = False
    host_state["container"]["State"]["Status"] = "exited"
    result = restore_cleanup_recovery.recover(state, diagnosis_path)
    assert result["status"] == "failed_create_cleaned"
    assert host_state == {"container": None, "volume": None}
    restore_cleanup_recovery_history.validate_history(state)


def test_public_recovery_resumes_manifest_published_before_seal(tmp_path, monkeypatch):
    state, diagnosis_path, host_state, _operation, _failure, _diagnosis, _main, _verify_compose, stop_interrupt = (
        _public_recovery_case(tmp_path, monkeypatch))
    stop_interrupt["stop"] = False
    write_once = restore_cleanup_recovery_history._write_once

    def interrupt_before_seal(directory, name, value):
        if directory.name == "a" * 32 and name == "recovery-seal.json":
            raise RuntimeError("interrupted between manifest and seal")
        return write_once(directory, name, value)

    monkeypatch.setattr(restore_cleanup_recovery_history, "_write_once", interrupt_before_seal)
    with pytest.raises(RuntimeError, match="interrupted between manifest and seal"):
        restore_cleanup_recovery.recover(state, diagnosis_path)
    root = state / "restore-cleanup-recovered" / ("a" * 32)
    assert (root / "recovery.json").is_file()
    assert not (root / "recovery-seal.json").exists()
    assert (state / "restore-operation.json").is_file()
    with pytest.raises(RuntimeError):
        restore_cleanup_recovery.prepare_next_attempt(state)

    monkeypatch.setattr(restore_cleanup_recovery_history, "_write_once", write_once)
    result = restore_cleanup_recovery.recover(state, diagnosis_path)
    assert result["status"] == "failed_create_cleaned"
    assert (root / "recovery-seal.json").is_file()
    assert not (state / "restore-operation.json").exists()
    assert host_state == {"container": None, "volume": None}
    restore_cleanup_recovery_history.validate_history(state)
    restore_cleanup_recovery.prepare_next_attempt(state)


def test_resealed_wrong_command_history_blocks_next_attempt(tmp_path, monkeypatch):
    state, diagnosis_path, _host_state, _operation, _failure, _diagnosis, _main, _verify_compose, stop_interrupt = (
        _public_recovery_case(tmp_path, monkeypatch))
    stop_interrupt["stop"] = False
    restore_cleanup_recovery.recover(state, diagnosis_path)
    root = state / "restore-cleanup-recovered" / ("a" * 32)
    relative = f"restore-{'a' * 32}-cleanup-recovery-remove-volume.intent.json"
    evidence_path = root / "evidence" / relative
    evidence_path.chmod(0o600)
    intent = json.loads(evidence_path.read_text())
    intent["command"] = ["docker", "volume", "rm", "unrelated-volume"]
    evidence_path.write_text(json.dumps(intent, sort_keys=True) + "\n")
    evidence_path.chmod(0o400)

    manifest_path = root / "recovery.json"
    manifest_path.chmod(0o600)
    manifest = json.loads(manifest_path.read_text())
    result_relative = f"restore-{'a' * 32}-cleanup-recovery-remove-volume.result.json"
    result_path = root / "evidence" / result_relative
    result_path.chmod(0o600)
    result = json.loads(result_path.read_text())
    result["intent_sha256"] = digest_file(evidence_path)
    result_path.write_text(json.dumps(result, sort_keys=True) + "\n")
    result_path.chmod(0o400)
    for file_path, file_relative in ((evidence_path, relative), (result_path, result_relative)):
        row = next(row for row in manifest["files"] if row["path"] == file_relative)
        row["sha256"] = digest_file(file_path)
        row["bytes"] = file_path.stat().st_size
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n")
    manifest_path.chmod(0o400)
    seal_path = root / "recovery-seal.json"
    seal_path.chmod(0o600)
    seal_path.write_text(json.dumps({"schema": 1, "token": "a" * 32,
                                     "sha256": digest_file(manifest_path)}, sort_keys=True) + "\n")
    seal_path.chmod(0o400)
    with pytest.raises(RuntimeError, match="restore_cleanup_recovery_history_command_scope_invalid"):
        restore_cleanup_recovery.prepare_next_attempt(state)
