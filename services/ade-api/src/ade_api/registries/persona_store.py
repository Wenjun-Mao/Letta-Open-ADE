from __future__ import annotations

import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from ade_api.registries.persona_records import PersonaRowValues


class PersonaSqliteStore:
    """SQLite schema, CRUD, metadata, and FTS operations for persona records."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def ensure_schema(self) -> None:
        with closing(self._connect()) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS personas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    scenario TEXT NOT NULL CHECK (scenario IN ('chat', 'comment')),
                    label TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL DEFAULT '',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    archived INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    archived_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_personas_scenario_archived_key
                    ON personas (scenario, archived, key);
                CREATE VIRTUAL TABLE IF NOT EXISTS persona_fts
                    USING fts5(key, label, description, content, tags, persona_id UNINDEXED);
                CREATE TABLE IF NOT EXISTS persona_registry_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def list_rows(
        self, *, include_archived: bool, scenario: str | None
    ) -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[str] = []
        if not include_archived:
            clauses.append("archived = 0")
        if scenario:
            clauses.append("scenario = ?")
            params.append(scenario)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with closing(self._connect()) as conn:
            return conn.execute(
                f"SELECT * FROM personas {where_sql} ORDER BY archived ASC, scenario ASC, key ASC",
                params,
            ).fetchall()

    def search_rows(
        self, query: str, *, include_archived: bool, scenario: str | None
    ) -> list[sqlite3.Row]:
        clauses = ["persona_fts MATCH ?"]
        params: list[str] = [self._fts_query(query)]
        if not include_archived:
            clauses.append("p.archived = 0")
        if scenario:
            clauses.append("p.scenario = ?")
            params.append(scenario)
        with closing(self._connect()) as conn:
            return conn.execute(
                f"""
                SELECT p.*
                FROM persona_fts f
                JOIN personas p ON p.id = f.persona_id
                WHERE {" AND ".join(clauses)}
                ORDER BY rank, p.archived ASC, p.scenario ASC, p.key ASC
                """,
                params,
            ).fetchall()

    def get_row(
        self, key: str, *, archived: bool, scenario: str | None
    ) -> sqlite3.Row | None:
        clauses = ["key = ?", "archived = ?"]
        params: list[str | int] = [key, 1 if archived else 0]
        if scenario:
            clauses.append("scenario = ?")
            params.append(scenario)
        with closing(self._connect()) as conn:
            return conn.execute(
                f"SELECT * FROM personas WHERE {' AND '.join(clauses)}",
                params,
            ).fetchone()

    def create_row(self, values: PersonaRowValues) -> sqlite3.Row:
        with self.transaction() as conn:
            return self._insert_row(conn, values)

    def update_row(self, key: str, values: PersonaRowValues) -> sqlite3.Row | None:
        with self.transaction() as conn:
            now = self._now()
            conn.execute(
                """
                UPDATE personas
                SET label = ?,
                    description = ?,
                    content = ?,
                    tags_json = ?,
                    metadata_json = ?,
                    updated_at = ?
                WHERE key = ? AND archived = 0
                """,
                (
                    values.label,
                    values.description,
                    values.content,
                    values.tags_json,
                    values.metadata_json,
                    now,
                    key,
                ),
            )
            row = self._row_for_key(conn, key)
            if row is not None:
                self._upsert_fts(conn, row, values.tags_text)
            return row

    def archive_row(self, key: str) -> sqlite3.Row | None:
        with self.transaction() as conn:
            now = self._now()
            conn.execute(
                "UPDATE personas SET archived = 1, archived_at = ?, updated_at = ? WHERE key = ?",
                (now, now, key),
            )
            row = self._row_for_key(conn, key)
            if row is not None:
                self._upsert_fts(conn, row)
            return row

    def restore_row(self, key: str) -> sqlite3.Row | None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE personas SET archived = 0, archived_at = NULL, updated_at = ? WHERE key = ?",
                (self._now(), key),
            )
            row = self._row_for_key(conn, key)
            if row is not None:
                self._upsert_fts(conn, row)
            return row

    def purge_row(self, persona_id: int) -> None:
        with self.transaction() as conn:
            conn.execute("DELETE FROM persona_fts WHERE persona_id = ?", (persona_id,))
            conn.execute("DELETE FROM personas WHERE id = ?", (persona_id,))

    def upsert_seed_row(
        self, conn: sqlite3.Connection, values: PersonaRowValues
    ) -> str:
        """Apply one managed seed record within the caller's transaction."""
        existing = self._row_for_key(conn, values.key)
        if existing is None:
            self._insert_row(conn, values)
            return "created"

        now = self._now()
        archived_at = now if values.archived else None
        conn.execute(
            """
            UPDATE personas
            SET scenario = ?,
                label = ?,
                description = ?,
                content = ?,
                tags_json = ?,
                metadata_json = ?,
                archived = ?,
                archived_at = ?,
                updated_at = ?
            WHERE key = ?
            """,
            (
                values.scenario,
                values.label,
                values.description,
                values.content,
                values.tags_json,
                values.metadata_json,
                int(values.archived),
                archived_at,
                now,
                values.key,
            ),
        )
        row = self._row_for_key(conn, values.key)
        if row is None:  # pragma: no cover - guarded by the existing row above
            raise RuntimeError(f"Missing persona after seed upsert: {values.key}")
        self._upsert_fts(conn, row, values.tags_text)
        return "updated"

    def delete_rows_by_keys(self, conn: sqlite3.Connection, keys: set[str]) -> int:
        if not keys:
            return 0
        placeholders = ", ".join("?" for _ in keys)
        rows = conn.execute(
            f"SELECT id FROM personas WHERE key IN ({placeholders})",
            sorted(keys),
        ).fetchall()
        if not rows:
            return 0
        ids = [int(row["id"]) for row in rows]
        id_placeholders = ", ".join("?" for _ in ids)
        conn.execute(
            f"DELETE FROM persona_fts WHERE persona_id IN ({id_placeholders})", ids
        )
        conn.execute(f"DELETE FROM personas WHERE id IN ({id_placeholders})", ids)
        return len(ids)

    @staticmethod
    def existing_keys(conn: sqlite3.Connection, keys: set[str]) -> set[str]:
        if not keys:
            return set()
        placeholders = ", ".join("?" for _ in keys)
        rows = conn.execute(
            f"SELECT key FROM personas WHERE key IN ({placeholders})",
            sorted(keys),
        ).fetchall()
        return {str(row["key"]) for row in rows}

    @staticmethod
    def get_metadata_value(conn: sqlite3.Connection, key: str) -> str:
        row = conn.execute(
            "SELECT value FROM persona_registry_metadata WHERE key = ?", (key,)
        ).fetchone()
        return str(row["value"] if row else "")

    @staticmethod
    def set_metadata_value(conn: sqlite3.Connection, key: str, value: str) -> None:
        conn.execute(
            """
            INSERT INTO persona_registry_metadata (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
        except BaseException:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            conn.close()

    def _insert_row(
        self, conn: sqlite3.Connection, values: PersonaRowValues
    ) -> sqlite3.Row:
        now = self._now()
        archived_at = now if values.archived else None
        cursor = conn.execute(
            """
            INSERT INTO personas
                (key, scenario, label, description, content, tags_json, metadata_json, archived, created_at, updated_at, archived_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                values.key,
                values.scenario,
                values.label,
                values.description,
                values.content,
                values.tags_json,
                values.metadata_json,
                int(values.archived),
                now,
                now,
                archived_at,
            ),
        )
        row = conn.execute(
            "SELECT * FROM personas WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        if row is None:  # pragma: no cover - SQLite returned an inserted row id
            raise RuntimeError(f"Missing inserted persona: {values.key}")
        self._upsert_fts(conn, row, values.tags_text)
        return row

    @staticmethod
    def _row_for_key(conn: sqlite3.Connection, key: str) -> sqlite3.Row | None:
        return conn.execute("SELECT * FROM personas WHERE key = ?", (key,)).fetchone()

    @staticmethod
    def _upsert_fts(
        conn: sqlite3.Connection, row: sqlite3.Row, tags_text: str | None = None
    ) -> None:
        persona_id = int(row["id"])
        conn.execute("DELETE FROM persona_fts WHERE persona_id = ?", (persona_id,))
        conn.execute(
            """
            INSERT INTO persona_fts (key, label, description, content, tags, persona_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(row["key"]),
                str(row["label"]),
                str(row["description"]),
                str(row["content"]),
                tags_text
                if tags_text is not None
                else " ".join(PersonaSqliteStore._tags_from_json(row["tags_json"])),
                persona_id,
            ),
        )

    @staticmethod
    def _tags_from_json(raw: str) -> list[str]:
        try:
            parsed = json.loads(str(raw or ""))
        except json.JSONDecodeError:
            return []
        return [str(item) for item in parsed] if isinstance(parsed, list) else []

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    @staticmethod
    def _fts_query(query: str) -> str:
        terms = [
            term.strip().replace('"', '""')
            for term in str(query or "").split()
            if term.strip()
        ]
        if not terms:
            cleaned = str(query or "").strip().replace('"', '""')
            return f'"{cleaned}"'
        return " ".join(f'"{term}"' for term in terms)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
