from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ade_api.features.prompt_center.personas.records import (
    PersonaRecordMapper,
    PersonaValues,
)
from ade_api.features.prompt_center.personas.rules import PersonaRules
from ade_api.features.prompt_center.personas.store import PersonaSqliteStore
from ade_api.features.prompt_center.types import RegistryError


class PersonaSeedProjection:
    """Projects the reviewed seed JSONL into managed SQLite persona records."""

    def __init__(
        self,
        *,
        seed_jsonl_path: Path,
        store: PersonaSqliteStore,
        mapper: PersonaRecordMapper,
        rules: PersonaRules,
    ) -> None:
        self.seed_jsonl_path = Path(seed_jsonl_path).resolve()
        self.store = store
        self.mapper = mapper
        self.rules = rules

    def sync(self) -> dict[str, Any]:
        """Atomically apply a changed managed seed without touching runtime-only rows."""
        if not self.seed_jsonl_path.is_file():
            return self._unchanged_result()

        seed_bytes = self.seed_jsonl_path.read_bytes()
        values = self._parse_seed(seed_bytes.decode("utf-8"))
        seed_hash = hashlib.sha256(seed_bytes).hexdigest()
        seed_keys = {value.key for value in values}

        # Parsing completes before the transaction so malformed source cannot partially project.
        with self.store.transaction() as conn:
            current_hash = self.store.get_metadata_value(conn, "seed_sha256")
            if current_hash == seed_hash:
                return self._unchanged_result()

            previous_keys = self._managed_keys(
                self.store.get_metadata_value(conn, "seed_keys_json")
            )
            runtime_collisions = self.store.existing_keys(
                conn, seed_keys - previous_keys
            )
            if runtime_collisions:
                keys = ", ".join(sorted(runtime_collisions))
                raise RegistryError(
                    f"Seed keys collide with runtime-only personas: {keys}"
                )
            counts = {"created": 0, "updated": 0, "skipped": 0}
            for value in values:
                outcome = self.store.upsert_seed_row(
                    conn, self.mapper.to_row_values(value)
                )
                counts[outcome] += 1

            removed = self.store.delete_rows_by_keys(conn, previous_keys - seed_keys)
            self.store.set_metadata_value(conn, "seed_sha256", seed_hash)
            self.store.set_metadata_value(
                conn, "seed_keys_json", json.dumps(sorted(seed_keys))
            )

        return {"changed": True, **counts, "removed": removed}

    def _parse_seed(self, content: str) -> list[PersonaValues]:
        values: list[PersonaValues] = []
        keys: set[str] = set()
        for line_number, raw_line in enumerate(content.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RegistryError(
                    f"Invalid seed JSONL at line {line_number}: {exc}"
                ) from exc
            if not isinstance(payload, dict):
                raise RegistryError(
                    f"Invalid seed JSONL at line {line_number}: expected object"
                )
            value = self.rules.values_from_seed_payload(
                payload, line_number=line_number
            )
            if value.key in keys:
                raise RegistryError(
                    f"Invalid seed JSONL at line {line_number}: duplicate key '{value.key}'"
                )
            keys.add(value.key)
            values.append(value)
        return values

    @staticmethod
    def _managed_keys(raw: str) -> set[str]:
        try:
            parsed = json.loads(raw or "[]")
        except json.JSONDecodeError:
            return set()
        return (
            {str(item) for item in parsed if isinstance(item, str)}
            if isinstance(parsed, list)
            else set()
        )

    @staticmethod
    def _unchanged_result() -> dict[str, Any]:
        return {
            "changed": False,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "removed": 0,
        }
