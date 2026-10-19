"""Exact owned-store ordering, partial failure retention, and no restore claims."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import time
from uuid import uuid4

import pytest

from .. import paired_backup as backup
from ..backup_readbacks import native_pending
from ..operations import Lease, create_record


def test_database_dump_is_create_only_custom_format_with_owners_and_grants(
    tmp_path, monkeypatch
):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if "pg_dump" in command:
            kwargs["stdout"].write(b"controlled-custom-archive")
        else:
            assert kwargs["stdin"].read() == b"controlled-custom-archive"
        return SimpleNamespace(
            returncode=0, stdout=b"controlled archive table of contents"
        )

    monkeypatch.setattr(backup.subprocess, "run", run)
    path = tmp_path / "ade.dump"
    result = backup.dump_database(path, "owned-db", "owned-admin", "owned-database")
    assert calls == [
        [
            "docker",
            "exec",
            "owned-db",
            "pg_dump",
            "-U",
            "owned-admin",
            "-d",
            "owned-database",
            "-Fc",
        ],
        ["docker", "exec", "-i", "owned-db", "pg_restore", "--list"],
    ]
    assert result["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        backup.dump_database(path, "owned-db", "owned-admin", "owned-database")
    assert len(calls) == 2


@pytest.mark.parametrize("fault", [None, "native_dump", "closeout"])
def test_two_store_backup_has_no_writers_and_always_closes_owned_resources(
    tmp_path, monkeypatch, fault
):
    events = []
    root = tmp_path / "activation"
    now = int(time.time())
    lease = Lease(
        "ade-hindsight-integration-backup-test",
        str(uuid4()),
        "a" * 40,
        now - 1,
        now + 3600,
        now + 7200,
        "/mnt/projects",
        (),
    )
    lease.save(root)
    product_run = root / "evidence/run"
    create_record(
        product_run / "invocation.json",
        {"source": {"source_revision": lease.source_revision}},
    )
    environment = tmp_path / "private.env"
    environment.write_text(
        "INTEGRATION_ADE_OPERATOR_KEY=never-record-key\nINTEGRATION_HINDSIGHT_KEY=never-record-key\nINTEGRATION_ROUTER_KEY=never-record-key\n"
    )
    code = (
        tmp_path / ("b" * 40) / "workflows/evals/hindsight_integration/paired_backup.py"
    )
    code.parent.mkdir(parents=True)
    code.write_text("controlled controller source")
    alembic = code.parents[3] / "services/ade-api/alembic.ini"
    alembic.parent.mkdir(parents=True)
    alembic.write_text(
        "[alembic]\nversion_table_schema=ade\nversion_table=ade_alembic_version\n"
    )
    monkeypatch.setattr(backup, "__file__", str(code))
    rows = [
        {
            "id": name,
            "state": "running",
            "image": "sha256:" + "c" * 64,
            "auto_remove": False,
            "labels": {
                "com.docker.compose.service": name,
                "com.docker.compose.project": lease.project,
                "io.ade.integration.activation": lease.activation_id,
                "io.ade.integration.source": lease.source_revision,
            },
        }
        for name in (
            "ade-web",
            "ade-api",
            "ade-worker",
            "hindsight",
            "model-router",
            "fault-proxy",
            "ade-db",
            "db",
        )
    ]

    class Docker:
        def owned(self, _lease):
            return rows

        def snapshot(self, _ids):
            return []

        def stop(self, identity):
            if fault == "closeout" and identity == "db":
                raise RuntimeError("controlled_stop_failure")
            events.append(("stop", identity))
            next(row for row in rows if row["id"] == identity)["state"] = "exited"

    def dump(output, container, user, database):
        assert {row["id"] for row in rows if row["state"] == "running"} == {
            "ade-db",
            "db",
        }
        events.append(("dump", container))
        if fault == "native_dump" and container == "db":
            raise RuntimeError("controlled_second_dump_failure")
        output.write_bytes(b"controlled archive")
        return {
            "file": output.name,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "bytes": output.stat().st_size,
        }

    monkeypatch.setattr(backup, "DockerOperations", Docker)
    monkeypatch.setattr(backup, "healthy_lease", lambda *args: None)
    monkeypatch.setattr(backup, "require_configuration", lambda *args: None)
    monkeypatch.setattr(backup, "product_readbacks", lambda *args: [])
    monkeypatch.setattr(
        backup, "sql", lambda *args: "" if "bank_id" in args[-1] else "20261019_0010"
    )
    monkeypatch.setattr(
        backup,
        "native_pending",
        lambda *args: {"pending": [], "failed": [], "incomplete_banks": []},
    )
    monkeypatch.setattr(
        backup,
        "router_snapshot",
        lambda *args: {"records": [], "missing_outcome_request_ids": []},
    )
    monkeypatch.setattr(backup, "dump_database", dump)
    monkeypatch.setattr(backup.time, "sleep", lambda seconds: None)
    output = root / "evidence/paired-01"
    if fault:
        with pytest.raises(RuntimeError):
            backup.run_backup(
                root,
                environment,
                output,
                controller_revision="b" * 40,
                product_run=product_run,
            )
    else:
        backup.run_backup(
            root,
            environment,
            output,
            controller_revision="b" * 40,
            product_run=product_run,
        )
    assert events[:6] == [
        ("stop", name)
        for name in (
            "ade-web",
            "ade-api",
            "ade-worker",
            "hindsight",
            "model-router",
            "fault-proxy",
        )
    ]
    assert events[6:8] == [("dump", "ade-db"), ("dump", "db")]
    closeout = json.loads((output / "closeout.json").read_text())
    assert closeout["baseline_unchanged"]
    assert bool(closeout["running_owned"]) == (fault == "closeout")
    assert (root / "closed.json").exists() and (output / "ade.dump").exists()
    if fault == "native_dump":
        assert (output / "failure.json").exists()
        assert not (output / "paired-backup.json").exists()
    else:
        assert (
            json.loads((output / "paired-backup.json").read_text())["restore_verified"]
            is False
        )
    assert not any(
        b"never-record-key" in path.read_bytes()
        for path in output.rglob("*.*")
        if path.is_file()
    )


def test_native_pending_preserves_failures_unknown_states_and_incomplete_pages():
    class Reads:
        def get(self, service, path):
            assert service == "native" and "limit=100" in path
            return {
                "total": 3,
                "operations": [
                    {"operation_id": "failed", "status": "failed"},
                    {"operation_id": "active", "status": "future-state"},
                ],
            }

    result = native_pending(Reads(), ["ade-" + "a" * 32])
    assert [row["operation_id"] for row in result["pending"]] == ["active"]
    assert [row["operation_id"] for row in result["failed"]] == ["failed"]
    assert result["incomplete_banks"] == ["ade-" + "a" * 32]


def test_unstaged_controller_cannot_quiesce_a_stack(tmp_path):
    with pytest.raises(ValueError, match="staged committed"):
        backup.run_backup(
            tmp_path,
            tmp_path / "private.env",
            tmp_path / "out",
            controller_revision="a" * 40,
            product_run=tmp_path / "run",
        )


def test_migration_identity_comes_from_bound_source_configuration(tmp_path):
    config = tmp_path / "services/ade-api/alembic.ini"
    config.parent.mkdir(parents=True)
    config.write_text(
        "[alembic]\nversion_table_schema=owned\nversion_table=custom_revision\n"
    )
    assert (
        backup.migration_head_query(tmp_path)
        == 'SELECT version_num FROM "owned"."custom_revision" ORDER BY version_num;'
    )
    config.write_text(
        "[alembic]\nversion_table_schema=owned\nversion_table=invalid; DROP SCHEMA ade\n"
    )
    with pytest.raises(ValueError, match="unsafe_alembic"):
        backup.migration_head_query(tmp_path)


def test_actual_migration_identity_does_not_assume_alembic_default():
    source = Path(__file__).resolve().parents[4]
    assert (
        backup.migration_head_query(source)
        == 'SELECT version_num FROM "ade"."ade_alembic_version" ORDER BY version_num;'
    )
