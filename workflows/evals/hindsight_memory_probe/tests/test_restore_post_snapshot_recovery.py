"""Archive seals and interrupted source retirement stay recoverable and exact."""

import hashlib
import json
from pathlib import Path

import pytest

from workflows.evals.hindsight_memory_probe import (
    restore_post_snapshot_archive as archive,
    restore_post_snapshot_recovery as recovery,
)


def _write(path: Path, data: bytes, mode: int = 0o400) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)


def _retired_fixture(tmp_path: Path, *, source_present=True, closure_sealed=False):
    token = "a" * 32
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    source_name = f"restore-{token}-evidence.json"
    source = state / source_name
    content = b"original failed attempt bytes\n"
    if source_present:
        _write(source, content)
    second_source = state / f"restore-{token}-later.json"
    second_content = b"another original receipt\n"
    _write(second_source, second_content)
    root = state / "restore-post-restore-retired" / token
    if source_present:
        _write(root / "evidence" / source_name, content)
    _write(root / "evidence" / second_source.name, second_content)
    manifest = {
        "schema": 1, "kind": "failed_post_restore_snapshot_preserved_retired",
        "status": "failed_post_restore_retired", "token": token,
        "capture_sha256": hashlib.sha256(b"captured-state").hexdigest(),
        "files": [
            {"path": second_source.name,
             "sha256": hashlib.sha256(second_content).hexdigest(),
             "bytes": len(second_content)},
        ],
    }
    if source_present:
        manifest["files"].insert(0, {"path": source_name,
            "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)})
    _write(root / "retirement.json", json.dumps(manifest, sort_keys=True).encode())
    _write(root / "retirement-seal.json", json.dumps({
        "schema": 1, "token": token,
        "sha256": hashlib.sha256((root / "retirement.json").read_bytes()).hexdigest(),
    }, sort_keys=True).encode())
    closure = {
        "schema": 1, "token": token, "status": "failed_post_restore_retired",
        "archive_sha256": hashlib.sha256((root / "retirement.json").read_bytes()).hexdigest(),
        "container_absent": True, "volume_absent": True, "main_baseline_unchanged": True,
        "closure_receipts": [], "completed_at": 1.0,
    }
    _write(root / "closure" / "closure.json", json.dumps(closure, sort_keys=True).encode())
    if closure_sealed:
        _write(root / "closure" / "closure-seal.json", json.dumps({
            "schema": 1, "token": token,
            "sha256": hashlib.sha256((root / "closure" / "closure.json").read_bytes()).hexdigest(),
        }, sort_keys=True).encode())
    return state, root, source, token


def test_next_attempt_repairs_closure_seal_then_finishes_source_retirement(tmp_path):
    state, root, source, token = _retired_fixture(tmp_path)

    recovery.prepare_next_attempt(state)

    assert not source.exists()
    seal = json.loads((root / "closure" / "closure-seal.json").read_text())
    assert seal["sha256"] == hashlib.sha256((root / "closure" / "closure.json").read_bytes()).hexdigest()
    assert archive.verify_archive(root, token)["status"] == "failed_post_restore_retired"


def test_source_change_blocks_retirement_without_deleting_anything(tmp_path):
    state, _root, source, _token = _retired_fixture(tmp_path)
    source.chmod(0o600)
    source.write_bytes(b"changed bytes")

    with pytest.raises(RuntimeError, match="source_changed"):
        recovery.prepare_next_attempt(state)

    assert source.read_bytes() == b"changed bytes"


def test_missing_source_is_a_preserved_absence_and_does_not_block_resume(tmp_path):
    state, _root, source, _token = _retired_fixture(tmp_path, source_present=False)

    recovery.prepare_next_attempt(state)

    assert not source.exists()


def test_unlisted_active_source_blocks_next_attempt(tmp_path):
    state, _root, _source, token = _retired_fixture(tmp_path)
    extra = state / f"restore-{token}-new.json"
    _write(extra, b"not in sealed history")

    with pytest.raises(RuntimeError, match="source_unarchived"):
        recovery.prepare_next_attempt(state)

    assert extra.is_file()


def test_interrupted_active_source_retirement_resumes_from_sealed_history(tmp_path, monkeypatch):
    state, _root, _source, token = _retired_fixture(tmp_path)
    original_unlink = Path.unlink
    removed_sources = []

    def fail_after_one(path, *args, **kwargs):
        if path.parent == state and path.name.startswith(f"restore-{token}-"):
            if removed_sources:
                raise OSError("simulated interruption during source retirement")
            removed_sources.append(path.name)
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_after_one)
    with pytest.raises(OSError, match="simulated interruption"):
        recovery.prepare_next_attempt(state)
    assert len(removed_sources) == 1
    monkeypatch.setattr(Path, "unlink", original_unlink)

    recovery.prepare_next_attempt(state)

    assert not list(state.glob(f"restore-{token}-*.json"))
    assert archive.verify_archive(state / "restore-post-restore-retired" / token, token)


def test_symlinked_closure_seal_blocks_source_retirement(tmp_path):
    state, root, source, token = _retired_fixture(tmp_path, closure_sealed=True)
    seal = root / "closure" / "closure-seal.json"
    seal.unlink()
    seal.symlink_to(root / "retirement-seal.json")

    with pytest.raises(RuntimeError, match="history_invalid"):
        recovery.prepare_next_attempt(state)

    assert source.is_file()
