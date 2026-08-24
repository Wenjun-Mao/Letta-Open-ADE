from __future__ import annotations

from pathlib import Path

import pytest

from scripts.migrate_runtime_data import migrate_file


LEGACY_PATH = Path("data/agent_lifecycle/registry.json")
RUNTIME_PATH = Path("data/runtime/agent-lifecycle/registry.json")


def test_migrate_runtime_data_copies_then_can_remove_identical_source(
    tmp_path: Path,
) -> None:
    source = tmp_path / LEGACY_PATH
    source.parent.mkdir(parents=True)
    source.write_text('{"version": 1}\n', encoding="utf-8")

    result = migrate_file(tmp_path, LEGACY_PATH, RUNTIME_PATH)
    assert result.startswith("copy ")
    assert (tmp_path / RUNTIME_PATH).read_bytes() == source.read_bytes()

    result = migrate_file(
        tmp_path,
        LEGACY_PATH,
        RUNTIME_PATH,
        remove_source=True,
    )
    assert result.startswith("verified and remove source ")
    assert not source.exists()


def test_migrate_runtime_data_refuses_conflicting_destination(tmp_path: Path) -> None:
    source = tmp_path / LEGACY_PATH
    destination = tmp_path / RUNTIME_PATH
    source.parent.mkdir(parents=True)
    destination.parent.mkdir(parents=True)
    source.write_text("legacy", encoding="utf-8")
    destination.write_text("runtime", encoding="utf-8")

    with pytest.raises(
        RuntimeError, match="Refusing to replace conflicting runtime data"
    ):
        migrate_file(tmp_path, LEGACY_PATH, RUNTIME_PATH)


def test_migrate_runtime_data_dry_run_does_not_write(tmp_path: Path) -> None:
    source = tmp_path / LEGACY_PATH
    source.parent.mkdir(parents=True)
    source.write_text("legacy", encoding="utf-8")

    result = migrate_file(tmp_path, LEGACY_PATH, RUNTIME_PATH, dry_run=True)
    assert result.startswith("would copy ")
    assert not (tmp_path / RUNTIME_PATH).exists()
