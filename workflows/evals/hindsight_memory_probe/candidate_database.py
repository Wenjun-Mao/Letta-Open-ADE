"""Exact candidate PostgreSQL snapshot and exclusive logical archive handling."""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from pathlib import Path

from . import canonical_snapshot, epochs, host_guard as host
from .receipts import ReceiptStore

SNAPSHOT_TABLES = canonical_snapshot.SNAPSHOT_TABLES


def db_container(directory: Path, registry: dict, admitted: dict) -> dict:
    candidates = host.candidate_containers(host.containers(), epochs.effective_registry(directory, registry))
    expected_workdir = str(Path(admitted["release_path"]) / "workflows/evals/hindsight_memory_probe")
    expected = [row for row in admitted["containers"] if row["service"] == "db"
                and row["working_dir"] == expected_workdir]
    if len(expected) != 1:
        raise RuntimeError("candidate_database_identity_ambiguous")
    row = expected[0]
    current = next((item for item in candidates if item["Id"] == row["id"]), None)
    if current is None or current["State"]["Status"] != "running" or identity_projection(current) | {"status": row["status"]} != row:
        raise RuntimeError("candidate_database_identity_invalid")
    running_databases = [item["Id"] for item in candidates
                         if item["Config"]["Labels"]["com.docker.compose.service"] == "db"
                         and item["State"]["Status"] == "running"]
    if running_databases != [row["id"]]:
        raise RuntimeError("candidate_database_overlap_detected")
    if not any(mount.get("Name") == "ade-hindsight-probe_db-data" and mount.get("Destination") == "/var/lib/postgresql/data" for mount in current.get("Mounts", [])):
        raise RuntimeError("candidate_database_volume_invalid")
    return current


def identity_projection(container: dict) -> dict:
    labels = container.get("Config", {}).get("Labels") or {}
    return {
        "id": container["Id"], "image_id": container["Image"],
        "started_at": container["State"]["StartedAt"], "status": container["State"]["Status"],
        "service": labels.get("com.docker.compose.service"),
        "project": labels.get("com.docker.compose.project"),
        "working_dir": labels.get("com.docker.compose.project.working_dir"),
        "config_files": labels.get("com.docker.compose.project.config_files"),
        "oneoff": labels.get("com.docker.compose.oneoff") == "True",
    }


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def psql_text(directory: Path, registry: dict, admitted: dict, db: dict, query: str,
              run_monitored, timeout: int = 8) -> str:
    path = directory / f"finalize-{admitted['token']}-{uuid.uuid4().hex}.query.partial"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            code = run_monitored(directory, registry, epochs.active(directory, registry), admitted,
                                 ["docker", "exec", db["Id"], "psql", "-U", "hindsight_probe", "-d", "hindsight_probe", "-At", "-c", query],
                                 timeout, stdout=output, stderr=subprocess.DEVNULL)
            output.flush()
            os.fsync(output.fileno())
        if code != 0:
            raise RuntimeError("candidate_database_readback_failed")
        return path.read_text().strip()
    finally:
        path.unlink(missing_ok=True)


def operation_count(directory: Path, registry: dict, admitted: dict, run_monitored) -> int:
    counts = operation_status_counts(directory, registry, admitted, run_monitored)
    return sum(counts.get(status, 0) for status in ("pending", "processing", "deferred"))


def operation_status_counts(directory: Path, registry: dict, admitted: dict, run_monitored) -> dict:
    db = db_container(directory, registry, admitted)
    query = ("SELECT COALESCE(jsonb_object_agg(status, operation_count), '{}'::jsonb)::text "
             "FROM (SELECT status, count(*)::int AS operation_count "
             "FROM public.async_operations GROUP BY status) AS statuses")
    try:
        value = json.loads(psql_text(directory, registry, admitted, db, query, run_monitored))
        if (not isinstance(value, dict)
                or any(not isinstance(key, str) or not isinstance(count, int) or count < 0
                       for key, count in value.items())):
            raise ValueError("status_counts_invalid")
        return value
    except (TypeError, ValueError) as exc:
        raise RuntimeError("async_operation_readback_invalid") from exc


def snapshot_database(directory: Path, registry: dict, admitted: dict, store: ReceiptStore,
                      run_monitored) -> dict:
    snapshot_path = store.directory / f"finalize-{admitted['token']}-canonical-snapshot.json"
    if snapshot_path.exists():
        snapshot = json.loads(snapshot_path.read_text())
        root = store.directory / "finalization" / admitted["token"]
        for entry in snapshot["tables"].values():
            path = root / entry["file"]
            if not path.is_file() or sha256_file(path) != entry["sha256"]:
                raise RuntimeError("canonical_snapshot_receipt_corrupt")
        return snapshot
    db = db_container(directory, registry, admitted)
    root = store.directory / "finalization" / admitted["token"]
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(root, 0o700)
    current_db = psql_text(directory, registry, admitted, db, "SELECT current_database()", run_monitored)
    if current_db != "hindsight_probe":
        raise RuntimeError("candidate_database_name_mismatch")
    async_status_counts = operation_status_counts(directory, registry, admitted, run_monitored)
    if sum(async_status_counts.get(status, 0) for status in ("pending", "processing", "deferred")):
        raise RuntimeError("async_operations_not_drained_before_snapshot")
    paths = {}
    for table in SNAPSHOT_TABLES:
        sql = canonical_snapshot.table_query(table)
        target = root / f"{table}.jsonl"
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as output:
            code = run_monitored(directory, registry, epochs.active(directory, registry), admitted,
                                 ["docker", "exec", db["Id"], "psql", "-U", "hindsight_probe", "-d", "hindsight_probe", "-At", "-c", sql],
                                 20, stdout=output, stderr=subprocess.DEVNULL)
            if code != 0:
                raise RuntimeError("canonical_snapshot_query_failed")
            output.flush()
            os.fsync(output.fileno())
        paths[table] = {"file": target.name, "sha256": sha256_file(target), "bytes": target.stat().st_size}
    schema_sql = "SELECT jsonb_build_object('schemas',(SELECT COALESCE(jsonb_agg(jsonb_build_object('name',nspname,'owner',r.rolname) ORDER BY nspname),'[]'::jsonb) FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner),'extensions',(SELECT COALESCE(jsonb_agg(jsonb_build_object('name',extname,'version',extversion) ORDER BY extname),'[]'::jsonb) FROM pg_extension),'alembic',(SELECT COALESCE(jsonb_agg(to_jsonb(a) ORDER BY to_jsonb(a)::text),'[]'::jsonb) FROM public.alembic_version a))::text"
    schema_path = root / "schema-extensions.json"
    schema_fd = os.open(schema_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(schema_fd, "wb") as output:
        output.write(psql_text(directory, registry, admitted, db, schema_sql, run_monitored).encode())
        output.flush()
        os.fsync(output.fileno())
    paths["schema_extensions"] = {"file": schema_path.name, "sha256": sha256_file(schema_path), "bytes": schema_path.stat().st_size}
    selection_reference = admitted.get("restart_selection", {"status": "absent"})
    scope = {"status": "absent"}
    if selection_reference.get("status") == "frozen":
        selection_path = directory.parent / "restart-selection.json"
        if sha256_file(selection_path) != selection_reference["sha256"]:
            raise RuntimeError("restart_selection_changed_after_admission")
        from .restart_selection import read_selection

        read_selection(selection_path)
        restart_reference = admitted.get("restart_readback", {"status": "absent"})
        if restart_reference.get("status") == "completed":
            scope = {
                "status": "public_readback_bound",
                "selection_sha256": restart_reference["selection_sha256"],
                "selection_file_sha256": restart_reference["selection_file_sha256"],
                "restart_readback_sha256": restart_reference["sha256"],
                "before_file_sha256": restart_reference["before"]["sha256"],
                "before_snapshot_sha256": restart_reference["before"]["content_sha256"],
                "after_file_sha256": restart_reference["after"]["sha256"],
                "after_snapshot_sha256": restart_reference["after"]["content_sha256"],
            }
        else:
            scope = {"status": "frozen_selection_without_restart_proof",
                     "selection_file_sha256": selection_reference["sha256"]}
    scope_path = root / "scope-eligibility.json"
    scope_fd = os.open(scope_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(scope_fd, "wb") as output:
        output.write((json.dumps(scope, sort_keys=True, separators=(",", ":")) + "\n").encode())
        output.flush()
        os.fsync(output.fileno())
    paths["scope_eligibility"] = {"file": scope_path.name, "sha256": sha256_file(scope_path), "bytes": scope_path.stat().st_size}
    result = {"container_id": db["Id"], "image_id": db["Image"], "database": current_db,
              "volume": "ade-hindsight-probe_db-data", "tables": paths,
              "async_operation_status_counts": async_status_counts}
    store.write(f"finalize-{admitted['token']}-canonical-snapshot.json", result)
    return result


def dump_database(directory: Path, registry: dict, admitted: dict, snapshot: dict,
                  store: ReceiptStore, run_monitored) -> dict:
    db = db_container(directory, registry, admitted)
    if psql_text(directory, registry, admitted, db, "SELECT current_database()", run_monitored) != "hindsight_probe":
        raise RuntimeError("candidate_database_name_mismatch")
    root = store.directory / "finalization" / admitted["token"]
    staging, final = root / "candidate.dump.partial", root / "candidate.dump"
    stderr_path = root / "pg_dump.stderr.partial"
    result_path = store.directory / f"finalize-{admitted['token']}-dump-result.json"
    if result_path.exists():
        result = json.loads(result_path.read_text())
        if not final.is_file() or sha256_file(final) != result["sha256"]:
            raise RuntimeError("candidate_dump_receipt_corrupt")
        return result
    if final.exists():
        if final.stat().st_size <= 0:
            raise RuntimeError("candidate_dump_publication_invalid")
        with final.open("rb") as archive:
            listing = run_monitored(directory, registry, epochs.active(directory, registry), admitted,
                                    ["docker", "exec", "-i", db["Id"], "pg_restore", "--list"], 30,
                                    stdin=archive, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if listing != 0:
            raise RuntimeError("candidate_dump_toc_invalid")
        result = build_dump_result(final, db, snapshot, admitted)
        store.write(result_path.name, result)
        return result
    if staging.exists() or stderr_path.exists():
        raise RuntimeError("candidate_dump_incomplete_artifact_preserved")
    fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    err_fd = os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    command = ["docker", "exec", "-i", db["Id"], "pg_dump", "-U", "hindsight_probe", "-d", "hindsight_probe",
               "-Fc", "--no-owner", "--no-acl", "--lock-wait-timeout=10000"]
    try:
        with os.fdopen(fd, "wb") as output, os.fdopen(err_fd, "wb") as diagnostics:
            return_code = run_monitored(directory, registry, epochs.active(directory, registry), admitted,
                                        command, admitted["dump_timeout"], stdout=output, stderr=diagnostics)
            output.flush()
            os.fsync(output.fileno())
            diagnostics.flush()
            os.fsync(diagnostics.fileno())
    except RuntimeError as exc:
        if str(exc) == "finalization_process_deadline_elapsed":
            raise RuntimeError("candidate_dump_timeout") from exc
        raise
    if return_code != 0 or staging.stat().st_size <= 0:
        raise RuntimeError("candidate_dump_failed")
    with staging.open("rb") as archive:
        listing = run_monitored(directory, registry, epochs.active(directory, registry), admitted,
                                ["docker", "exec", "-i", db["Id"], "pg_restore", "--list"], 30,
                                stdin=archive, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if listing != 0:
        raise RuntimeError("candidate_dump_toc_invalid")
    os.link(staging, final, follow_symlinks=False)
    fsync_directory(root)
    staging.unlink()
    stderr_path.unlink()
    result = build_dump_result(final, db, snapshot, admitted)
    store.write(result_path.name, result)
    return result


def build_dump_result(final: Path, db: dict, snapshot: dict, admitted: dict) -> dict:
    return {"archive": final.name, "bytes": final.stat().st_size, "sha256": sha256_file(final),
            "container_id": db["Id"], "image_id": db["Image"], "volume": snapshot["volume"],
            "database": snapshot["database"], "registry_sha256": admitted["registry_sha256"],
            "epoch_sha256": admitted["epoch_sha256"], "restart_readback": admitted["restart_readback"],
            "toc_valid": True, "published_at": time.time()}


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
