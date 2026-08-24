from __future__ import annotations

import json
from pathlib import Path

import pytest

from ade_api.features.prompt_center.personas.sqlite import PersonaSqliteRegistry
from ade_api.features.prompt_center.types import RegistryError


def _registry(tmp_path) -> PersonaSqliteRegistry:
    return PersonaSqliteRegistry(
        tmp_path,
        db_path=tmp_path / "data" / "runtime" / "personas" / "personas.sqlite3",
        seed_jsonl_path=tmp_path / "missing_seed.jsonl",
    )


def _write_seed(path: Path, *records: dict[str, object]) -> str:
    content = "\n".join(json.dumps(record) for record in records) + "\n"
    path.write_text(content, encoding="utf-8")
    return content


def _unchanged_seed_sync() -> dict[str, object]:
    return {"changed": False, "created": 0, "updated": 0, "skipped": 0, "removed": 0}


def test_persona_sqlite_crud_archive_restore_and_purge(tmp_path) -> None:
    registry = _registry(tmp_path)

    created = registry.create_persona(
        key="comment_demo",
        scenario="comment",
        label="Demo",
        description="A demo persona",
        content="Gentle football fan.",
        tags=["football"],
        metadata={"source": "test"},
    )
    assert created["key"] == "comment_demo"
    assert (
        created["source_path"] == "data/runtime/personas/personas.sqlite3#comment_demo"
    )
    assert created["tags"] == ["football"]
    assert created["metadata"] == {"source": "test"}

    with pytest.raises(RegistryError, match="already exists"):
        registry.create_persona(
            key="comment_demo", scenario="comment", content="Duplicate"
        )

    updated = registry.update_persona(
        key="comment_demo", scenario="comment", content="Sharper voice."
    )
    assert updated["content"] == "Sharper voice."
    assert updated["label"] == "Demo"

    archived = registry.archive_persona("comment_demo", scenario="comment")
    assert archived["archived"] is True
    assert registry.list_personas(scenario="comment") == []
    assert [
        item["key"]
        for item in registry.list_personas(scenario="comment", include_archived=True)
    ] == ["comment_demo"]

    restored = registry.restore_persona("comment_demo", scenario="comment")
    assert restored["archived"] is False

    registry.archive_persona("comment_demo", scenario="comment")
    registry.purge_persona("comment_demo", scenario="comment")
    assert registry.list_personas(scenario="comment", include_archived=True) == []


def test_persona_sqlite_scenario_filter_and_fts_search(tmp_path) -> None:
    registry = _registry(tmp_path)
    registry.create_persona(
        key="chat_warm", scenario="chat", content="Warm chat companion."
    )
    registry.create_persona(
        key="comment_messi", scenario="comment", content="Messi focused football fan."
    )
    registry.create_persona(
        key="comment_other", scenario="comment", content="Basketball voice."
    )

    assert [item["key"] for item in registry.list_personas(scenario="chat")] == [
        "chat_warm"
    ]
    assert [
        item["key"] for item in registry.search_personas("Messi", scenario="comment")
    ] == ["comment_messi"]


def test_persona_sqlite_rejects_label_personas(tmp_path) -> None:
    registry = _registry(tmp_path)

    with pytest.raises(RegistryError, match="Label scenario does not support persona"):
        registry.create_persona(key="label_demo", scenario="label", content="Nope")


def test_persona_seed_jsonl_loads_when_db_is_empty(tmp_path) -> None:
    seed_path = tmp_path / "seed.jsonl"
    seed_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "key": "chat_linxiaotang",
                        "scenario": "chat",
                        "label": "Chat Lin Xiao Tang",
                        "description": "Seed chat persona",
                        "content": "Chat seed",
                    }
                ),
                json.dumps(
                    {
                        "key": "comment_10",
                        "scenario": "comment",
                        "label": "Only Messi",
                        "description": "Seed comment persona",
                        "content": "Messi fan",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    registry = PersonaSqliteRegistry(
        tmp_path,
        db_path=tmp_path / "data" / "personas" / "personas.sqlite3",
        seed_jsonl_path=seed_path,
    )

    assert registry.get_persona("chat_linxiaotang", scenario="chat") is not None
    assert registry.get_persona("comment_10", scenario="comment") is not None


def test_persona_seed_sync_applies_new_versions_and_preserves_runtime_only_records(
    tmp_path,
) -> None:
    seed_path = tmp_path / "seed.jsonl"
    _write_seed(
        seed_path,
        {"key": "chat_seed", "scenario": "chat", "content": "Version one"},
    )
    db_path = tmp_path / "data" / "runtime" / "personas" / "personas.sqlite3"

    registry = PersonaSqliteRegistry(
        tmp_path, db_path=db_path, seed_jsonl_path=seed_path
    )
    assert registry.sync_seed() == _unchanged_seed_sync()
    registry.update_persona(key="chat_seed", scenario="chat", content="Runtime edit")
    registry.create_persona(
        key="comment_runtime", scenario="comment", content="Runtime only"
    )

    unchanged = PersonaSqliteRegistry(
        tmp_path, db_path=db_path, seed_jsonl_path=seed_path
    )
    assert (
        unchanged.get_persona("chat_seed", scenario="chat")["content"] == "Runtime edit"
    )

    _write_seed(
        seed_path,
        {"key": "chat_seed", "scenario": "chat", "content": "Version two"},
    )
    assert registry.sync_seed() == {
        "changed": True,
        "created": 0,
        "updated": 1,
        "skipped": 0,
        "removed": 0,
    }

    assert (
        registry.get_persona("chat_seed", scenario="chat")["content"] == "Version two"
    )
    assert (
        registry.get_persona("comment_runtime", scenario="comment")["content"]
        == "Runtime only"
    )
    assert registry.sync_seed() == _unchanged_seed_sync()


def test_persona_seed_sync_rejects_new_seed_key_owned_by_runtime(tmp_path) -> None:
    seed_path = tmp_path / "seed.jsonl"
    original_content = _write_seed(
        seed_path,
        {"key": "chat_seed", "scenario": "chat", "content": "Original"},
    )
    db_path = tmp_path / "data" / "runtime" / "personas" / "personas.sqlite3"
    registry = PersonaSqliteRegistry(
        tmp_path, db_path=db_path, seed_jsonl_path=seed_path
    )
    registry.create_persona(key="chat_future", scenario="chat", content="Runtime-owned")

    _write_seed(
        seed_path,
        {"key": "chat_seed", "scenario": "chat", "content": "Changed"},
        {"key": "chat_future", "scenario": "chat", "content": "Seed-owned"},
    )

    with pytest.raises(
        RegistryError,
        match="Seed keys collide with runtime-only personas: chat_future",
    ):
        registry.sync_seed()

    assert registry.get_persona("chat_seed", scenario="chat")["content"] == "Original"
    assert (
        registry.get_persona("chat_future", scenario="chat")["content"]
        == "Runtime-owned"
    )
    seed_path.write_text(original_content, encoding="utf-8")
    assert registry.sync_seed() == _unchanged_seed_sync()


def test_persona_seed_sync_removes_records_deleted_from_new_seed_version(
    tmp_path,
) -> None:
    seed_path = tmp_path / "seed.jsonl"
    _write_seed(
        seed_path,
        {"key": "chat_keep", "scenario": "chat", "content": "Keep"},
        {"key": "comment_remove", "scenario": "comment", "content": "Remove"},
    )
    db_path = tmp_path / "data" / "runtime" / "personas" / "personas.sqlite3"
    registry = PersonaSqliteRegistry(
        tmp_path, db_path=db_path, seed_jsonl_path=seed_path
    )
    registry.update_persona(
        key="comment_remove", scenario="comment", content="Runtime-edited managed seed"
    )
    registry.create_persona(
        key="comment_runtime", scenario="comment", content="Runtime only"
    )

    _write_seed(
        seed_path,
        {"key": "chat_keep", "scenario": "chat", "content": "Keep"},
    )

    assert registry.sync_seed() == {
        "changed": True,
        "created": 0,
        "updated": 1,
        "skipped": 0,
        "removed": 1,
    }
    assert registry.get_persona("chat_keep", scenario="chat") is not None
    assert registry.get_persona("comment_remove", scenario="comment") is None
    assert (
        registry.get_persona("comment_runtime", scenario="comment")["content"]
        == "Runtime only"
    )


def test_persona_seed_sync_rejects_duplicate_managed_keys_without_mutating_runtime(
    tmp_path,
) -> None:
    seed_path = tmp_path / "seed.jsonl"
    original_content = _write_seed(
        seed_path,
        {"key": "chat_seed", "scenario": "chat", "content": "Original"},
    )
    db_path = tmp_path / "data" / "runtime" / "personas" / "personas.sqlite3"
    registry = PersonaSqliteRegistry(
        tmp_path, db_path=db_path, seed_jsonl_path=seed_path
    )
    registry.create_persona(
        key="comment_runtime", scenario="comment", content="Runtime only"
    )

    _write_seed(
        seed_path,
        {"key": "chat_seed", "scenario": "chat", "content": "Updated"},
        {"key": "chat_seed", "scenario": "chat", "content": "Duplicate"},
    )

    with pytest.raises(RegistryError, match="duplicate key 'chat_seed'"):
        registry.sync_seed()

    assert registry.get_persona("chat_seed", scenario="chat")["content"] == "Original"
    assert (
        registry.get_persona("comment_runtime", scenario="comment")["content"]
        == "Runtime only"
    )
    seed_path.write_text(original_content, encoding="utf-8")
    assert registry.sync_seed() == _unchanged_seed_sync()


def test_persona_seed_sync_rolls_back_records_and_metadata_on_write_failure(
    tmp_path, monkeypatch
) -> None:
    seed_path = tmp_path / "seed.jsonl"
    original_content = _write_seed(
        seed_path,
        {"key": "chat_keep", "scenario": "chat", "content": "Keep"},
        {"key": "comment_remove", "scenario": "comment", "content": "Remove"},
    )
    db_path = tmp_path / "data" / "runtime" / "personas" / "personas.sqlite3"
    registry = PersonaSqliteRegistry(
        tmp_path, db_path=db_path, seed_jsonl_path=seed_path
    )
    registry.create_persona(
        key="comment_runtime", scenario="comment", content="Runtime only"
    )

    _write_seed(
        seed_path,
        {"key": "chat_keep", "scenario": "chat", "content": "Changed"},
        {"key": "chat_new", "scenario": "chat", "content": "New"},
    )

    original_set_metadata = registry._store.set_metadata_value

    def fail_before_managed_keys(conn, key: str, value: str) -> None:
        if key == "seed_keys_json":
            raise RuntimeError("simulated metadata write failure")
        original_set_metadata(conn, key, value)

    with monkeypatch.context() as patch:
        patch.setattr(registry._store, "set_metadata_value", fail_before_managed_keys)
        with pytest.raises(RuntimeError, match="simulated metadata write failure"):
            registry.sync_seed()

    assert registry.get_persona("chat_keep", scenario="chat")["content"] == "Keep"
    assert registry.get_persona("chat_new", scenario="chat") is None
    assert registry.get_persona("comment_remove", scenario="comment") is not None
    assert (
        registry.get_persona("comment_runtime", scenario="comment")["content"]
        == "Runtime only"
    )
    seed_path.write_text(original_content, encoding="utf-8")
    assert registry.sync_seed() == _unchanged_seed_sync()


def test_checked_in_seed_contains_curated_and_excel_personas() -> None:
    seed_path = Path("content/personas/personas.jsonl")
    records = [
        json.loads(line)
        for line in seed_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    keys = {record["key"] for record in records}

    assert len(records) == 102
    assert "chat_linxiaotang" in keys
    assert "comment_linxiaotang" in keys
    assert "comment_10" in keys
    assert "comment_109" in keys


def test_persona_jsonl_and_markdown_export_round_trip(tmp_path) -> None:
    registry = _registry(tmp_path)
    registry.create_persona(
        key="comment_export", scenario="comment", label="Export", content="Export body"
    )

    jsonl_path = tmp_path / "export.jsonl"
    markdown_path = tmp_path / "export.md"
    assert registry.export_jsonl(jsonl_path, scenario="comment") == 1
    assert registry.export_markdown(markdown_path, scenario="comment") == 1

    imported = PersonaSqliteRegistry(
        tmp_path / "imported",
        db_path=tmp_path / "imported" / "data" / "personas.sqlite3",
        seed_jsonl_path=tmp_path / "missing_seed.jsonl",
    )
    result = imported.import_jsonl(jsonl_path)

    assert result == {"created": 1, "updated": 0, "skipped": 0}
    assert (
        imported.get_persona("comment_export", scenario="comment")["content"]
        == "Export body"
    )
    assert "Export body" in markdown_path.read_text(encoding="utf-8")


def test_persona_jsonl_import_upsert_handles_archived_records(tmp_path) -> None:
    registry = _registry(tmp_path)
    registry.create_persona(
        key="comment_archived", scenario="comment", content="Old body"
    )
    registry.archive_persona("comment_archived", scenario="comment")

    jsonl_path = tmp_path / "upsert.jsonl"
    jsonl_path.write_text(
        json.dumps(
            {
                "key": "comment_archived",
                "scenario": "comment",
                "label": "Updated",
                "description": "",
                "content": "New body",
                "archived": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = registry.import_jsonl(jsonl_path, on_conflict="upsert")

    assert result == {"created": 0, "updated": 1, "skipped": 0}
    record = registry.get_persona("comment_archived", archived=True, scenario="comment")
    assert record["content"] == "New body"
    assert record["label"] == "Updated"
