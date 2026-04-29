from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_platform_api.registries.persona_sqlite import PersonaSqliteRegistry
from agent_platform_api.registries.prompt_persona_store import RegistryError


def _registry(tmp_path) -> PersonaSqliteRegistry:
    return PersonaSqliteRegistry(
        tmp_path,
        db_path=tmp_path / "data" / "personas" / "personas.sqlite3",
        seed_jsonl_path=tmp_path / "missing_seed.jsonl",
    )


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
    assert created["source_path"] == "data/personas/personas.sqlite3#comment_demo"
    assert created["tags"] == ["football"]
    assert created["metadata"] == {"source": "test"}

    with pytest.raises(RegistryError, match="already exists"):
        registry.create_persona(key="comment_demo", scenario="comment", content="Duplicate")

    updated = registry.update_persona(key="comment_demo", scenario="comment", content="Sharper voice.")
    assert updated["content"] == "Sharper voice."
    assert updated["label"] == "Demo"

    archived = registry.archive_persona("comment_demo", scenario="comment")
    assert archived["archived"] is True
    assert registry.list_personas(scenario="comment") == []
    assert [item["key"] for item in registry.list_personas(scenario="comment", include_archived=True)] == [
        "comment_demo"
    ]

    restored = registry.restore_persona("comment_demo", scenario="comment")
    assert restored["archived"] is False

    registry.archive_persona("comment_demo", scenario="comment")
    registry.purge_persona("comment_demo", scenario="comment")
    assert registry.list_personas(scenario="comment", include_archived=True) == []


def test_persona_sqlite_scenario_filter_and_fts_search(tmp_path) -> None:
    registry = _registry(tmp_path)
    registry.create_persona(key="chat_warm", scenario="chat", content="Warm chat companion.")
    registry.create_persona(key="comment_messi", scenario="comment", content="Messi focused football fan.")
    registry.create_persona(key="comment_other", scenario="comment", content="Basketball voice.")

    assert [item["key"] for item in registry.list_personas(scenario="chat")] == ["chat_warm"]
    assert [item["key"] for item in registry.search_personas("Messi", scenario="comment")] == ["comment_messi"]


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


def test_checked_in_seed_contains_curated_and_excel_personas() -> None:
    seed_path = Path("agent_platform_api/seed_data/personas.jsonl")
    records = [json.loads(line) for line in seed_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    keys = {record["key"] for record in records}

    assert len(records) == 102
    assert "chat_linxiaotang" in keys
    assert "comment_linxiaotang" in keys
    assert "comment_10" in keys
    assert "comment_109" in keys


def test_persona_jsonl_and_markdown_export_round_trip(tmp_path) -> None:
    registry = _registry(tmp_path)
    registry.create_persona(key="comment_export", scenario="comment", label="Export", content="Export body")

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
    assert imported.get_persona("comment_export", scenario="comment")["content"] == "Export body"
    assert "Export body" in markdown_path.read_text(encoding="utf-8")


def test_persona_jsonl_import_upsert_handles_archived_records(tmp_path) -> None:
    registry = _registry(tmp_path)
    registry.create_persona(key="comment_archived", scenario="comment", content="Old body")
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
