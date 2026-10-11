"""Byte-preserving failed-create cleanup history and restartable publication."""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from pathlib import Path

from . import restore_retirement_archive as source_archive
from .campaign_clock import WORK_CUTOFF
from .receipts import ReceiptStore

STAGES = ("stop", "remove-container", "remove-volume")


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _write_once(directory: Path, name: str, value: dict) -> Path:
    path = directory / name
    if path.exists():
        if path.is_symlink() or not path.is_file() or json.loads(path.read_text()) != value:
            raise RuntimeError("restore_cleanup_recovery_history_conflict")
        return path
    ReceiptStore(directory).write(name, value)
    path.chmod(0o400)
    return path


def archive_attempt(directory: Path, token: str, diagnosis_path: Path, admission: dict) -> Path:
    root = directory / "restore-cleanup-recovered" / token
    source_archive._mkdir_durable(root)
    sources = source_archive._source_files(directory, token)
    sources["diagnosis.json"] = diagnosis_path
    sources["cleanup-recovery-admission.json"] = directory / f"restore-{token}-cleanup-recovery-admission.json"
    sources["cleanup-recovery-admission.seal.json"] = directory / f"restore-{token}-cleanup-recovery-admission.seal.json"
    rows = [{"path": name, "sha256": source_archive.digest_file(path), "bytes": path.stat().st_size}
            for name, path in sorted(sources.items())]
    for name, path in sources.items():
        source_archive._copy_immutable(path, root / "evidence" / name)
    manifest = {"schema": 1, "kind": "failed_create_cleaned", "token": token,
                "operation_sha256": admission["operation_sha256"],
                "diagnosis_sha256": admission["diagnosis_sha256"],
                "admission_sha256": source_archive.digest_file(sources["cleanup-recovery-admission.json"]),
                "files": rows}
    manifest_path = root / "recovery.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text())
        if any(existing.get(key) != manifest.get(key) for key in manifest):
            raise RuntimeError("restore_cleanup_recovery_archive_conflict")
        manifest = existing
    else:
        _write_once(root, manifest_path.name, manifest)
    _seal_and_remove(directory, token, root)
    return manifest_path


def _seal_and_remove(directory: Path, token: str, root: Path) -> None:
    manifest_path = root / "recovery.json"
    seal_path = root / "recovery-seal.json"
    seal = {"schema": 1, "token": token, "sha256": source_archive.digest_file(manifest_path)}
    _write_once(root, seal_path.name, seal)
    validate_history(directory)
    _remove_active_sources(directory, token, root)


def finish_interrupted(directory: Path, diagnosis_path: Path) -> dict | None:
    try:
        token = json.loads(diagnosis_path.read_text()).get("token")
    except Exception:
        return None
    if not isinstance(token, str) or not re.fullmatch(r"[a-f0-9]{32}", token):
        return None
    root = directory / "restore-cleanup-recovered" / token
    if not root.is_dir() or not (root / "recovery.json").is_file():
        return None
    validate_history(directory, allow_unsealed=True)
    _seal_and_remove(directory, token, root)
    return {"status": "failed_create_cleaned", "token": token,
            "recovery": str(root / "recovery.json"), "sha256": source_archive.digest_file(root / "recovery.json")}


def _remove_active_sources(directory: Path, token: str, root: Path) -> None:
    manifest = json.loads((root / "recovery.json").read_text())
    expected = {row["path"]: row["sha256"] for row in manifest["files"]}
    active = source_archive._source_files(directory, token)
    for name, path in active.items():
        saved = root / "evidence" / name
        if name not in expected or source_archive.digest_file(path) != expected[name] \
                or source_archive.digest_file(saved) != expected[name]:
            raise RuntimeError("restore_cleanup_recovery_source_changed")
    for path in active.values():
        path.unlink()
    restore_root = directory / "restore" / token
    if restore_root.exists():
        shutil.rmtree(restore_root)
    source_archive._fsync_directory(directory)


def _required_files(token: str, diagnosis: dict) -> set[str]:
    files = {"restore-operation.json", "restore-operation-seal.json", f"restore-{token}-failure.result.json",
             f"restore-{token}-create.intent.json", "diagnosis.json", "cleanup-recovery-admission.json",
             "cleanup-recovery-admission.seal.json", f"restore-{token}-cleanup-recovery-complete.result.json",
             f"restore-{token}-cleanup-recovery-readback-admission.json",
             f"restore-{token}-cleanup-recovery-readback-admission.seal.json",
             f"restore-{token}-{diagnosis['create_job_token']}-job.json",
             f"job-{diagnosis['create_job_token']}.result.json"}
    for stage in STAGES:
        files.add(f"restore-{token}-cleanup-recovery-{stage}.intent.json")
        files.add(f"restore-{token}-cleanup-recovery-{stage}.result.json")
    return files


def _validate_files(root: Path, rows: list[dict]) -> dict[str, Path]:
    if len({row.get("path") for row in rows if isinstance(row, dict)}) != len(rows):
        raise RuntimeError("restore_cleanup_recovery_history_duplicate_path")
    by_path = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "bytes"}:
            raise RuntimeError("restore_cleanup_recovery_history_schema_invalid")
        relative = Path(row["path"])
        target = root / "evidence" / relative
        if (relative.is_absolute() or ".." in relative.parts or not relative.parts or target.is_symlink()
                or not target.is_file() or target.stat().st_mode & 0o377
                or target.stat().st_size != row["bytes"] or source_archive.digest_file(target) != row["sha256"]):
            raise RuntimeError("restore_cleanup_recovery_history_file_invalid")
        by_path[row["path"]] = target
    evidence = root / "evidence"
    found = set()
    for path in evidence.rglob("*"):
        if path.is_symlink():
            raise RuntimeError("restore_cleanup_recovery_history_symlink")
        if path.is_file():
            found.add(str(path.relative_to(evidence)))
    if found != set(by_path):
        raise RuntimeError("restore_cleanup_recovery_history_unlisted_file")
    return by_path


def validate_history(directory: Path, *, allow_unsealed: bool = False) -> None:
    parent = directory / "restore-cleanup-recovered"
    if not parent.exists():
        return
    if parent.is_symlink() or not parent.is_dir():
        raise RuntimeError("restore_cleanup_recovery_history_invalid")
    for root in parent.iterdir():
        token = root.name
        if root.is_symlink() or not root.is_dir() or not re.fullmatch(r"[a-f0-9]{32}", token):
            raise RuntimeError("restore_cleanup_recovery_history_invalid")
        manifest_path, seal_path = root / "recovery.json", root / "recovery-seal.json"
        root_entries = {path.name for path in root.iterdir()}
        sealed_entries = {"evidence", "recovery.json", "recovery-seal.json"}
        unsealed_entries = {"evidence", "recovery.json"}
        if (root_entries != sealed_entries
                and not (allow_unsealed and root_entries == unsealed_entries)):
            raise RuntimeError("restore_cleanup_recovery_history_unlisted_root_entry")
        if (not manifest_path.is_file() or manifest_path.is_symlink()
                    or manifest_path.stat().st_mode & 0o377):
            raise RuntimeError("restore_cleanup_recovery_history_incomplete")
        manifest = json.loads(manifest_path.read_text())
        rows = manifest.get("files")
        if (set(manifest) != {"schema", "kind", "token", "operation_sha256", "diagnosis_sha256",
                             "admission_sha256", "files"}
                or manifest.get("schema") != 1 or manifest.get("kind") != "failed_create_cleaned"
                or manifest.get("token") != token or not isinstance(rows, list) or not rows):
            raise RuntimeError("restore_cleanup_recovery_history_schema_invalid")
        if not seal_path.exists() and allow_unsealed:
            seal = {"schema": 1, "token": token, "sha256": source_archive.digest_file(manifest_path)}
        else:
            if (not seal_path.is_file() or seal_path.is_symlink()
                    or seal_path.stat().st_mode & 0o377):
                raise RuntimeError("restore_cleanup_recovery_history_unsealed")
            seal = json.loads(seal_path.read_text())
        if (set(seal) != {"schema", "token", "sha256"} or seal.get("schema") != 1
                or seal.get("token") != token or seal.get("sha256") != source_archive.digest_file(manifest_path)):
            raise RuntimeError("restore_cleanup_recovery_history_seal_invalid")
        by_path = _validate_files(root, rows)
        diagnosis_path = by_path.get("diagnosis.json")
        if diagnosis_path is None:
            raise RuntimeError("restore_cleanup_recovery_history_diagnosis_missing")
        diagnosis = json.loads(diagnosis_path.read_text())
        diagnosis_fields = {"schema", "kind", "token", "operation_sha256", "failure_sha256",
                            "create_intent_sha256", "create_job_token", "create_job_registration_sha256",
                            "create_child_result_sha256", "create_wrapper_result_absent", "container_id",
                            "container_started_at", "image_id", "container_identity_sha256", "volume",
                            "volume_identity_sha256", "controller_gone", "processes_gone",
                            "main_stopped", "baseline_unchanged"}
        if (set(diagnosis) != diagnosis_fields or diagnosis.get("schema") != 1
                or diagnosis.get("kind") != "created_but_unpublished_cleanup_only"
                or any(diagnosis.get(key) is not True for key in
                       ("create_wrapper_result_absent", "controller_gone", "processes_gone", "main_stopped", "baseline_unchanged"))):
            raise RuntimeError("restore_cleanup_recovery_history_diagnosis_invalid")
        required = _required_files(token, diagnosis)
        if not required.issubset(by_path):
            raise RuntimeError("restore_cleanup_recovery_history_membership_invalid")
        operation_bytes = by_path["restore-operation.json"].read_bytes()
        operation = json.loads(operation_bytes)
        operation_hash = hashlib.sha256(operation_bytes).hexdigest()
        operation_seal = json.loads(by_path["restore-operation-seal.json"].read_text())
        failure_path = by_path[f"restore-{token}-failure.result.json"]
        intent_path = by_path[f"restore-{token}-create.intent.json"]
        failure = json.loads(failure_path.read_text())
        intent = json.loads(intent_path.read_text())
        admission_path = by_path["cleanup-recovery-admission.json"]
        admission = json.loads(admission_path.read_text())
        admission_seal = json.loads(by_path["cleanup-recovery-admission.seal.json"].read_text())
        readback_path = by_path[f"restore-{token}-cleanup-recovery-readback-admission.json"]
        readback_admission = json.loads(readback_path.read_text())
        readback_seal = json.loads(by_path[f"restore-{token}-cleanup-recovery-readback-admission.seal.json"].read_text())
        admission_fields = {"schema", "kind", "token", "operation_sha256", "diagnosis_sha256",
                            "container_identity", "volume_identity", "deadline", "created_at"}
        readback_fields = {"schema", "kind", "token", "operation_sha256", "diagnosis_sha256",
                           "deadline", "commands", "created_at"}
        if (set(admission) != admission_fields or admission.get("schema") != 1
                or admission.get("kind") != "restore_cleanup_only_recovery"
                or admission.get("diagnosis_sha256") != source_archive.digest_file(diagnosis_path)
                or type(admission.get("deadline")) not in (int, float)
                or not math.isfinite(admission["deadline"])
                or admission["deadline"] > WORK_CUTOFF
                or type(admission.get("created_at")) not in (int, float)
                or not math.isfinite(admission["created_at"])
                or admission["deadline"] > admission["created_at"] + 600
                or admission["deadline"] <= admission["created_at"]
                or operation.get("token") != token or manifest.get("operation_sha256") != operation_hash
                or operation_seal.get("sha256") != operation_hash or operation_seal.get("token") != token
                or diagnosis.get("token") != token or diagnosis.get("operation_sha256") != operation_hash
                or diagnosis.get("failure_sha256") != source_archive.digest_file(failure_path)
                or diagnosis.get("create_intent_sha256") != source_archive.digest_file(intent_path)
                or manifest.get("diagnosis_sha256") != source_archive.digest_file(diagnosis_path)
                or manifest.get("admission_sha256") != source_archive.digest_file(admission_path)
                or set(readback_admission) != readback_fields or readback_admission.get("schema") != 1
                or readback_admission.get("kind") != "read_only_restore_cleanup_recovery"
                or readback_admission.get("token") != token
                or readback_admission.get("operation_sha256") != operation_hash
                or readback_admission.get("diagnosis_sha256") != source_archive.digest_file(diagnosis_path)
                or readback_admission.get("commands") != ["docker ps", "docker inspect", "docker volume ls", "docker volume inspect"]
                or type(readback_admission.get("deadline")) not in (int, float)
                or not math.isfinite(readback_admission["deadline"])
                or readback_admission["deadline"] > WORK_CUTOFF
                or type(readback_admission.get("created_at")) not in (int, float)
                or not math.isfinite(readback_admission["created_at"])
                or readback_admission["deadline"] > readback_admission["created_at"] + 600
                or readback_admission["deadline"] <= readback_admission["created_at"]
                or readback_admission["created_at"] > admission["created_at"]
                or readback_seal.get("token") != token
                or readback_seal.get("sha256") != source_archive.digest_file(readback_path)
                or admission_seal.get("token") != token
                or admission_seal.get("sha256") != source_archive.digest_file(admission_path)
                or admission.get("token") != token or admission.get("operation_sha256") != operation_hash
                or failure.get("token") != token or failure.get("status") != "failed"
                or failure.get("stage") != "create" or failure.get("reason") != "restore_unowned_container_detected"
                or intent.get("token") != token or intent.get("compose_sha256") != operation["compose"]["sha256"]
                or intent.get("project") != operation["compose"]["project"]
                or intent.get("volume") != operation["compose"]["volume"]):
            raise RuntimeError("restore_cleanup_recovery_history_binding_invalid")
        create_job_path = by_path[f"restore-{token}-{diagnosis['create_job_token']}-job.json"]
        create_job = json.loads(create_job_path.read_text())
        child_path = by_path[f"job-{diagnosis['create_job_token']}.result.json"]
        command = ["docker", "compose", "--project-name", operation["compose"]["project"], "-f",
                   operation["compose"]["path"], "up", "-d", "--pull", "never", "db"]
        if (diagnosis.get("create_wrapper_result_absent") is not True
                or f"restore-{token}-{diagnosis['create_job_token']}-result.json" in by_path
                or diagnosis.get("create_job_registration_sha256") != source_archive.digest_file(create_job_path)
                or diagnosis.get("create_child_result_sha256") != source_archive.digest_file(child_path)
                or create_job.get("token") != diagnosis["create_job_token"]
                or create_job.get("operation_token") != token
                or create_job.get("operation") != "compose-create"
                or create_job.get("command_sha256") != hashlib.sha256(json.dumps(command).encode()).hexdigest()
                or json.loads(child_path.read_text()).get("exit_code") != 0):
            raise RuntimeError("restore_cleanup_recovery_history_create_proof_invalid")
        if (admission.get("container_identity", {}).get("id") != diagnosis.get("container_id")
                or admission.get("container_identity", {}).get("image_id") != diagnosis.get("image_id")
                or admission.get("container_identity", {}).get("started_at") != diagnosis.get("container_started_at")
                or digest(admission.get("container_identity")) != diagnosis.get("container_identity_sha256")
                or admission.get("volume_identity", {}).get("Name") != diagnosis.get("volume")
                or hashlib.sha256(json.dumps(admission.get("volume_identity"), sort_keys=True).encode()).hexdigest()
                != diagnosis.get("volume_identity_sha256")):
            raise RuntimeError("restore_cleanup_recovery_history_resource_binding_invalid")
        read_only_operations = {"restore-identity-readback", "restore-identity-list-readback",
                                "restore-operator-readback", "restore-operator-list-readback"}
        read_only_jobs = []
        for name, job_path in by_path.items():
            match = re.fullmatch(rf"restore-{re.escape(token)}-([a-f0-9]{{32}})-job\.json", name)
            if not match:
                continue
            job = json.loads(job_path.read_text())
            if job.get("operation") not in read_only_operations:
                continue
            job_token = match.group(1)
            child = by_path.get(f"job-{job_token}.result.json")
            wrapper = by_path.get(f"restore-{token}-{job_token}-result.json")
            wrapper_value = json.loads(wrapper.read_text()) if wrapper else {}
            if (job.get("token") != job_token or job.get("operation_token") != token
                    or child is None or json.loads(child.read_text()).get("exit_code") != 0
                    or wrapper_value.get("operation") != job.get("operation")
                    or wrapper_value.get("exit_code") != 0
                    or wrapper_value.get("command_sha256") != job.get("command_sha256")
                    or type(job.get("deadline")) not in (int, float)
                    or job["deadline"] > readback_admission["deadline"]):
                raise RuntimeError("restore_cleanup_recovery_history_readback_job_invalid")
            read_only_jobs.append(job["operation"])
        if not {"restore-operator-list-readback", "restore-operator-readback"}.issubset(read_only_jobs):
            raise RuntimeError("restore_cleanup_recovery_history_readback_incomplete")
        for stage in STAGES:
            stage_intent_path = by_path[f"restore-{token}-cleanup-recovery-{stage}.intent.json"]
            stage_result_path = by_path[f"restore-{token}-cleanup-recovery-{stage}.result.json"]
            stage_intent = json.loads(stage_intent_path.read_text())
            stage_result = json.loads(stage_result_path.read_text())
            if (set(stage_intent) != {"schema", "token", "admission_sha256", "container_identity",
                                      "volume_identity", "stage", "command", "pre_container_sha256",
                                      "pre_volume_sha256", "created_at"}
                    or stage_intent.get("schema") != 1
                    or stage_intent.get("token") != token or stage_intent.get("stage") != stage
                    or stage_intent.get("admission_sha256") != digest(admission)
                    or stage_intent.get("container_identity") != admission["container_identity"]
                    or stage_intent.get("volume_identity") != admission["volume_identity"]
                    or set(stage_result) != {"schema", "token", "admission_sha256", "stage", "intent_sha256",
                                             "command_job_token", "command_child_result_sha256",
                                             "wrapper_result_absent", "completed_at"}
                    or stage_result.get("schema") != 1
                    or stage_result.get("token") != token or stage_result.get("stage") != stage
                    or stage_result.get("intent_sha256") != source_archive.digest_file(stage_intent_path)
                    or stage_result.get("admission_sha256") != digest(admission)):
                raise RuntimeError("restore_cleanup_recovery_history_stage_invalid")
            command = stage_intent.get("command")
            expected_commands = {
                "stop": None if command is None else ["docker", "stop", "--time", "20", diagnosis["container_id"]],
                "remove-container": ["docker", "rm", diagnosis["container_id"]],
                "remove-volume": ["docker", "volume", "rm", diagnosis["volume"]],
            }
            if command != expected_commands[stage]:
                raise RuntimeError("restore_cleanup_recovery_history_command_scope_invalid")
            if command is not None:
                job_token = stage_result.get("command_job_token")
                registration_path = by_path.get(f"restore-{token}-{job_token}-job.json")
                child_result_path = by_path.get(f"job-{job_token}.result.json")
                expected_hash = hashlib.sha256(json.dumps(command).encode()).hexdigest()
                if (registration_path is None or child_result_path is None
                        or stage_result.get("command_child_result_sha256") != source_archive.digest_file(child_result_path)
                        or json.loads(registration_path.read_text()).get("token") != job_token
                        or json.loads(registration_path.read_text()).get("operation_token") != token
                        or json.loads(registration_path.read_text()).get("operation") != "cleanup-recovery-" + stage
                        or json.loads(registration_path.read_text()).get("command_sha256") != expected_hash
                        or json.loads(child_result_path.read_text()).get("exit_code") != 0):
                    raise RuntimeError("restore_cleanup_recovery_history_command_invalid")
                wrapper_name = f"restore-{token}-{job_token}-result.json"
                if (type(stage_result.get("wrapper_result_absent")) is not bool
                        or stage_result["wrapper_result_absent"] != (wrapper_name not in by_path)):
                    raise RuntimeError("restore_cleanup_recovery_history_wrapper_conflict")
                if stage_result.get("wrapper_result_absent") is False:
                    wrapper_path = by_path.get(wrapper_name)
                    wrapper = json.loads(wrapper_path.read_text()) if wrapper_path else {}
                    registration = json.loads(registration_path.read_text()) if registration_path else {}
                    if (wrapper_path is None or wrapper.get("exit_code") != 0
                            or wrapper.get("operation") != registration.get("operation")
                            or wrapper.get("command_sha256") != expected_hash):
                        raise RuntimeError("restore_cleanup_recovery_history_wrapper_missing")
            elif (stage != "stop" or stage_result.get("command_job_token") is not None
                    or stage_result.get("command_child_result_sha256") is not None
                    or stage_result.get("wrapper_result_absent") is not None):
                raise RuntimeError("restore_cleanup_recovery_history_noop_stage_invalid")
        forbidden = {f"restore-{token}-create.result.json"}
        forbidden.update(f"restore-{token}-{suffix}.{kind}.json"
                         for suffix in ("restore", "snapshot", "compare") for kind in ("intent", "result"))
        forbidden.add(f"restore-{token}-result.json")
        if forbidden.intersection(by_path):
            raise RuntimeError("restore_cleanup_recovery_history_original_progress_invalid")
        complete_path = by_path[f"restore-{token}-cleanup-recovery-complete.result.json"]
        complete = json.loads(complete_path.read_text())
        if (complete.get("token") != token or complete.get("status") != "failed_create_cleaned"
                or complete.get("container_absent") is not True or complete.get("volume_absent") is not True
                or complete.get("main_and_baseline_verified") is not True
                or complete.get("admission_sha256") != digest(admission)):
            raise RuntimeError("restore_cleanup_recovery_history_completion_invalid")
