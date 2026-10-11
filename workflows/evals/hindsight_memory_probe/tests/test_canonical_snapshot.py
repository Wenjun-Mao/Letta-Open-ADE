"""Canonical JSONL producer contract shared by candidate and restore snapshots."""

import hashlib

import pytest

from workflows.evals.hindsight_memory_probe import (
    candidate_database, canonical_snapshot, epochs, restore_snapshot,
)
from workflows.evals.hindsight_memory_probe.receipts import ReceiptStore
from workflows.evals.hindsight_memory_probe.restore_compare import _table_rows


def test_table_query_whitelists_names_and_streams_ordered_rows():
    assert canonical_snapshot.table_query("banks") == (
        "SELECT to_jsonb(t)::text FROM public.banks AS t ORDER BY to_jsonb(t)::text")
    assert restore_snapshot.table_query("banks") == canonical_snapshot.table_query("banks")
    with pytest.raises(RuntimeError, match="table_not_allowed"):
        canonical_snapshot.table_query("banks; DROP TABLE banks")


def test_restore_snapshot_preserves_ordered_rows_and_zero_byte_empty_table(tmp_path):
    root = tmp_path / "restore"
    root.mkdir()
    operation = {"restore_root": str(root), "compose": {"project": "restore", "volume": "data"}}
    rows = b'{"a":1}\n{"b":2}\n'

    def run_command(command, *, stdout, **_kwargs):
        query = command[-1]
        if query == "SELECT current_database()":
            stdout.write(b"hindsight_probe\n")
        elif query == restore_snapshot.SCHEMA_SQL:
            stdout.write(b'{"schemas":[],"extensions":[],"alembic":[]}\n')
        elif query in {canonical_snapshot.table_query(table)
                       for table in canonical_snapshot.SNAPSHOT_TABLES}:
            if query == canonical_snapshot.table_query("banks"):
                stdout.write(rows)
            # PostgreSQL -At emits no bytes when an ordered row query returns no rows.
        else:
            raise AssertionError(f"unexpected snapshot query: {query}")
        return 0

    result = restore_snapshot.snapshot(tmp_path, operation, {"Id": "container", "Image": "image"},
                                      store=None, run_command=run_command)
    entries = result["tables"]
    assert (root / entries["banks"]["file"]).read_bytes() == rows
    empty = root / entries["observation_history"]["file"]
    assert empty.read_bytes() == b""
    assert entries["observation_history"]["bytes"] == 0

    parsed = _table_rows({"tables": {
        "banks": {"file": entries["banks"]["file"], "sha256": hashlib.sha256(rows).hexdigest(),
                  "bytes": len(rows)},
        "observation_history": {"file": empty.name, "sha256": hashlib.sha256(b"").hexdigest(),
                                "bytes": 0},
    }}, root)
    assert parsed["banks"] == [{"a": 1}, {"b": 2}]
    assert parsed["observation_history"] == []


def test_candidate_snapshot_uses_shared_query_and_preserves_empty_table(tmp_path, monkeypatch):
    store = ReceiptStore(tmp_path / "receipts")
    admitted = {"token": "a" * 32, "restart_selection": {"status": "absent"}}
    monkeypatch.setattr(candidate_database, "db_container", lambda *_: {"Id": "container", "Image": "image"})
    monkeypatch.setattr(candidate_database, "psql_text", lambda *_args, **_kwargs: "hindsight_probe")
    monkeypatch.setattr(candidate_database, "operation_status_counts", lambda *_: {})
    monkeypatch.setattr(epochs, "active", lambda *_: {"sha256": "epoch", "index": 1})
    rows = b'{"a":1}\n{"b":2}\n'
    queries = []

    def monitored(_directory, _registry, _epoch, _admitted, command, _timeout, *, stdout, **_kwargs):
        query = command[-1]
        queries.append(query)
        if query == canonical_snapshot.table_query("banks"):
            stdout.write(rows)
        return 0

    result = candidate_database.snapshot_database(
        tmp_path, {"release": "/release"}, admitted, store, monitored)

    assert queries == [canonical_snapshot.table_query(table)
                       for table in canonical_snapshot.SNAPSHOT_TABLES]
    root = store.directory / "finalization" / admitted["token"]
    assert (root / result["tables"]["banks"]["file"]).read_bytes() == rows
    empty = root / result["tables"]["observation_history"]["file"]
    assert empty.read_bytes() == b""
    assert result["tables"]["observation_history"]["bytes"] == 0
