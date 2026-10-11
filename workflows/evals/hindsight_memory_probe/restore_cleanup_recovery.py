"""Bounded, registered cleanup-only recovery for a completed Compose create."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from . import restore_retirement_archive as source_archive
from . import restore_cleanup_recovery_contract as contract
from . import restore_cleanup_recovery_history as history
STAGES = ("stop", "remove-container", "remove-volume")


_digest = contract._digest
_write_once = contract._write_once
_readback_admission = contract._readback_admission
_admission = contract._admission
_container_identity = contract._container_identity
_volume_identity = contract._volume_identity
_diagnosis = contract._diagnosis
_source_proof = contract._source_proof

def _readback(directory: Path, operation: dict, *, allow_unregistered: bool = True):
    from . import restore_database as db
    container = db.restore_container(operation, allow_unregistered=allow_unregistered)
    volume = db.verify_volume(operation, allow_unregistered=allow_unregistered)
    return container, volume


def _command_proof(directory: Path, operation: dict, stage: str, command: list[str]) -> dict | None:
    from . import host_guard, restore_process

    expected_hash = hashlib.sha256(json.dumps(command).encode()).hexdigest()
    matches = [job for job in restore_process.registered_jobs(directory, operation["token"])
               if job.get("operation") == "cleanup-recovery-" + stage]
    if not matches:
        return None
    if len(matches) != 1 or matches[0].get("command_sha256") != expected_hash:
        raise RuntimeError("restore_cleanup_recovery_job_conflict")
    job = matches[0]
    child = directory / f"job-{job['token']}.result.json"
    if not child.is_file():
        if host_guard.tagged_processes(job["token"]):
            raise RuntimeError("restore_cleanup_recovery_job_active")
        raise RuntimeError("restore_cleanup_recovery_job_outcome_ambiguous")
    result = json.loads(child.read_text())
    return {"job": job, "child_result_path": child, "child_result": result,
            "wrapper_path": directory / f"restore-{operation['token']}-{job['token']}-result.json"}


def _stage_paths(directory: Path, token: str, stage: str) -> tuple[Path, Path]:
    return (directory / f"restore-{token}-cleanup-recovery-{stage}.intent.json",
            directory / f"restore-{token}-cleanup-recovery-{stage}.result.json")


def _stage_identity(operation: dict, admission: dict) -> dict:
    return {"schema": 1, "token": operation["token"],
            "admission_sha256": _digest(admission), "container_identity": admission["container_identity"],
            "volume_identity": admission["volume_identity"]}


def _run_stage(directory: Path, operation: dict, admission: dict, stage: str,
               command: list[str] | None, pre_container: dict | None, pre_volume: dict | None) -> None:
    from . import restore_process

    token = operation["token"]
    intent_path, result_path = _stage_paths(directory, token, stage)
    base = _stage_identity(operation, admission)
    intent = {**base, "stage": stage, "command": command,
              "pre_container_sha256": _digest(_container_identity(pre_container)) if pre_container else None,
              "pre_volume_sha256": _digest(_volume_identity(pre_volume)) if pre_volume else None,
              "created_at": time.time()}
    if intent_path.exists():
        saved = json.loads(intent_path.read_text())
        if set(saved) != {"schema", "token", "admission_sha256", "container_identity", "volume_identity",
                          "stage", "command", "pre_container_sha256", "pre_volume_sha256", "created_at"}:
            raise RuntimeError("restore_cleanup_recovery_stage_intent_invalid")
        if any(saved.get(key) != intent.get(key) for key in
               ("schema", "token", "admission_sha256", "stage", "command",
                "pre_container_sha256", "pre_volume_sha256")):
            # On resume, state may already reflect this stage; validate its immutable preimage below.
            if (saved.get("schema") != 1 or saved.get("token") != token
                    or saved.get("admission_sha256") != base["admission_sha256"]
                    or saved.get("stage") != stage or saved.get("command") != command):
                raise RuntimeError("restore_cleanup_recovery_stage_intent_invalid")
        intent = saved
        command = saved.get("command")
    else:
        if time.time() >= admission["deadline"]:
            raise RuntimeError("restore_cleanup_recovery_deadline_elapsed")
        _write_once(directory, intent_path.name, intent)
    if result_path.exists():
        result = json.loads(result_path.read_text())
        if (result.get("schema") != 1 or result.get("token") != token
                or result.get("admission_sha256") != base["admission_sha256"]
                or result.get("stage") != stage or result.get("intent_sha256") != source_archive.digest_file(intent_path)):
            raise RuntimeError("restore_cleanup_recovery_stage_result_invalid")
        if command is not None:
            proof = _command_proof(directory, operation, stage, command)
            if (proof is None or proof["child_result"].get("exit_code") != 0
                    or result.get("command_job_token") != proof["job"]["token"]
                    or result.get("command_child_result_sha256") != source_archive.digest_file(proof["child_result_path"])):
                raise RuntimeError("restore_cleanup_recovery_stage_command_unproven")
        return
    if command is not None:
        proof = _command_proof(directory, operation, stage, command)
        if proof is None:
            if time.time() >= admission["deadline"]:
                raise RuntimeError("restore_cleanup_recovery_deadline_elapsed")
            restore_process.run_command(directory, operation, command, timeout=45,
                operation_label="cleanup-recovery-" + stage, monitor=lambda: None)
        proof = _command_proof(directory, operation, stage, command)
        if proof is None or proof["child_result"].get("exit_code") != 0:
            raise RuntimeError("restore_cleanup_recovery_command_result_missing")
    _write_once(directory, result_path.name, {"schema": 1, "token": token,
        "admission_sha256": base["admission_sha256"], "stage": stage,
        "intent_sha256": source_archive.digest_file(intent_path),
        "command_job_token": None if command is None else proof["job"]["token"],
        "command_child_result_sha256": None if command is None else source_archive.digest_file(proof["child_result_path"]),
        "wrapper_result_absent": False if command is None else not proof["wrapper_path"].exists(),
        "completed_at": time.time()})


_verify_diagnosis_container = contract._verify_diagnosis_container

def _run_cleanup(directory: Path, operation: dict, admission: dict, diagnosis: dict) -> None:
    from . import restore, restore_database as db

    token = operation["token"]
    container_id = admission["container_identity"]["id"]
    cleanup_operation = {**operation, "cleanup_deadline": admission["deadline"],
                         "_cleanup_recovery_container_id": container_id}
    complete_path = directory / f"restore-{token}-cleanup-recovery-complete.result.json"
    if complete_path.is_file():
        complete = json.loads(complete_path.read_text())
        if complete.get("token") != token or complete.get("admission_sha256") != _digest(admission):
            raise RuntimeError("restore_cleanup_recovery_completion_invalid")
        container, volume = _readback(directory, cleanup_operation)
        if container is None and volume is None:
            registry, epoch, main_admission, evidence = restore._load_main(directory)
            restore._verify_host(directory, registry, main_admission, prospective=False)
            return
        raise RuntimeError("restore_cleanup_recovery_resource_resurrected")
    for stage in STAGES:
        existing_intent, _existing_result = _stage_paths(directory, token, stage)
        if existing_intent.is_file():
            command = json.loads(existing_intent.read_text()).get("command")
        else:
            command = None
        if stage == "stop":
            container, volume = _readback(directory, cleanup_operation)
            if container is None or volume is None:
                _resume_proven_absence(directory, cleanup_operation, admission, diagnosis)
                continue
            _verify_diagnosis_container(diagnosis, container, volume)
            command = command if existing_intent.is_file() else (
                ["docker", "stop", "--time", "20", container_id]
                if container["State"]["Status"] == "running" else None)
        elif stage == "remove-container":
            container, volume = _readback(directory, cleanup_operation)
            if container is None:
                _resume_proven_absence(directory, cleanup_operation, admission, diagnosis)
                continue
            _verify_diagnosis_container(diagnosis, container, volume)
            if container["State"]["Status"] == "running":
                raise RuntimeError("restore_cleanup_recovery_stop_unproven")
            command = command if existing_intent.is_file() else ["docker", "rm", container_id]
        else:
            container, volume = _readback(directory, cleanup_operation)
            if container is not None:
                raise RuntimeError("restore_cleanup_recovery_container_removal_unproven")
            if volume is None:
                _resume_proven_absence(directory, cleanup_operation, admission, diagnosis)
                continue
            if _volume_identity(volume) != admission["volume_identity"]:
                raise RuntimeError("restore_cleanup_recovery_volume_changed")
            consumers = db.docker_text(["docker", "ps", "-aq", "--no-trunc", "--filter",
                                        "volume=" + operation["compose"]["volume"]])
            if consumers:
                raise RuntimeError("restore_cleanup_recovery_volume_consumer_detected")
            command = command if existing_intent.is_file() else ["docker", "volume", "rm", operation["compose"]["volume"]]
        _run_stage(directory, cleanup_operation, admission, stage, command, container, volume)
        after_container, after_volume = _readback(directory, cleanup_operation)
        if stage == "stop":
            if after_container is None or after_container["State"]["Status"] == "running" or after_volume is None:
                raise RuntimeError("restore_cleanup_recovery_stop_unproven")
            _verify_diagnosis_container(diagnosis, after_container, after_volume)
        elif stage == "remove-container" and after_container is not None:
            raise RuntimeError("restore_cleanup_recovery_removal_unproven")
        elif stage == "remove-volume" and after_volume is not None:
            raise RuntimeError("restore_cleanup_recovery_removal_unproven")
    container, volume = _readback(directory, cleanup_operation)
    if container is not None or volume is not None:
        raise RuntimeError("restore_cleanup_recovery_removal_unproven")
    registry, epoch, main_admission, evidence = restore._load_main(directory)
    restore._verify_host(directory, registry, main_admission, prospective=False)
    _write_once(directory, f"restore-{token}-cleanup-recovery-complete.result.json", {
        "schema": 1, "token": token, "admission_sha256": _digest(admission),
        "status": "failed_create_cleaned", "container_absent": True, "volume_absent": True,
        "main_and_baseline_verified": True, "completed_at": time.time()})


def _resume_proven_absence(directory: Path, operation: dict, admission: dict, diagnosis: dict) -> None:
    """Accept absent resources only when a registered exact removal is proven."""
    token = operation["token"]
    container, volume = _readback(directory, operation)
    if container is None:
        intent, result = _stage_paths(directory, token, "remove-container")
        command = ["docker", "rm", admission["container_identity"]["id"]]
        _recover_stage_from_child(directory, operation, admission, "remove-container", intent, result, command)
    if volume is None:
        intent, result = _stage_paths(directory, token, "remove-volume")
        command = ["docker", "volume", "rm", operation["compose"]["volume"]]
        _recover_stage_from_child(directory, operation, admission, "remove-volume", intent, result, command)


def _recover_stage_from_child(directory: Path, operation: dict, admission: dict, stage: str,
                              intent_path: Path, result_path: Path, command: list[str]) -> None:
    if not intent_path.is_file():
        raise RuntimeError("restore_cleanup_recovery_unregistered_removal_rejected")
    intent = json.loads(intent_path.read_text())
    if (intent.get("token") != operation["token"] or intent.get("stage") != stage
            or intent.get("command") != command or intent.get("admission_sha256") != _digest(admission)):
        raise RuntimeError("restore_cleanup_recovery_stage_intent_invalid")
    if result_path.is_file():
        result = json.loads(result_path.read_text())
        proof = _command_proof(directory, operation, stage, command)
        if (proof is None or proof["child_result"].get("exit_code") != 0
                or result.get("token") != operation["token"] or result.get("stage") != stage
                or result.get("intent_sha256") != source_archive.digest_file(intent_path)
                or result.get("command_job_token") != proof["job"]["token"]
                or result.get("command_child_result_sha256") != source_archive.digest_file(proof["child_result_path"])):
            raise RuntimeError("restore_cleanup_recovery_stage_result_invalid")
        return
    proof = _command_proof(directory, operation, stage, command)
    if proof is None or proof["child_result"].get("exit_code") != 0:
        raise RuntimeError("restore_cleanup_recovery_removal_result_missing")
    _write_once(directory, result_path.name, {"schema": 1, "token": operation["token"],
        "admission_sha256": _digest(admission), "stage": stage,
        "intent_sha256": source_archive.digest_file(intent_path), "command_job_token": proof["job"]["token"],
        "command_child_result_sha256": source_archive.digest_file(proof["child_result_path"]),
        "wrapper_result_absent": not proof["wrapper_path"].exists(), "completed_at": time.time()})


def recover(directory: Path, diagnosis_path: Path) -> dict:
    from . import host_guard as host, restore, restore_cleanup, restore_database as db, restore_process
    from .restore_retirement import admission_lease

    with admission_lease(directory):
        interrupted = history.finish_interrupted(directory, diagnosis_path)
        if interrupted:
            return interrupted
        operation = restore.read_operation(directory)
        token = operation["token"]
        diagnosis = _diagnosis(directory, operation, diagnosis_path)
        if (directory / f"restore-{token}-result.json").exists():
            raise RuntimeError("restore_cleanup_recovery_successful_result_rejected")
        _source_proof(directory, operation)
        readback_admission = _readback_admission(directory, operation, diagnosis_path)
        readback_operation = {**operation, "cleanup_deadline": readback_admission["deadline"],
                              "_cleanup_recovery_container_id": diagnosis["container_id"]}
        jobs = restore_process.registered_jobs(directory, token)
        if any(host.tagged_processes(job["token"]) for job in jobs):
            raise RuntimeError("restore_cleanup_recovery_process_active")
        with restore_cleanup.registered_host_readback(directory, readback_operation):
            restore._verify_host(directory, json.loads((directory / "registry.json").read_text()),
                {"containers": operation["finalization"]["containers"]}, prospective=False,
                allow_restore_creation=True)
            db.verify_compose(operation)
            container, volume = _readback(directory, operation)
            if container is None or volume is None:
                admission_path = directory / f"restore-{token}-cleanup-recovery-admission.json"
                if not admission_path.is_file():
                    raise RuntimeError("restore_cleanup_recovery_resource_missing")
                admission = _admission(directory, operation, diagnosis_path, diagnosis,
                                       json.loads(admission_path.read_text())["container_identity"],
                                       json.loads(admission_path.read_text())["volume_identity"])
            else:
                _verify_diagnosis_container(diagnosis, container, volume)
                admission = _admission(directory, operation, diagnosis_path, diagnosis, container, volume)
        cleanup_operation = {**operation, "cleanup_deadline": admission["deadline"],
                             "_cleanup_recovery_container_id": admission["container_identity"]["id"]}
        with restore_cleanup.registered_host_readback(directory, cleanup_operation):
            _run_cleanup(directory, cleanup_operation, admission, diagnosis)
        manifest_path = history.archive_attempt(directory, token, diagnosis_path, admission)
        return {"status": "failed_create_cleaned", "token": token, "recovery": str(manifest_path),
                "sha256": source_archive.digest_file(manifest_path)}


def prepare_next_attempt(directory: Path) -> None:
    history.validate_history(directory)
