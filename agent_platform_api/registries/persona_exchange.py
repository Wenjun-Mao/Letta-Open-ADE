from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Protocol

from agent_platform_api.registries.prompt_persona_store import RegistryError

PersonaConflictPolicy = Literal["error", "skip", "upsert"]


class PersonaExchangeRegistry(Protocol):
    def list_personas(
        self,
        *,
        include_archived: bool = False,
        scenario: str | None = None,
        search: str = "",
    ) -> list[dict[str, Any]]: ...

    def get_persona(
        self,
        key: str,
        *,
        archived: bool = False,
        scenario: str | None = None,
    ) -> dict[str, Any] | None: ...

    def create_persona(
        self,
        *,
        key: str,
        content: str,
        label: str | None = None,
        description: str | None = None,
        scenario: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def update_persona(
        self,
        *,
        key: str,
        content: str | None = None,
        label: str | None = None,
        description: str | None = None,
        scenario: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def archive_persona(self, key: str, scenario: str | None = None) -> dict[str, Any]: ...

    def restore_persona(self, key: str, scenario: str | None = None) -> dict[str, Any]: ...


def import_personas_jsonl(
    registry: PersonaExchangeRegistry,
    path: Path,
    *,
    on_conflict: PersonaConflictPolicy = "error",
) -> dict[str, int]:
    if on_conflict not in {"error", "skip", "upsert"}:
        raise RegistryError("on_conflict must be one of: error, skip, upsert")
    counts = {"created": 0, "updated": 0, "skipped": 0}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        payload = _parse_jsonl_payload(raw_line, line_number)
        if payload is None:
            continue

        key = str(payload.get("key", "") or "")
        scenario = payload.get("scenario")
        is_archived = bool(payload.get("archived", False))
        existing = registry.get_persona(key, archived=False, scenario=scenario)
        existing_archived = registry.get_persona(key, archived=True, scenario=scenario)
        existing = existing or existing_archived
        if existing and on_conflict == "skip":
            counts["skipped"] += 1
            continue
        if existing and on_conflict == "error":
            raise RegistryError(f"persona '{key}' already exists")
        if existing:
            if bool(existing.get("archived")):
                registry.restore_persona(key, scenario=scenario)
            registry.update_persona(
                key=key,
                content=str(payload.get("content", "") or ""),
                label=str(payload.get("label", "") or ""),
                description=str(payload.get("description", "") or ""),
                scenario=scenario,
                tags=_coerce_tags(payload.get("tags")),
                metadata=_coerce_metadata(payload.get("metadata")),
            )
            if is_archived:
                registry.archive_persona(key, scenario=scenario)
            counts["updated"] += 1
            continue

        record = registry.create_persona(
            key=key,
            content=str(payload.get("content", "") or ""),
            label=str(payload.get("label", "") or ""),
            description=str(payload.get("description", "") or ""),
            scenario=scenario,
            tags=_coerce_tags(payload.get("tags")),
            metadata=_coerce_metadata(payload.get("metadata")),
        )
        if is_archived:
            registry.archive_persona(str(record["key"]), scenario=record.get("scenario"))
        counts["created"] += 1
    return counts


def export_personas_jsonl(
    registry: PersonaExchangeRegistry,
    path: Path,
    *,
    include_archived: bool = False,
    scenario: str | None = None,
) -> int:
    records = registry.list_personas(include_archived=include_archived, scenario=scenario)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            payload = {
                "key": record["key"],
                "scenario": record["scenario"],
                "label": record["label"],
                "description": record["description"],
                "content": record["content"],
                "archived": record["archived"],
                "tags": record.get("tags", []),
                "metadata": record.get("metadata", {}),
            }
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return len(records)


def export_personas_markdown(
    registry: PersonaExchangeRegistry,
    path: Path,
    *,
    include_archived: bool = False,
    scenario: str | None = None,
) -> int:
    records = registry.list_personas(include_archived=include_archived, scenario=scenario)
    path.parent.mkdir(parents=True, exist_ok=True)
    sections: list[str] = []
    for record in records:
        sections.append(
            "\n".join(
                [
                    f"## {record['label'] or record['key']}",
                    "",
                    f"- key: `{record['key']}`",
                    f"- scenario: `{record['scenario']}`",
                    f"- archived: `{str(record['archived']).lower()}`",
                    "",
                    str(record["content"]).strip(),
                    "",
                ]
            )
        )
    path.write_text("# Persona Export\n\n" + "\n".join(sections), encoding="utf-8", newline="\n")
    return len(records)


def _parse_jsonl_payload(raw_line: str, line_number: int) -> dict[str, Any] | None:
    line = raw_line.strip()
    if not line:
        return None
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise RegistryError(f"Invalid JSONL at line {line_number}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RegistryError(f"Invalid JSONL at line {line_number}: expected object")
    return payload


def _coerce_tags(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str) and raw.strip():
        return [item.strip() for item in raw.split(",") if item.strip()]
    return []


def _coerce_metadata(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}
