"""Registration receipt consumers and failed-before-create restore retirement."""

import hashlib
import json
from contextlib import contextmanager, nullcontext
from types import SimpleNamespace

import pytest

from workflows.evals.hindsight_memory_probe import (
    host_guard,
    restore,
    restore_cleanup,
    restore_database,
    restore_process,
    restore_retirement,
    restore_retirement_archive,
)
from workflows.evals.hindsight_memory_probe.campaign_clock import DEADLINE, WORK_CUTOFF


def _retirement_case(tmp_path, monkeypatch, *, changed=None):
    state = tmp_path / "receipts"
    state.mkdir(mode=0o700)
    token = "9" * 32
    parent = "8" * 32
    release = "/release/" + "a" * 40
    archive_path = state / "finalization" / parent / "candidate.dump"
    archive_path.parent.mkdir(parents=True)
    archive_path.write_bytes(b"pgdump")
    snapshot_path = state / "snapshot.json"
    snapshot_path.write_text('{"source":"unchanged"}\n')
    selection_path = state / "selection.json"
    selection_path.write_text('{"selection":"frozen"}\n')
    dump_result = state / "dump-result.json"
    dump_result.write_bytes(b"dump-result")
    restart = {"sha256": "d" * 64}
    registry = {"registry_sha256": "b" * 64}
    epoch = {"sha256": "c" * 64, "release": release}
    admission = {
        "token": parent,
        "containers": [],
        "restart_selection": {"ref": "selection"},
        "restart_readback": restart,
    }
    evidence = {
        "archive": archive_path,
        "dump": {"bytes": archive_path.stat().st_size},
        "snapshot_path": snapshot_path,
        "selection_path": selection_path,
        "finalized": {"dump_result": dump_result.name},
    }
    operation = {
        "schema": 1,
        "token": token,
        "registry_sha256": registry["registry_sha256"],
        "epoch_sha256": epoch["sha256"],
        "parent_finalization_token": parent,
        "parent_stopped_epoch_sha256": epoch["sha256"],
        "release_path": release,
        "deadline": WORK_CUTOFF - 200,
        "cleanup_deadline": WORK_CUTOFF - 100,
        "hard_deadline": DEADLINE,
        "archive": {
            "path": str(archive_path),
            "sha256": restore_retirement_archive.digest_file(archive_path),
            "bytes": archive_path.stat().st_size,
            "dump_result_sha256": restore_retirement_archive.digest_file(dump_result),
        },
        "snapshot": {
            "path": str(snapshot_path),
            "sha256": restore_retirement_archive.digest_file(snapshot_path),
            "root": str(archive_path.parent),
        },
        "selection": {
            "path": str(selection_path),
            "sha256": restore_retirement_archive.digest_file(selection_path),
            "restart_proof_sha256": restart["sha256"],
        },
        "finalization": {
            "containers": admission["containers"],
            "restart_selection": admission["restart_selection"],
            "restart_readback": admission["restart_readback"],
        },
        "compose": {"project": "ade-hindsight-restore-" + token[:16]},
    }
    if changed == "operation_path":
        operation["snapshot"]["path"] = str(state / "different-snapshot.json")
        (state / "different-snapshot.json").write_text(snapshot_path.read_text())
    if changed == "epoch":
        operation["epoch_sha256"] = "0" * 64
    operation_path = state / "restore-operation.json"
    operation_path.write_text(json.dumps(operation))
    (state / "restore-operation-seal.json").write_text(
        json.dumps(
            {
                "token": token,
                "sha256": restore_retirement_archive.digest_file(operation_path),
            }
        )
    )
    failure = state / f"restore-{token}-failure.result.json"
    failure.write_text(
        json.dumps(
            {
                "token": token,
                "status": "failed",
                "stage": "controller-start",
                "reason": "restore_controller_failed",
            }
        )
    )
    failure.chmod(0o600)
    controller_token = "1" * 32
    controller = state / f"restore-{token}-controller-{controller_token}.json"
    controller.write_text(json.dumps({"token": token, "identity": {"pid": 42}}))
    producer_operations = {
        restore_process.IDENTITY_READBACK,
        restore_process.IDENTITY_LIST_READBACK,
        restore_process.OPERATOR_READBACK,
        restore_process.OPERATOR_LIST_READBACK,
    }
    assert producer_operations == restore_process.READ_ONLY_HOST_OPERATIONS
    for index, label in enumerate(sorted(producer_operations), start=1):
        process_token = f"{index:032x}"
        registration = {
            "schema": 1,
            "token": process_token,
            "operation_token": token,
            "operation": label,
        }
        (state / f"restore-{token}-{process_token}-job.json").write_text(
            json.dumps(registration)
        )
        (state / f"job-{process_token}.result.json").write_text(
            json.dumps({"exit_code": 0})
        )
        (state / f"restore-{token}-{process_token}-result.json").write_text(
            json.dumps({"operation": label, "exit_code": 0})
        )
    diagnosis = {
        "schema": 1,
        "kind": "failed_before_creation",
        "failure_stage": "controller-start",
        "failure_code": "pre_creation_controller_admission_failure",
        "token": token,
        "operation_sha256": restore_retirement_archive.digest_file(operation_path),
        "failure_result_sha256": restore_retirement_archive.digest_file(failure),
        "archive_sha256": operation["archive"]["sha256"],
        "snapshot_sha256": operation["snapshot"]["sha256"],
        "selection_sha256": operation["selection"]["sha256"],
        "no_create_intent": True,
        "no_create_result": True,
        "controller_gone": True,
        "registered_processes_gone": True,
        "restore_container_absent": True,
        "restore_volume_absent": True,
        "main_stopped": True,
        "baseline_unchanged": True,
    }
    diagnosis_path = state / "diagnosis.json"
    diagnosis_path.write_text(json.dumps(diagnosis))
    diagnosis_path.chmod(0o400)
    (state / "registry.json").write_text(json.dumps(registry))
    if changed == "canonical_bytes":
        snapshot_path.write_text(snapshot_path.read_text() + " ")
    if changed == "archive_bytes":
        archive_path.write_bytes(b"changed")
    if changed == "selection_bytes":
        selection_path.write_text('{"selection":"changed"}\n')
    if changed == "success_receipt":
        (state / f"restore-{token}-result.json").write_text('{"status":"completed"}')
    if changed == "create_intent":
        (state / f"restore-{token}-create.intent.json").write_text("{}")
    if changed == "create_result":
        (state / f"restore-{token}-create.result.json").write_text(
            '{"status":"created"}'
        )
    if changed == "create_registration":
        process_token = "e" * 32
        (state / f"restore-{token}-{process_token}-job.json").write_text(
            json.dumps(
                {
                    "schema": 1,
                    "token": process_token,
                    "operation_token": token,
                    "operation": "restore-create",
                }
            )
        )
    if changed == "missing_failure":
        failure.unlink()
    if changed == "foreign_failure":
        failure.write_text(
            json.dumps(
                {"token": "7" * 32, "status": "failed", "stage": "controller-start"}
            )
        )
        diagnosis["failure_result_sha256"] = restore_retirement_archive.digest_file(
            failure
        )
        diagnosis_path.chmod(0o600)
        diagnosis_path.write_text(json.dumps(diagnosis))
        diagnosis_path.chmod(0o400)
    monkeypatch.setattr(
        restore, "_load_main", lambda _state: (registry, epoch, admission, evidence)
    )
    monkeypatch.setattr(
        restore,
        "_verify_host",
        lambda *_args, **_kwargs: (
            (_ for _ in ()).throw(RuntimeError("restore_baseline_identity_changed"))
            if changed == "baseline"
            else []
        ),
    )
    monkeypatch.setattr(
        host_guard, "identity_matches", lambda _identity: changed == "active_controller"
    )
    monkeypatch.setattr(restore.host, "tagged_processes", lambda *_args: [])
    monkeypatch.setattr(
        restore_cleanup, "retirement_readback", lambda *_args: nullcontext()
    )
    monkeypatch.setattr(restore_database, "verify_compose", lambda *_args: None)
    monkeypatch.setattr(
        restore_database, "restore_container", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        restore_database, "verify_volume", lambda *_args, **_kwargs: None
    )
    return state, diagnosis_path


def test_public_retirement_preserves_complete_failed_admission_namespace(
    tmp_path, monkeypatch
):
    state, diagnosis = _retirement_case(tmp_path, monkeypatch)

    result = restore_retirement.retire_failed_before_create(state, diagnosis)

    assert result["status"] == "retired_failed_before_creation"
    retired = state / "restore-retired" / ("9" * 32)
    manifest = restore_retirement_archive.verify_archive(retired, "9" * 32)
    names = {row["path"] for row in manifest["files"]}
    assert "restore-operation.json" in names
    assert "restore-" + "9" * 32 + "-failure.result.json" in names
    assert "diagnosis.json" in names
    file_hashes = {row["path"]: row["sha256"] for row in manifest["files"]}
    diagnosis_value = json.loads((retired / "evidence" / "diagnosis.json").read_text())
    assert (
        file_hashes["restore-" + "9" * 32 + "-failure.result.json"]
        == diagnosis_value["failure_result_sha256"]
    )
    assert not (state / "restore-operation.json").exists()
    assert not (state / ("restore-" + "9" * 32 + "-failure.result.json")).exists()


@pytest.mark.parametrize(
    "changed",
    [
        "active_controller",
        "missing_failure",
        "foreign_failure",
        "success_receipt",
        "create_intent",
        "create_result",
        "create_registration",
        "baseline",
        "archive_bytes",
        "selection_bytes",
        "canonical_bytes",
        "operation_path",
        "epoch",
    ],
)
def test_public_retirement_rejects_unqualified_or_drifted_attempts(
    tmp_path, monkeypatch, changed
):
    state, diagnosis = _retirement_case(tmp_path, monkeypatch, changed=changed)

    with pytest.raises((RuntimeError, OSError)):
        restore_retirement.retire_failed_before_create(state, diagnosis)

    assert not (state / "restore-retired" / ("9" * 32) / "retirement.json").exists()


def test_retirement_readback_has_its_own_fixed_readonly_deadline(tmp_path, monkeypatch):
    operation_path = tmp_path / "restore-operation.json"
    operation_path.write_text('{"token":"token"}')
    operation = {"token": "token", "deadline": 10, "cleanup_deadline": 20}
    admission = {
        "schema": 1,
        "kind": "read_only_restore_retirement",
        "token": "token",
        "operation_sha256": restore_retirement_archive.digest_file(operation_path),
        "deadline": WORK_CUTOFF,
        "commands": [
            "docker ps",
            "docker inspect",
            "docker volume ls",
            "docker volume inspect",
        ],
    }
    observed = {}

    @contextmanager
    def readback(_directory, value):
        observed.update(value)
        yield

    monkeypatch.setattr(restore_cleanup, "registered_host_readback", readback)
    monkeypatch.setattr(
        restore_cleanup, "time", SimpleNamespace(time=lambda: WORK_CUTOFF - 1)
    )

    with restore_cleanup.retirement_readback(tmp_path, operation, admission):
        pass

    assert observed["cleanup_deadline"] == WORK_CUTOFF
    assert operation["cleanup_deadline"] == 20


def test_retirement_archives_attempt_bytes_before_idempotent_source_removal(
    tmp_path, monkeypatch
):
    token = "e" * 32
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    operation = {
        "token": token,
        "archive": {"sha256": "a" * 64},
        "snapshot": {"sha256": "b" * 64},
        "selection": {"sha256": "c" * 64},
    }
    operation_path = state / "restore-operation.json"
    operation_path.write_text(json.dumps(operation))
    operation_hash = restore_retirement_archive.digest_file(operation_path)
    (state / "restore-operation-seal.json").write_text(
        json.dumps({"sha256": operation_hash})
    )
    failure_path = state / f"restore-{token}-failure.result.json"
    failure_path.write_text(
        json.dumps({"token": token, "status": "failed", "stage": "controller-start"})
    )
    receipt = state / f"restore-{token}-cleanup.failure.json"
    receipt.write_bytes(b"cleanup-failure\n")
    restore_root = state / "restore" / token
    restore_root.mkdir(parents=True, mode=0o700)
    (restore_root / "compose.yaml").write_bytes(b"compose-bytes\n")
    diagnosis = state / "diagnosis.json"
    diagnosis_value = {
        "schema": 1,
        "kind": "failed_before_creation",
        "failure_stage": "controller-start",
        "failure_code": "pre_creation_controller_admission_failure",
        "token": token,
        "operation_sha256": operation_hash,
        "archive_sha256": "a" * 64,
        "snapshot_sha256": "b" * 64,
        "selection_sha256": "c" * 64,
        "failure_result_sha256": restore_retirement_archive.digest_file(failure_path),
        "no_create_intent": True,
        "no_create_result": True,
        "controller_gone": True,
        "registered_processes_gone": True,
        "restore_container_absent": True,
        "restore_volume_absent": True,
        "main_stopped": True,
        "baseline_unchanged": True,
    }
    diagnosis.write_text(json.dumps(diagnosis_value))

    root = restore_retirement_archive.archive_attempt(
        state, diagnosis, operation, diagnosis_value
    )
    restore_retirement_archive.publish_active_marker(state, token, root)
    restore_retirement_archive.validate_retired_history(state)
    receipt.unlink()
    monkeypatch.setattr(restore, "read_operation", lambda _directory: operation)

    assert restore_retirement_archive.prepare_next_attempt(state)
    assert not (state / "restore-operation.json").exists()
    assert not (state / "restore" / token).exists()
    assert not (state / "restore-retirement-active.json").exists()
    assert (root / "evidence" / receipt.name).read_bytes() == b"cleanup-failure\n"
    assert (
        root / "evidence" / "restore" / token / "compose.yaml"
    ).read_bytes() == b"compose-bytes\n"


def test_retirement_archive_tampering_blocks_recovery(tmp_path):
    root = tmp_path / "retired" / "token"
    evidence = root / "evidence"
    evidence.mkdir(parents=True)
    archived = evidence / "restore-operation.json"
    archived.write_bytes(b"original")
    manifest = {
        "schema": 1,
        "token": "token",
        "status": "retired_failed_before_creation",
        "files": [
            {
                "path": "restore-operation.json",
                "sha256": hashlib.sha256(b"original").hexdigest(),
                "bytes": 8,
            }
        ],
    }
    manifest_path = root / "retirement.json"
    manifest_path.write_text(json.dumps(manifest))
    (root / "retirement-seal.json").write_text(
        json.dumps(
            {
                "token": "token",
                "sha256": restore_retirement_archive.digest_file(manifest_path),
            }
        )
    )
    archived.write_bytes(b"tampered!")

    with pytest.raises(RuntimeError, match="archive_invalid"):
        restore_retirement_archive.verify_archive(root, "token")


def test_retirement_diagnosis_requires_exact_readonly_hash_bound_contract(tmp_path):
    token = "f" * 32
    operation_path = tmp_path / "restore-operation.json"
    operation = {
        "token": token,
        "archive": {"sha256": "a" * 64},
        "snapshot": {"sha256": "b" * 64},
        "selection": {"sha256": "c" * 64},
    }
    operation_path.write_text(json.dumps(operation))
    failure_path = tmp_path / f"restore-{token}-failure.result.json"
    failure_path.write_text(
        json.dumps({"token": token, "status": "failed", "stage": "controller-start"})
    )
    failure_path.chmod(0o600)
    diagnosis = {
        "schema": 1,
        "kind": "failed_before_creation",
        "failure_stage": "controller-start",
        "failure_code": "pre_creation_controller_admission_failure",
        "token": token,
        "operation_sha256": restore_retirement_archive.digest_file(operation_path),
        "archive_sha256": "a" * 64,
        "snapshot_sha256": "b" * 64,
        "selection_sha256": "c" * 64,
        "failure_result_sha256": restore_retirement_archive.digest_file(failure_path),
        "no_create_intent": True,
        "no_create_result": True,
        "controller_gone": True,
        "registered_processes_gone": True,
        "restore_container_absent": True,
        "restore_volume_absent": True,
        "main_stopped": True,
        "baseline_unchanged": True,
    }
    path = tmp_path / "diagnosis.json"
    path.write_text(json.dumps(diagnosis))
    path.chmod(0o400)

    assert restore_retirement._diagnosis(path, operation, tmp_path) == diagnosis
    path.chmod(0o600)
    with pytest.raises(RuntimeError, match="not_private_immutable"):
        restore_retirement._diagnosis(path, operation, tmp_path)
