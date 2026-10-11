"""Capture canonical read-only table state from an exact disposable restore DB."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from . import candidate_database, canonical_snapshot
from .receipts import ReceiptStore


SCHEMA_SQL = ("SELECT jsonb_build_object('schemas',(SELECT COALESCE(jsonb_agg(jsonb_build_object('name',nspname,'owner',r.rolname) ORDER BY nspname),'[]'::jsonb) FROM pg_namespace n JOIN pg_roles r ON r.oid=nspowner),"
              "'extensions',(SELECT COALESCE(jsonb_agg(jsonb_build_object('name',extname,'version',extversion) ORDER BY extname),'[]'::jsonb) FROM pg_extension),"
              "'alembic',(SELECT COALESCE(jsonb_agg(to_jsonb(a) ORDER BY to_jsonb(a)::text),'[]'::jsonb) FROM public.alembic_version a))::text")


def table_query(table: str) -> str:
    return canonical_snapshot.table_query(table)


def allowed_queries() -> set[str]:
    return {"SELECT current_database()", SCHEMA_SQL,
            *(table_query(table) for table in candidate_database.SNAPSHOT_TABLES)}


def psql_text(directory: Path, operation: dict, container: dict, query: str,
              run_command, timeout: int = 15) -> str:
    path = Path(operation["restore_root"]) / f"query-{uuid.uuid4().hex}.partial"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    command = ["docker", "exec", "-i", container["Id"], "psql", "-U", "hindsight_probe",
               "-d", "hindsight_probe", "-At", "-c", query]
    try:
        with os.fdopen(descriptor, "wb") as output:
            code = run_command(command, timeout=timeout,
                               operation_label="restore-snapshot-query", stdout=output)
            output.flush()
            os.fsync(output.fileno())
        if code != 0:
            raise RuntimeError("restore_snapshot_query_failed")
        return path.read_text(encoding="utf-8").strip()
    finally:
        path.unlink(missing_ok=True)


def snapshot(directory: Path, operation: dict, container: dict, store: ReceiptStore,
             run_command) -> dict:
    path = Path(operation["restore_root"]) / "canonical-snapshot.json"
    if path.exists():
        value = json.loads(path.read_text())
        root = Path(operation["restore_root"])
        for entry in value.get("tables", {}).values():
            file = root / entry["file"]
            if not file.is_file() or candidate_database.sha256_file(file) != entry["sha256"]:
                raise RuntimeError("restore_snapshot_receipt_corrupt")
        return value
    if psql_text(directory, operation, container, "SELECT current_database()", run_command) != "hindsight_probe":
        raise RuntimeError("restore_database_name_mismatch")
    root = Path(operation["restore_root"])
    paths = {}
    for table in candidate_database.SNAPSHOT_TABLES:
        query = table_query(table)
        target = root / f"{table}.jsonl"
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as output:
            code = run_command(["docker", "exec", "-i", container["Id"], "psql", "-U", "hindsight_probe",
                                "-d", "hindsight_probe", "-At", "-c", query],
                               timeout=45, operation_label="restore-snapshot-table-" + table,
                               stdout=output)
            output.flush()
            os.fsync(output.fileno())
        if code != 0:
            raise RuntimeError("restore_snapshot_table_query_failed")
        paths[table] = {"file": target.name, "sha256": candidate_database.sha256_file(target),
                        "bytes": target.stat().st_size}

    schema_path = root / "schema-extensions.json"
    schema = psql_text(directory, operation, container, SCHEMA_SQL, run_command)
    try:
        json.loads(schema)
    except ValueError as exc:
        raise RuntimeError("restore_schema_snapshot_invalid") from exc
    descriptor = os.open(schema_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(schema)
        output.flush()
        os.fsync(output.fileno())
    paths["schema_extensions"] = {"file": schema_path.name,
        "sha256": candidate_database.sha256_file(schema_path), "bytes": schema_path.stat().st_size}
    result = {"schema": 1, "container_id": container["Id"], "image_id": container["Image"],
              "project": operation["compose"]["project"], "volume": operation["compose"]["volume"],
              "database": "hindsight_probe", "tables": paths,
              "captured_at": __import__("time").time()}
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n")
        output.flush()
        os.fsync(output.fileno())
    return result
