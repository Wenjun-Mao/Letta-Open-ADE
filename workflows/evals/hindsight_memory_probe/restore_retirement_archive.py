"""Private byte-preserving archive and recovery for restore retirement."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path

from .receipts import ReceiptStore


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _mkdir_durable(path: Path) -> None:
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    for directory in reversed(missing):
        _fsync_directory(directory)
        _fsync_directory(directory.parent)


def _source_files(directory: Path, token: str) -> dict[str, Path]:
    if any(directory.glob(".*.partial")):
        raise RuntimeError("restore_retirement_partial_receipt_present")
    sources = {}
    for name in ("restore-operation.json", "restore-operation-seal.json"):
        path = directory / name
        if path.exists():
            if not path.is_file() or path.is_symlink():
                raise RuntimeError("restore_retirement_source_invalid")
            sources[name] = path
    pattern = re.compile(rf"restore-{re.escape(token)}-.*\.json")
    for path in directory.iterdir():
        if pattern.fullmatch(path.name):
            if path.is_symlink() or not path.is_file():
                raise RuntimeError("restore_retirement_source_invalid")
            sources[path.name] = path
    restore_root = directory / "restore" / token
    if restore_root.exists():
        if restore_root.is_symlink() or not restore_root.is_dir():
            raise RuntimeError("restore_retirement_source_invalid")
        for path in restore_root.rglob("*"):
            if path.is_symlink():
                raise RuntimeError("restore_retirement_source_invalid")
            if path.is_file():
                sources[
                    str(Path("restore") / token / path.relative_to(restore_root))
                ] = path
            elif not path.is_dir():
                raise RuntimeError("restore_retirement_source_invalid")
    for job in _restore_jobs(directory, token):
        result = directory / f"job-{job['token']}.result.json"
        if result.exists():
            if result.is_symlink() or not result.is_file():
                raise RuntimeError("restore_retirement_source_invalid")
            sources[result.name] = result
    return sources


def _restore_jobs(directory: Path, token: str) -> list[dict]:
    from .restore_process import registered_jobs

    return registered_jobs(directory, token)


def _copy_immutable(source: Path, destination: Path) -> None:
    _mkdir_durable(destination.parent)
    if destination.exists():
        if destination.is_symlink() or digest_file(destination) != digest_file(source):
            raise RuntimeError("restore_retirement_archive_conflict")
        return
    temporary = destination.parent / f".{uuid.uuid4().hex}.partial"
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    try:
        with os.fdopen(descriptor, "wb") as output, source.open("rb") as input_file:
            shutil.copyfileobj(input_file, output)
            output.flush()
            os.fsync(output.fileno())
            os.fchmod(output.fileno(), 0o400)
        os.link(temporary, destination)
        os.unlink(temporary)
        _fsync_directory(destination.parent)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def archive_attempt(
    directory: Path, diagnosis_path: Path, operation: dict, diagnosis: dict
) -> Path:
    token = operation["token"]
    root = directory / "restore-retired" / token
    evidence = root / "evidence"
    _mkdir_durable(root)
    if any(
        not (directory / name).is_file()
        for name in ("restore-operation.json", "restore-operation-seal.json")
    ):
        raise RuntimeError("restore_retirement_source_missing")
    sources = _source_files(directory, token)
    sources["diagnosis.json"] = diagnosis_path
    manifest_files = []
    for relative, source in sorted(sources.items()):
        digest = digest_file(source)
        target = evidence / relative
        _copy_immutable(source, target)
        if digest_file(target) != digest:
            raise RuntimeError("restore_retirement_archive_hash_mismatch")
        manifest_files.append(
            {"path": relative, "sha256": digest, "bytes": source.stat().st_size}
        )
    manifest = {
        "schema": 1,
        "token": token,
        "status": "retired_failed_before_creation",
        "operation_sha256": digest_file(directory / "restore-operation.json"),
        "diagnosis_sha256": digest_file(diagnosis_path),
        "diagnosis": diagnosis,
        "files": manifest_files,
        "created_at": time.time(),
    }
    manifest_path = root / "retirement.json"
    seal_path = root / "retirement-seal.json"
    if manifest_path.exists() or seal_path.exists():
        if not manifest_path.is_file() or not seal_path.is_file():
            raise RuntimeError("restore_retirement_publication_incomplete")
        existing = json.loads(manifest_path.read_text())
        if existing != manifest or json.loads(seal_path.read_text()).get(
            "sha256"
        ) != digest_file(manifest_path):
            raise RuntimeError("restore_retirement_archive_conflict")
    else:
        ReceiptStore(root).write(manifest_path.name, manifest)
        ReceiptStore(root).write(
            seal_path.name,
            {"schema": 1, "token": token, "sha256": digest_file(manifest_path)},
        )
        manifest_path.chmod(0o400)
        seal_path.chmod(0o400)
        _fsync_directory(root)
        _fsync_directory(root.parent)
    return root


def remove_sources(directory: Path, token: str, retirement_root: Path) -> None:
    manifest = json.loads((retirement_root / "retirement.json").read_text())
    evidence = retirement_root / "evidence"
    by_path = {row["path"]: row["sha256"] for row in manifest["files"]}
    sources = _source_files(directory, token)
    for relative, source in sources.items():
        if relative not in by_path or digest_file(source) != by_path[relative]:
            raise RuntimeError("restore_retirement_source_changed")
        archived = evidence / relative
        if (
            archived.is_symlink()
            or not archived.is_file()
            or digest_file(archived) != by_path[relative]
        ):
            raise RuntimeError("restore_retirement_archive_invalid")
    for relative, source in sources.items():
        source.unlink()
    _fsync_directory(directory)
    restore_root = directory / "restore" / token
    if restore_root.exists():
        shutil.rmtree(restore_root)
        _fsync_directory(restore_root.parent)
    marker = directory / "restore-retirement-active.json"
    if marker.exists():
        value = json.loads(marker.read_text())
        if value.get("token") != token:
            raise RuntimeError("restore_retirement_active_marker_mismatch")
        marker.unlink()
        _fsync_directory(directory)


def verify_archive(root: Path, token: str) -> dict:
    manifest_path, seal_path = root / "retirement.json", root / "retirement-seal.json"
    if (
        not manifest_path.is_file()
        or manifest_path.is_symlink()
        or not seal_path.is_file()
        or seal_path.is_symlink()
    ):
        raise RuntimeError("restore_retirement_publication_incomplete")
    manifest = json.loads(manifest_path.read_text())
    seal = json.loads(seal_path.read_text())
    if (
        manifest.get("schema") != 1
        or manifest.get("status") != "retired_failed_before_creation"
        or manifest.get("token") != token
        or seal.get("token") != token
        or seal.get("sha256") != digest_file(manifest_path)
    ):
        raise RuntimeError("restore_retirement_seal_invalid")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError("restore_retirement_archive_invalid")
    if len({row.get("path") for row in files if isinstance(row, dict)}) != len(files):
        raise RuntimeError("restore_retirement_archive_invalid")
    for row in files:
        relative = Path(row.get("path", ""))
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise RuntimeError("restore_retirement_archive_invalid")
        archived = root / "evidence" / relative
        if (
            archived.is_symlink()
            or not archived.is_file()
            or digest_file(archived) != row.get("sha256")
            or archived.stat().st_size != row.get("bytes")
        ):
            raise RuntimeError("restore_retirement_archive_invalid")
    by_path = {row["path"]: row for row in files}
    operation_path = root / "evidence" / "restore-operation.json"
    seal_path = root / "evidence" / "restore-operation-seal.json"
    diagnosis_path = root / "evidence" / "diagnosis.json"
    if not all(path.is_file() for path in (operation_path, seal_path, diagnosis_path)):
        raise RuntimeError("restore_retirement_archive_invalid")
    operation_bytes = operation_path.read_bytes()
    operation = json.loads(operation_bytes)
    operation_hash = hashlib.sha256(operation_bytes).hexdigest()
    diagnosis = json.loads(diagnosis_path.read_text())
    diagnosis_fields = {
        "schema",
        "kind",
        "failure_stage",
        "failure_code",
        "token",
        "operation_sha256",
        "archive_sha256",
        "snapshot_sha256",
        "selection_sha256",
        "failure_result_sha256",
        "no_create_intent",
        "no_create_result",
        "controller_gone",
        "registered_processes_gone",
        "restore_container_absent",
        "restore_volume_absent",
        "main_stopped",
        "baseline_unchanged",
    }
    if (
        operation.get("token") != token
        or manifest.get("operation_sha256") != operation_hash
        or by_path["restore-operation.json"].get("sha256") != operation_hash
        or json.loads(seal_path.read_text()).get("sha256") != operation_hash
        or manifest.get("diagnosis_sha256") != digest_file(diagnosis_path)
        or manifest.get("diagnosis") != diagnosis
        or by_path["diagnosis.json"].get("sha256") != digest_file(diagnosis_path)
        or set(diagnosis) != diagnosis_fields
        or diagnosis.get("schema") != 1
        or diagnosis.get("token") != token
        or diagnosis.get("operation_sha256") != operation_hash
        or diagnosis.get("kind") != "failed_before_creation"
        or diagnosis.get("failure_stage") != "controller-start"
        or diagnosis.get("failure_code") != "pre_creation_controller_admission_failure"
        or any(
            diagnosis.get(key) is not True
            for key in (
                "no_create_intent",
                "no_create_result",
                "controller_gone",
                "registered_processes_gone",
                "restore_container_absent",
                "restore_volume_absent",
                "main_stopped",
                "baseline_unchanged",
            )
        )
        or diagnosis.get("archive_sha256") != operation.get("archive", {}).get("sha256")
        or diagnosis.get("snapshot_sha256")
        != operation.get("snapshot", {}).get("sha256")
        or diagnosis.get("selection_sha256")
        != operation.get("selection", {}).get("sha256")
    ):
        raise RuntimeError("restore_retirement_archive_invalid")
    failure_path = root / "evidence" / f"restore-{token}-failure.result.json"
    if not failure_path.is_file() or digest_file(failure_path) != diagnosis.get(
        "failure_result_sha256"
    ):
        raise RuntimeError("restore_retirement_archive_invalid")
    failure = json.loads(failure_path.read_text())
    if (
        failure.get("token") != token
        or failure.get("status") != "failed"
        or failure.get("stage") != "controller-start"
    ):
        raise RuntimeError("restore_retirement_archive_invalid")
    return manifest


def publish_active_marker(directory: Path, token: str, root: Path) -> None:
    marker = directory / "restore-retirement-active.json"
    value = {
        "schema": 1,
        "token": token,
        "retirement_sha256": digest_file(root / "retirement.json"),
    }
    if marker.exists():
        if marker.is_symlink() or json.loads(marker.read_text()) != value:
            raise RuntimeError("restore_retirement_active_marker_conflict")
        return
    ReceiptStore(directory).write(marker.name, value)
    marker.chmod(0o400)
    _fsync_directory(directory)


def prepare_next_attempt(directory: Path) -> bool:
    """Finish only a fully sealed retirement, leaving incomplete attempts blocked."""
    operation = directory / "restore-operation.json"
    marker = directory / "restore-retirement-active.json"
    if marker.exists():
        if marker.is_symlink():
            raise RuntimeError("restore_retirement_active_marker_invalid")
        marker_value = json.loads(marker.read_text())
        token = marker_value.get("token")
        if not isinstance(token, str) or not re.fullmatch(r"[a-f0-9]{32}", token):
            raise RuntimeError("restore_retirement_active_marker_invalid")
        if operation.is_file():
            from .restore import read_operation

            if read_operation(directory)["token"] != token:
                raise RuntimeError("restore_retirement_active_marker_mismatch")
    elif operation.is_file():
        from .restore import read_operation

        value = read_operation(directory)
        token = value["token"]
    else:
        return False
    root = directory / "restore-retired" / token
    manifest_path = root / "retirement.json"
    if not manifest_path.is_file():
        return False
    verify_archive(root, token)
    if marker.exists() and marker_value.get("retirement_sha256") != digest_file(
        manifest_path
    ):
        raise RuntimeError("restore_retirement_active_marker_mismatch")
    elif not marker.exists():
        return False
    remove_sources(directory, token, root)
    return True


def validate_retired_history(directory: Path) -> None:
    retired_root = directory / "restore-retired"
    if not retired_root.exists():
        return
    if retired_root.is_symlink() or not retired_root.is_dir():
        raise RuntimeError("restore_retirement_history_invalid")
    for root in retired_root.iterdir():
        if (
            root.is_symlink()
            or not root.is_dir()
            or not re.fullmatch(r"[a-f0-9]{32}", root.name)
        ):
            raise RuntimeError("restore_retirement_history_invalid")
        manifest = verify_archive(root, root.name)
        expected = {root / "retirement.json", root / "retirement-seal.json"}
        expected.update(root / "evidence" / row["path"] for row in manifest["files"])
        actual = {path for path in root.rglob("*") if path.is_file()}
        if actual != expected or any(path.is_symlink() for path in root.rglob("*")):
            raise RuntimeError("restore_retirement_history_invalid")
