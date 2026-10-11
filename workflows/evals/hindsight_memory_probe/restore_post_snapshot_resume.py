"""Continue a sealed failed-attempt retirement under a fresh authority."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from . import restore, restore_cleanup, restore_database as db
from . import restore_cleanup_recovery_contract
from . import restore_retirement_archive as archive
from .restore_post_snapshot_archive import (
    _copy_to_archive, _remove_active_sources, _validated_active_sources, verify_archive,
)
from .restore_post_snapshot_contract import _container_identity, _sha, _write_once


def resume_archived_retirement(directory: Path, operation: dict, authority_path: Path,
                               authority: dict, source_sha: str, proof: dict,
                               archive_root: Path, run_command) -> dict:
    """Verify and finish exact-container/volume removal after a sealed capture."""
    token = operation["token"]
    manifest = verify_archive(archive_root, token, require_seal=False)
    if (manifest.get("operation_sha256") != authority["operation_sha256"]
            or manifest.get("failure_sha256") != authority["failure_sha256"]):
        raise RuntimeError("restore_post_snapshot_recovery_archive_binding_invalid")
    archive_seal = archive_root / "retirement-seal.json"
    expected_archive_seal = {"schema": 1, "token": token,
                             "sha256": archive.digest_file(archive_root / "retirement.json")}
    if archive_seal.exists():
        if archive_seal.is_symlink() or json.loads(archive_seal.read_text()) != expected_archive_seal:
            raise RuntimeError("restore_post_snapshot_recovery_archive_seal_invalid")
    else:
        _write_once(archive_root, archive_seal.name, expected_archive_seal)
    verify_archive(archive_root, token)
    closure_root = archive_root / "closure"
    archive._mkdir_durable(closure_root)
    resume_parent = closure_root / "resumptions"
    resume_parent.mkdir(mode=0o700, exist_ok=True)
    resume_root = resume_parent / authority["admission_token"]
    resume_root.mkdir(mode=0o700, exist_ok=True)
    if (closure_root.is_symlink() or closure_root.stat().st_mode & 0o077
            or resume_parent.is_symlink() or resume_parent.stat().st_mode & 0o077
            or resume_root.is_symlink() or not resume_root.is_dir()
            or resume_root.stat().st_mode & 0o077):
        raise RuntimeError("restore_post_snapshot_recovery_resume_root_invalid")
    if any(path.name not in {"readback", "resume.json", "resume-seal.json"}
           for path in resume_root.iterdir()):
        raise RuntimeError("restore_post_snapshot_recovery_resume_source_unexpected")
    readback_operation = {**operation, "cleanup_deadline": authority["deadline"],
        "_cleanup_recovery_container_id": authority["container_id"], "_post_restore_recovery": True,
        "_post_restore_recovery_admission_token": authority["admission_token"],
        "_post_restore_recovery_authority_sha256": _sha(authority_path),
        "restore_root": str(resume_root / "readback")}
    (resume_root / "readback").mkdir(mode=0o700, exist_ok=True)
    with restore_cleanup.registered_host_readback(directory, readback_operation):
        registry = json.loads((directory / "registry.json").read_text())
        db.verify_compose(operation)
        rows = db.docker_json(["docker", "inspect", authority["container_id"]])
        container = rows[0] if rows else None
        volume = db.verify_volume(readback_operation)
        restore._verify_host(directory, registry,
            {"containers": operation["finalization"]["containers"]}, prospective=False,
            post_restore_recovery_started_at=(
                container.get("State", {}).get("StartedAt") if container is not None else None))
        if container is not None:
            actual = db.restore_container({**readback_operation,
                "_post_restore_recovery_started_at": container.get("State", {}).get("StartedAt")})
            if (actual is None or actual["Id"] != proof["create"]["container_id"]
                    or actual["Image"] != proof["create"]["image_id"]):
                raise RuntimeError("restore_post_snapshot_recovery_resume_identity_invalid")
        if volume is not None:
            if (volume.get("Name") != authority["volume"]
                    or restore_cleanup_recovery_contract._volume_identity(volume)
                       != proof["create"].get("volume_identity")):
                raise RuntimeError("restore_post_snapshot_recovery_resume_volume_invalid")
    commands = []
    if container is not None:
        if container.get("State", {}).get("Status") == "running":
            commands.append(["docker", "stop", "--time", "20", authority["container_id"]])
        commands.append(["docker", "rm", authority["container_id"]])
    if volume is not None:
        commands.append(["docker", "volume", "rm", authority["volume"]])
    request = {"schema": 1, "kind": "failed_post_restore_retirement_resume",
        "token": token, "admission_token": authority["admission_token"],
        "authority_sha256": _sha(authority_path), "operation_sha256": authority["operation_sha256"],
        "recovery_source_sha": source_sha, "deadline": authority["deadline"],
        "container_identity": None if container is None else _container_identity(container),
        "volume_identity": None if volume is None else restore_cleanup_recovery_contract._volume_identity(volume),
        "commands": commands, "created_at": time.time()}
    request_path = resume_root / "resume.json"
    if request_path.exists():
        if request_path.is_symlink() or json.loads(request_path.read_text()).get("authority_sha256") != _sha(authority_path):
            raise RuntimeError("restore_post_snapshot_recovery_resume_receipt_conflict")
    else:
        _write_once(resume_root, request_path.name, request)
    resume_seal = resume_root / "resume-seal.json"
    expected_resume_seal = {"schema": 1, "token": token, "sha256": _sha(request_path)}
    if resume_seal.exists():
        if resume_seal.is_symlink() or json.loads(resume_seal.read_text()) != expected_resume_seal:
            raise RuntimeError("restore_post_snapshot_recovery_resume_seal_conflict")
    else:
        _write_once(resume_root, resume_seal.name, expected_resume_seal)
    _validated_active_sources(directory, token, archive_root)
    operation_run = {**readback_operation, "_post_restore_recovery": True}
    if container is not None and container.get("State", {}).get("Status") == "running":
        run_command(directory, operation_run, authority["deadline"], "stop", commands.pop(0), 45)
        with restore_cleanup.registered_host_readback(directory, readback_operation):
            rows = db.docker_json(["docker", "inspect", authority["container_id"]])
            container = rows[0] if rows else None
        if container is None or container.get("State", {}).get("Status") == "running":
            raise RuntimeError("restore_post_snapshot_recovery_resume_stop_unproven")
    if container is not None:
        run_command(directory, operation_run, authority["deadline"], "remove-container", commands.pop(0), 45)
        with restore_cleanup.registered_host_readback(directory, readback_operation):
            remaining = db.restore_container(readback_operation)
        if remaining is not None:
            raise RuntimeError("restore_post_snapshot_recovery_resume_remove_container_unproven")
    if volume is not None:
        with restore_cleanup.registered_host_readback(directory, readback_operation):
            consumers = db.docker_text(["docker", "ps", "-aq", "--no-trunc", "--filter",
                                        "volume=" + authority["volume"]])
        if consumers:
            raise RuntimeError("restore_post_snapshot_recovery_resume_volume_consumer_detected")
        run_command(directory, operation_run, authority["deadline"], "remove-volume", commands[-1], 45)
    with restore_cleanup.registered_host_readback(directory, readback_operation):
        remaining_volume = db.verify_volume(readback_operation)
    if remaining_volume is not None:
        raise RuntimeError("restore_post_snapshot_recovery_resume_remove_volume_unproven")
    with restore_cleanup.registered_host_readback(directory, readback_operation):
        restore._verify_host(directory, registry,
            {"containers": operation["finalization"]["containers"]}, prospective=False)
    readback_root = resume_root / "readback"
    for path in sorted(readback_root.rglob("*")):
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise RuntimeError("restore_post_snapshot_recovery_resume_readback_invalid")
        if path.is_file():
            relative = str(path.relative_to(readback_root)).replace("/", "-")
            archive._copy_immutable(path, archive_root / "closure" / "evidence" /
                                   ("resume-" + authority["admission_token"] + "-readback-" + relative))
    shutil.rmtree(readback_root)
    _copy_to_archive(authority_path, archive_root / "closure" / "evidence" /
                     ("resume-" + authority["admission_token"] + "-authority.json"))
    for child in list(resume_root.iterdir()):
        if child.is_file():
            archive._copy_immutable(child, archive_root / "closure" / "evidence" /
                                   ("resume-" + authority["admission_token"] + "-" + child.name))
    _remove_active_sources(directory, token, archive_root, authority_path, resume_root)
    return {"status": "failed_post_restore_retired", "token": token,
            "archive": str(archive_root / "retirement.json"),
            "sha256": archive.digest_file(archive_root / "retirement.json"),
            "resumed": True}
