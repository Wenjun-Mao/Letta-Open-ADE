from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ade_api.features.prompt_center.codec import (
    first_non_empty_line,
)


@dataclass(frozen=True)
class PersonaValues:
    """Validated persona values before they are represented as SQLite columns."""

    key: str
    scenario: str
    label: str
    description: str
    content: str
    tags: tuple[str, ...]
    metadata: dict[str, Any]
    archived: bool = False


@dataclass(frozen=True)
class PersonaRowValues:
    """SQLite-ready representation of a persona."""

    key: str
    scenario: str
    label: str
    description: str
    content: str
    tags_json: str
    metadata_json: str
    tags_text: str
    archived: bool


class PersonaRecordMapper:
    """Maps persona values between SQLite rows and the registry's public records."""

    def __init__(self, project_root: Path, db_path: Path) -> None:
        self.project_root = Path(project_root).resolve()
        self.db_path = Path(db_path).resolve()

    def to_row_values(self, values: PersonaValues) -> PersonaRowValues:
        return PersonaRowValues(
            key=values.key,
            scenario=values.scenario,
            label=values.label,
            description=values.description,
            content=values.content,
            tags_json=json.dumps(list(values.tags), ensure_ascii=False, sort_keys=True),
            metadata_json=json.dumps(
                values.metadata, ensure_ascii=False, sort_keys=True
            ),
            tags_text=" ".join(values.tags),
            archived=values.archived,
        )

    def to_record(self, row: sqlite3.Row) -> dict[str, Any]:
        tags = self._loads_json(row["tags_json"], [])
        metadata = self._loads_json(row["metadata_json"], {})
        content = str(row["content"] or "")
        return {
            "id": int(row["id"]),
            "kind": "persona",
            "scenario": str(row["scenario"] or "chat"),
            "key": str(row["key"] or ""),
            "label": str(row["label"] or ""),
            "description": str(row["description"] or ""),
            "content": content,
            "preview": first_non_empty_line(content)[:180],
            "length": len(content),
            "archived": bool(row["archived"]),
            "archived_at": row["archived_at"],
            "source_path": f"{self._relative_db_path()}#{row['key']}",
            "updated_at": str(row["updated_at"] or ""),
            "output_schema": None,
            "tags": tags if isinstance(tags, list) else [],
            "metadata": metadata if isinstance(metadata, dict) else {},
        }

    def _relative_db_path(self) -> str:
        try:
            return self.db_path.relative_to(self.project_root).as_posix()
        except ValueError:
            return self.db_path.as_posix()

    @staticmethod
    def _loads_json(raw: str, default: Any) -> Any:
        try:
            return json.loads(str(raw or ""))
        except json.JSONDecodeError:
            return default
