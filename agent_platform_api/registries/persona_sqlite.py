from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_platform_api.registries.persona_exchange import (
    PersonaConflictPolicy,
    export_personas_jsonl,
    export_personas_markdown,
    import_personas_jsonl,
)
from agent_platform_api.registries.persona_records import PersonaRecordMapper
from agent_platform_api.registries.persona_rules import PersonaRules
from agent_platform_api.registries.persona_seed import PersonaSeedProjection
from agent_platform_api.registries.persona_store import PersonaSqliteStore
from agent_platform_api.registries.prompt_persona_store.types import (
    RegistryError,
    ScenarioKind,
)


class PersonaSqliteRegistry:
    """Coordinate persona domain operations across SQLite storage, mapping, and seed projection."""

    def __init__(
        self,
        project_root: Path,
        *,
        db_path: Path | None = None,
        seed_jsonl_path: Path | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.db_path = (
            db_path
            or self.project_root / "data" / "runtime" / "personas" / "personas.sqlite3"
        ).resolve()
        self.seed_jsonl_path = (
            seed_jsonl_path
            or self.project_root / "agent_platform_api" / "seed_data" / "personas.jsonl"
        ).resolve()
        self._rules = PersonaRules()
        self._mapper = PersonaRecordMapper(self.project_root, self.db_path)
        self._store = PersonaSqliteStore(self.db_path)
        self._seed_projection = PersonaSeedProjection(
            seed_jsonl_path=self.seed_jsonl_path,
            store=self._store,
            mapper=self._mapper,
            rules=self._rules,
        )
        self._store.ensure_schema()
        self.sync_seed()

    def list_personas(
        self,
        *,
        include_archived: bool = False,
        scenario: ScenarioKind | None = None,
        search: str = "",
    ) -> list[dict[str, Any]]:
        resolved_scenario = self._rules.normalize_scenario(scenario, allow_none=True)
        if resolved_scenario == "label":
            return []
        cleaned_search = str(search or "").strip()
        if cleaned_search:
            return self.search_personas(
                cleaned_search,
                include_archived=include_archived,
                scenario=resolved_scenario,
            )
        return [
            self._mapper.to_record(row)
            for row in self._store.list_rows(
                include_archived=include_archived, scenario=resolved_scenario
            )
        ]

    def search_personas(
        self,
        query: str,
        *,
        include_archived: bool = False,
        scenario: ScenarioKind | None = None,
    ) -> list[dict[str, Any]]:
        resolved_scenario = self._rules.normalize_scenario(scenario, allow_none=True)
        if resolved_scenario == "label":
            return []
        cleaned_query = str(query or "").strip()
        if not cleaned_query:
            return self.list_personas(
                include_archived=include_archived, scenario=resolved_scenario
            )
        return [
            self._mapper.to_record(row)
            for row in self._store.search_rows(
                cleaned_query,
                include_archived=include_archived,
                scenario=resolved_scenario,
            )
        ]

    def get_persona(
        self,
        key: str,
        *,
        archived: bool = False,
        scenario: ScenarioKind | None = None,
    ) -> dict[str, Any] | None:
        normalized_key = self._rules.normalize_key(key)
        resolved_scenario = self._rules.normalize_scenario(scenario, allow_none=True)
        if resolved_scenario == "label":
            return None
        row = self._store.get_row(
            normalized_key, archived=archived, scenario=resolved_scenario
        )
        return self._mapper.to_record(row) if row is not None else None

    def create_persona(
        self,
        *,
        key: str,
        content: str,
        label: str | None = None,
        description: str | None = None,
        scenario: ScenarioKind | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        values = self._rules.create_values(
            key=key,
            content=content,
            label=label,
            description=description,
            scenario=scenario,
            tags=tags,
            metadata=metadata,
        )
        if self._store.get_row(
            values.key, archived=False, scenario=None
        ) or self._store.get_row(
            values.key,
            archived=True,
            scenario=None,
        ):
            raise RegistryError(f"persona '{values.key}' already exists")
        return self._mapper.to_record(
            self._store.create_row(self._mapper.to_row_values(values))
        )

    def update_persona(
        self,
        *,
        key: str,
        content: str | None = None,
        label: str | None = None,
        description: str | None = None,
        scenario: ScenarioKind | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_key = self._rules.normalize_key(key)
        resolved_scenario = self._rules.normalize_scenario(scenario, allow_none=True)
        self._rules.ensure_supported_scenario(resolved_scenario)
        existing = self.get_persona(
            normalized_key, archived=False, scenario=resolved_scenario
        )
        if existing is None:
            raise RegistryError(f"persona '{normalized_key}' not found")
        values = self._rules.update_values(
            existing,
            content=content,
            label=label,
            description=description,
            tags=tags,
            metadata=metadata,
        )
        row = self._store.update_row(normalized_key, self._mapper.to_row_values(values))
        if (
            row is None
        ):  # pragma: no cover - another writer removed the record after lookup
            raise RegistryError(f"persona '{normalized_key}' not found")
        return self._mapper.to_record(row)

    def archive_persona(
        self, key: str, scenario: ScenarioKind | None = None
    ) -> dict[str, Any]:
        normalized_key = self._rules.normalize_key(key)
        resolved_scenario = self._rules.normalize_scenario(scenario, allow_none=True)
        self._rules.ensure_supported_scenario(resolved_scenario)
        if (
            self.get_persona(normalized_key, archived=False, scenario=resolved_scenario)
            is None
        ):
            raise RegistryError(f"persona '{normalized_key}' not found")
        row = self._store.archive_row(normalized_key)
        if (
            row is None
        ):  # pragma: no cover - another writer removed the record after lookup
            raise RegistryError(f"persona '{normalized_key}' not found")
        return self._mapper.to_record(row)

    def restore_persona(
        self, key: str, scenario: ScenarioKind | None = None
    ) -> dict[str, Any]:
        normalized_key = self._rules.normalize_key(key)
        resolved_scenario = self._rules.normalize_scenario(scenario, allow_none=True)
        self._rules.ensure_supported_scenario(resolved_scenario)
        if (
            self.get_persona(normalized_key, archived=True, scenario=resolved_scenario)
            is None
        ):
            raise RegistryError(f"Archived persona '{normalized_key}' not found")
        row = self._store.restore_row(normalized_key)
        if (
            row is None
        ):  # pragma: no cover - another writer removed the record after lookup
            raise RegistryError(f"Archived persona '{normalized_key}' not found")
        return self._mapper.to_record(row)

    def purge_persona(self, key: str, scenario: ScenarioKind | None = None) -> None:
        normalized_key = self._rules.normalize_key(key)
        resolved_scenario = self._rules.normalize_scenario(scenario, allow_none=True)
        self._rules.ensure_supported_scenario(resolved_scenario)
        existing = self.get_persona(
            normalized_key, archived=True, scenario=resolved_scenario
        )
        if existing is None:
            raise RegistryError(f"Archived persona '{normalized_key}' not found")
        self._store.purge_row(int(existing["id"]))

    def import_jsonl(
        self, path: Path, *, on_conflict: PersonaConflictPolicy = "error"
    ) -> dict[str, int]:
        return import_personas_jsonl(self, path, on_conflict=on_conflict)

    def export_jsonl(
        self,
        path: Path,
        *,
        include_archived: bool = False,
        scenario: ScenarioKind | None = None,
    ) -> int:
        return export_personas_jsonl(
            self, path, include_archived=include_archived, scenario=scenario
        )

    def export_markdown(
        self,
        path: Path,
        *,
        include_archived: bool = False,
        scenario: ScenarioKind | None = None,
    ) -> int:
        return export_personas_markdown(
            self, path, include_archived=include_archived, scenario=scenario
        )

    def sync_seed(self) -> dict[str, Any]:
        return self._seed_projection.sync()
