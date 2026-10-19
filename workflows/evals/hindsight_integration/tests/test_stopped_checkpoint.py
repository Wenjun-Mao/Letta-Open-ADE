"""Paired dump orchestration preserves failed partials and closes only the new owner."""

import json
import time
from uuid import uuid4

import pytest

from .. import stopped_checkpoint as checkpoint
from ..operations import Lease, create_record


@pytest.mark.parametrize("fault", [None, "native_dump", "parent_changed"])
def test_both_copies_or_partial_failure_always_close_new_owner(
    tmp_path, monkeypatch, fault
):
    root, parent = tmp_path / "new", tmp_path / "closed"
    parent.mkdir()
    now = int(time.time())
    lease = Lease(
        "ade-hindsight-integration-copy-test",
        str(uuid4()),
        "b" * 40,
        now - 1,
        now + 3600,
        now + 7200,
        "/mnt/projects",
        (),
    )
    lease.save(root)
    code = (
        tmp_path
        / lease.source_revision
        / "workflows/evals/hindsight_integration/stopped_checkpoint.py"
    )
    code.parent.mkdir(parents=True)
    code.write_text("controlled checkpoint source")
    config = code.parents[3] / "services/ade-api/alembic.ini"
    config.parent.mkdir(parents=True)
    config.write_text(
        "[alembic]\nversion_table_schema=ade\nversion_table=ade_alembic_version\n"
    )
    monkeypatch.setattr(checkpoint, "__file__", str(code))
    events, rows = [], []
    binding = {
        "activation_id": str(uuid4()),
        "source_revision": "a" * 40,
        "files": [],
        "native_progress": {"pending": ["original-operation"]},
        "ade_migration_head": "head",
        "stores": [
            {
                "store": name,
                "container_id": "original-" + name,
                "image_id": "sha256:" + "c" * 64,
                "volume": "original-" + name,
                "user": "admin",
                "database": name,
            }
            for name in ("ade", "hindsight")
        ],
    }

    class Docker:
        def owned(self, _lease):
            assert _lease == lease
            return rows

        def snapshot(self, ids):
            assert ids == []
            return []

        def stop(self, identity):
            assert identity.startswith("copied-")
            events.append(("stop", identity))
            next(row for row in rows if row["id"] == identity)["state"] = "exited"

    class Copies:
        def __init__(self, *args):
            pass

        def fence(self):
            pass

        def copy(self, store, output):
            events.append(("copy", store["store"]))
            create_record(output / "copy.json", {"copy_verified": True})
            return "new-" + store["store"], "helper-" + store["store"]

    def start(resources, store, volume):
        assert volume == "new-" + store["store"]
        identity = "copied-" + store["store"]
        rows.append(
            {
                "id": identity,
                "state": "running",
                "labels": {"com.docker.compose.service": store["store"] + "-db"},
            }
        )
        events.append(("start", identity))
        return identity

    def dump(output, identity, user, database):
        assert identity == "copied-" + database
        events.append(("dump", identity))
        if fault == "native_dump" and database == "hindsight":
            raise RuntimeError("controlled_dump_failure")
        output.write_bytes(b"controlled dump")
        return {"sha256": "d" * 64, "bytes": output.stat().st_size, "file": output.name}

    def bind(*args, **kwargs):
        if fault == "parent_changed" and (root / "closed.json").exists():
            return {**binding, "changed": True}
        return binding

    monkeypatch.setattr(checkpoint, "DockerOperations", Docker)
    monkeypatch.setattr(checkpoint, "CopyResources", Copies)
    monkeypatch.setattr(checkpoint, "healthy_lease", lambda *args: None)
    monkeypatch.setattr(checkpoint, "bind_parent", bind)
    monkeypatch.setattr(checkpoint, "database_copy", start)
    monkeypatch.setattr(checkpoint, "dump_database", dump)
    monkeypatch.setattr(checkpoint, "sql", lambda *args: "head")
    output = root / "evidence/copied-point"
    arguments = (root, parent, parent / "evidence/failed", output)
    if fault:
        with pytest.raises(RuntimeError):
            checkpoint.run_checkpoint(
                *arguments, controller_revision=lease.source_revision
            )
    else:
        checkpoint.run_checkpoint(*arguments, controller_revision=lease.source_revision)
    assert not (parent / "closed.json").exists()
    assert (root / "closed.json").exists()
    closeout = json.loads((output / "closeout.json").read_bytes())
    assert closeout["baseline_unchanged"] and closeout["running_owned"] == []
    assert closeout["closed_parent_unchanged"] == (fault != "parent_changed")
    assert (output / "ade/ade.dump").read_bytes() == b"controlled dump"
    if fault == "native_dump":
        assert (output / "failure.json").exists()
        assert not (output / "paired-backup.json").exists()
    else:
        result = json.loads((output / "paired-backup.json").read_bytes())
        assert result["native_progress_at_checkpoint"]["pending"] == [
            "original-operation"
        ]
        assert result["restore_verified"] is False and len(result["dumps"]) == 2
    assert events[:3] == [
        ("copy", "ade"),
        ("start", "copied-ade"),
        ("dump", "copied-ade"),
    ]


def test_database_copy_has_only_exact_store_image_and_new_volume(monkeypatch):
    calls = []

    class Resources:
        def create(self, *args):
            calls.append(args)
            return "new-db"

        def start(self, identity):
            assert identity == "new-db"

    monkeypatch.setattr(checkpoint, "ready", lambda *args: None)
    store = {"store": "ade", "image_id": "sha256:" + "c" * 64}
    assert checkpoint.database_copy(Resources(), store, "new-only-volume") == "new-db"
    service, image, flags, command = calls[0]
    assert service == "ade-db" and image == store["image_id"]
    assert (
        "type=volume,source=new-only-volume,target=/var/lib/postgresql/data,volume-nocopy"
        in flags
    )
    assert command[:3] == ["postgres", "-c", "listen_addresses="]
    assert not any("PASSWORD" in flag or "original" in flag for flag in flags)


def test_controller_not_staged_at_committed_revision_has_no_side_effects(tmp_path):
    with pytest.raises(ValueError, match="staged committed"):
        checkpoint.run_checkpoint(
            tmp_path, tmp_path, tmp_path, tmp_path / "new", controller_revision="d" * 40
        )
    assert list(tmp_path.iterdir()) == []
