"""Sealed evidence history and source retirement for failed restore recovery."""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

from . import host_guard, restore_process
from . import restore_retirement_archive as archive
from .restore_post_snapshot_contract import (
    _json_digest, _require_successful_job, _sha, _write_once,
)
from .restore_post_snapshot_admission import _validate_recovery_authority

def _copy_to_archive(source: Path, destination: Path) -> None:
    archive._copy_immutable(source, destination)
    if archive.digest_file(source) != archive.digest_file(destination):
        raise RuntimeError("restore_post_snapshot_recovery_archive_hash_mismatch")

def _archive(directory: Path, token: str, authority_path: Path, session_root: Path,
             operation: dict, recovery_source_sha: str, capture: dict) -> Path:
    root = directory / "restore-post-restore-retired" / token
    evidence = root / "evidence"
    archive._mkdir_durable(root)
    sources = archive._source_files(directory, token)
    recovery_parent = directory / "restore-post-restore-recovery" / token
    for path in sorted(recovery_parent.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("restore_post_snapshot_recovery_archive_symlink")
        if path.is_file():
            sources["post-restore-recovery/" + str(path.relative_to(recovery_parent))] = path
    for relative, source in sorted(sources.items()):
        _copy_to_archive(source, evidence / relative)
    rows = [{"path": relative, "sha256": archive.digest_file(source),
             "bytes": source.stat().st_size} for relative, source in sorted(sources.items())]
    failure_path = directory / f"restore-{token}-failure.result.json"
    absence_candidates = [f"restore-{token}-snapshot.result.json",
                          f"restore-{token}-compare.result.json",
                          f"restore-{token}-result.json",
                          str(Path("restore") / token / "canonical-snapshot.json")]
    for job in restore_process.registered_jobs(directory, token):
        child_name = f"job-{job['token']}.result.json"
        wrapper_name = f"restore-{token}-{job['token']}-result.json"
        absence_candidates.extend((child_name, wrapper_name))
    if any((directory / relative).is_symlink() for relative in absence_candidates):
        raise RuntimeError("restore_post_snapshot_recovery_absence_manifest_invalid")
    expected_absent = sorted({relative for relative in absence_candidates
                               if not (directory / relative).exists()
                               and not (directory / relative).is_symlink()})
    evidence_names = {row["path"] for row in rows}
    if any((directory / relative).exists() or (directory / relative).is_symlink()
           or relative in evidence_names
           for relative in expected_absent):
        raise RuntimeError("restore_post_snapshot_recovery_absence_manifest_invalid")
    manifest = {"schema": 1, "kind": "failed_post_restore_snapshot_preserved_retired",
        "status": "failed_post_restore_retired", "token": token,
        "operation_sha256": _sha(directory / "restore-operation.json"),
        "failure_sha256": _sha(failure_path),
        "operation_source_sha": Path(operation["release_path"]).name,
        "recovery_execution_source_sha": recovery_source_sha,
        "capture_sha256": _json_digest(capture), "absent_original_results": expected_absent,
        "files": rows, "created_at": time.time()}
    manifest_path, seal_path = root / "retirement.json", root / "retirement-seal.json"
    if manifest_path.exists():
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise RuntimeError("restore_post_snapshot_recovery_archive_invalid")
        existing = json.loads(manifest_path.read_text())
        for key in ("operation_sha256", "failure_sha256", "operation_source_sha",
                    "recovery_execution_source_sha", "absent_original_results"):
            if existing.get(key) != manifest.get(key):
                raise RuntimeError("restore_post_snapshot_recovery_archive_conflict")
        manifest = existing
    else:
        _write_once(root, manifest_path.name, manifest)
    seal = {"schema": 1, "token": token, "sha256": archive.digest_file(manifest_path)}
    _write_once(root, seal_path.name, seal)
    verify_archive(root, token)
    return root

def verify_archive(root: Path, token: str, *, require_seal: bool = True) -> dict:
    manifest_path, seal_path = root / "retirement.json", root / "retirement-seal.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RuntimeError("restore_post_snapshot_recovery_archive_unsealed")
    if seal_path.is_symlink():
        raise RuntimeError("restore_post_snapshot_recovery_archive_unsealed")
    if require_seal and (seal_path.is_symlink() or not seal_path.is_file()):
        raise RuntimeError("restore_post_snapshot_recovery_archive_unsealed")
    manifest = json.loads(manifest_path.read_text())
    seal = json.loads(seal_path.read_text()) if seal_path.is_file() and not seal_path.is_symlink() else None
    if (manifest.get("schema") != 1 or manifest.get("kind") != "failed_post_restore_snapshot_preserved_retired"
            or manifest.get("status") != "failed_post_restore_retired" or manifest.get("token") != token
            or require_seal and seal != {"schema": 1, "token": token, "sha256": archive.digest_file(manifest_path)}
            or not require_seal and seal is not None
            and seal != {"schema": 1, "token": token, "sha256": archive.digest_file(manifest_path)}):
        raise RuntimeError("restore_post_snapshot_recovery_archive_seal_invalid")
    rows = manifest.get("files")
    if not isinstance(rows, list) or not rows or len({row.get("path") for row in rows}) != len(rows):
        raise RuntimeError("restore_post_snapshot_recovery_archive_invalid")
    listed = set()
    for row in rows:
        relative = Path(row.get("path", ""))
        path = root / "evidence" / relative
        if (relative.is_absolute() or ".." in relative.parts or not relative.parts
                or path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o377
                or path.stat().st_size != row.get("bytes") or archive.digest_file(path) != row.get("sha256")):
            raise RuntimeError("restore_post_snapshot_recovery_archive_invalid")
        listed.add(str(relative))
    evidence = root / "evidence"
    found = {str(path.relative_to(evidence)) for path in evidence.rglob("*") if path.is_file()}
    if any(path.is_symlink() for path in evidence.rglob("*")) or found != listed:
        raise RuntimeError("restore_post_snapshot_recovery_archive_membership_invalid")
    return manifest

def _validated_active_sources(directory: Path, token: str, archive_root: Path) -> tuple[dict, list[Path], dict]:
    manifest = verify_archive(archive_root, token)
    by_path = {row["path"]: row["sha256"] for row in manifest["files"]}
    sources = archive._source_files(directory, token)
    resume_authority_hashes = {}
    resumption_root = archive_root / "closure" / "resumptions"
    if resumption_root.is_symlink():
        raise RuntimeError("restore_post_snapshot_recovery_resume_root_invalid")
    for resume_path in (resumption_root.glob("*/resume.json") if resumption_root.exists() else []):
        if (resume_path.is_symlink() or not resume_path.is_file()
                or resume_path.stat().st_mode & 0o377):
            raise RuntimeError("restore_post_snapshot_recovery_resume_receipt_invalid")
        resume = json.loads(resume_path.read_text())
        seal_path = resume_path.with_name("resume-seal.json")
        if (seal_path.is_symlink() or not seal_path.is_file()
                or seal_path.stat().st_mode & 0o377
                or json.loads(seal_path.read_text()) != {"schema": 1, "token": token,
                    "sha256": archive.digest_file(resume_path)}
                or not isinstance(resume, dict)
                or set(resume) != {"schema", "kind", "token", "admission_token", "authority_sha256",
                                   "operation_sha256", "recovery_source_sha", "deadline",
                                   "container_identity", "volume_identity", "commands", "created_at"}
                or resume.get("schema") != 1
                or resume.get("kind") != "failed_post_restore_retirement_resume"
                or resume.get("token") != token
                or resume.get("admission_token") != resume_path.parent.name
                or not re.fullmatch(r"[a-f0-9]{64}", resume.get("authority_sha256", ""))
                or resume.get("operation_sha256") != manifest.get("operation_sha256")
                or not isinstance(resume.get("commands"), list)):
            raise RuntimeError("restore_post_snapshot_recovery_resume_seal_invalid")
        resume_authority_hashes[resume.get("authority_sha256")] = resume.get("admission_token")
    extra_authorities = []
    closure_jobs = [job for job in restore_process.registered_jobs(directory, token)
                    if job.get("operation") in {
                        restore_process.POST_RESTORE_RECOVERY_READBACK,
                        "post-restore-recovery-remove-container",
                        "post-restore-recovery-remove-volume",
                    }]
    closure_only_names = set()
    for job in closure_jobs:
        closure_only_names.update({
            f"restore-{token}-{job['token']}-job.json",
            f"restore-{token}-{job['token']}-result.json",
            f"job-{job['token']}.result.json",
        })
    closure_only = {}
    archived_sources = {}
    for relative, source in sources.items():
        if relative in by_path:
            archived_sources[relative] = source
        elif source.name in closure_only_names:
            closure_only[relative] = source
        elif source.name.startswith(f"restore-{token}-post-restore-authority-"):
            admission_token = resume_authority_hashes.get(archive.digest_file(source))
            if admission_token is None or not source.name.endswith(admission_token + ".json"):
                raise RuntimeError("restore_post_snapshot_recovery_authority_unarchived")
            extra_authorities.append(source)
        else:
            raise RuntimeError("restore_post_snapshot_recovery_source_unarchived")
    closure_manifest = archive_root / "closure" / "closure.json"
    if not closure_manifest.exists():
        proof_paths = (directory / "restore-operation.json",
                       directory / f"restore-{token}-failure.result.json",
                       directory / f"restore-{token}-cleanup.result.json")
        if any(path.is_symlink() or not path.is_file() for path in proof_paths):
            raise RuntimeError("restore_post_snapshot_recovery_closure_source_invalid")
        operation = json.loads(proof_paths[0].read_text())
        for job in closure_jobs:
            if host_guard.tagged_processes(job["token"]):
                raise RuntimeError("restore_post_snapshot_recovery_process_active")
            _validate_recovery_authority(directory, operation, proof_paths[1], proof_paths[2], job)
            child = directory / f"job-{job['token']}.result.json"
            wrapper = directory / f"restore-{token}-{job['token']}-result.json"
            if (child.is_symlink() or wrapper.is_symlink()
                    or not child.is_file() or not wrapper.is_file()):
                raise RuntimeError("restore_post_snapshot_recovery_closure_receipt_missing")
            _require_successful_job(directory, token, job)
    recovery_parent = directory / "restore-post-restore-recovery" / token
    if recovery_parent.is_symlink():
        raise RuntimeError("restore_post_snapshot_recovery_archive_symlink")
    for path in (sorted(recovery_parent.rglob("*")) if recovery_parent.exists() else []):
        if path.is_symlink():
            raise RuntimeError("restore_post_snapshot_recovery_archive_symlink")
        if path.is_file():
            relative = "post-restore-recovery/" + str(path.relative_to(recovery_parent))
            if relative not in by_path:
                raise RuntimeError("restore_post_snapshot_recovery_source_unarchived")
            archived_sources[relative] = path
    for relative, source in archived_sources.items():
        saved = archive_root / "evidence" / relative
        if relative not in by_path or archive.digest_file(source) != by_path[relative] or archive.digest_file(saved) != by_path[relative]:
            raise RuntimeError("restore_post_snapshot_recovery_source_changed")
    return archived_sources, extra_authorities, closure_only


def _remove_active_sources(directory: Path, token: str, archive_root: Path,
                           authority_path: Path, session_root: Path) -> None:
    archived_sources, extra_authorities, closure_only = _validated_active_sources(directory, token, archive_root)
    closure_manifest = archive_root / "closure" / "closure.json"
    closure_seal = archive_root / "closure" / "closure-seal.json"
    closure_published = closure_manifest.exists()
    closure_root = closure_manifest.parent
    if not closure_root.exists() and not closure_root.is_symlink():
        archive._mkdir_durable(closure_root)
    if (closure_root.is_symlink() or not closure_root.is_dir()
            or closure_root.stat().st_mode & 0o077
            or closure_manifest.is_symlink() or closure_published and not closure_manifest.is_file()
            or closure_seal.is_symlink() or closure_seal.exists() and not closure_seal.is_file()):
        raise RuntimeError("restore_post_snapshot_recovery_closure_invalid")
    if closure_seal.is_file() and json.loads(closure_seal.read_text()) != {
            "schema": 1, "token": token, "sha256": archive.digest_file(closure_manifest)}:
        raise RuntimeError("restore_post_snapshot_recovery_closure_invalid")
    archived_names = {row["path"] for row in verify_archive(archive_root, token)["files"]}
    if (closure_published and not closure_seal.is_file()
            and set(archived_sources) != archived_names):
        raise RuntimeError("restore_post_snapshot_recovery_closure_seal_missing_after_retirement_started")
    closure_jobs = [job for job in restore_process.registered_jobs(directory, token)
                    if job.get("operation") in {
                        restore_process.POST_RESTORE_RECOVERY_READBACK,
                        "post-restore-recovery-remove-container",
                        "post-restore-recovery-remove-volume",
                    }]
    closure_evidence = archive_root / "closure" / "evidence"
    if closure_published:
        for source in closure_only.values():
            saved = closure_evidence / source.name
            if (saved.is_symlink() or not saved.is_file()
                    or archive.digest_file(source) != archive.digest_file(saved)):
                raise RuntimeError("restore_post_snapshot_recovery_closure_receipt_changed")
    if not closure_published:
        operation_path = directory / "restore-operation.json"
        failure_path = directory / f"restore-{token}-failure.result.json"
        cleanup_path = directory / f"restore-{token}-cleanup.result.json"
        if any(path.is_symlink() or not path.is_file()
               for path in (operation_path, failure_path, cleanup_path)):
            raise RuntimeError("restore_post_snapshot_recovery_closure_source_invalid")
        operation = json.loads(operation_path.read_text())
        for job in closure_jobs:
            if host_guard.tagged_processes(job["token"]):
                raise RuntimeError("restore_post_snapshot_recovery_process_active")
            wrapper = directory / f"restore-{token}-{job['token']}-result.json"
            child = directory / f"job-{job['token']}.result.json"
            registration = directory / f"restore-{token}-{job['token']}-job.json"
            if not wrapper.is_file() or not child.is_file():
                raise RuntimeError("restore_post_snapshot_recovery_removal_receipt_missing")
            _validate_recovery_authority(directory, operation, failure_path, cleanup_path, job)
            _require_successful_job(directory, token, job)
            for path in (registration, child, wrapper):
                _copy_to_archive(path, closure_evidence / path.name)
    closure_rows = []
    if closure_evidence.exists():
        for path in sorted(closure_evidence.iterdir()):
            closure_rows.append({"path": path.name, "sha256": archive.digest_file(path),
                                 "bytes": path.stat().st_size})
    closure_value = {
            "schema": 1, "token": token, "status": "failed_post_restore_retired",
            "archive_sha256": archive.digest_file(archive_root / "retirement.json"),
            "container_absent": True, "volume_absent": True, "main_baseline_unchanged": True,
            "closure_receipts": closure_rows, "completed_at": time.time()}
    if not closure_published:
        _write_once(closure_manifest.parent, closure_manifest.name, closure_value)
    else:
        existing = json.loads(closure_manifest.read_text())
        if any(existing.get(key) != value for key, value in closure_value.items()
               if key != "completed_at"):
            raise RuntimeError("restore_post_snapshot_recovery_closure_conflict")
    if not closure_seal.exists():
        _write_once(closure_manifest.parent, closure_seal.name, {
            "schema": 1, "token": token, "sha256": archive.digest_file(closure_manifest)})
    else:
        seal = json.loads(closure_seal.read_text())
        if seal != {"schema": 1, "token": token, "sha256": archive.digest_file(closure_manifest)}:
            raise RuntimeError("restore_post_snapshot_recovery_closure_invalid")
    for source in archived_sources.values():
        source.unlink()
    for authority in extra_authorities:
        authority.unlink()
    for job in closure_jobs:
        for source in (directory / f"restore-{token}-{job['token']}-job.json",
                       directory / f"restore-{token}-{job['token']}-result.json",
                       directory / f"job-{job['token']}.result.json"):
            source.unlink(missing_ok=True)
    for authority in directory.glob(f"restore-{token}-post-restore-authority-*.json"):
        authority.unlink(missing_ok=True)
    recovery_parent = directory / "restore-post-restore-recovery" / token
    if recovery_parent.exists():
        shutil.rmtree(recovery_parent)
    restore_root = directory / "restore" / token
    if restore_root.exists():
        if restore_root.is_symlink() or not restore_root.is_dir():
            raise RuntimeError("restore_post_snapshot_recovery_restore_root_invalid")
        shutil.rmtree(restore_root)
    archive._fsync_directory(directory)
