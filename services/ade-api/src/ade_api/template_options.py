from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from ade_api.dependencies import prompt_persona_registry
from ade_api.models.common import ScenarioType
from ade_api.options.constants import SCENARIO_DEFAULTS


def normalize_scenario(value: str | None, *, default: ScenarioType = "chat") -> ScenarioType:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return default
    if normalized in {"chat", "comment", "label"}:
        return normalized  # type: ignore[return-value]
    raise HTTPException(status_code=400, detail="scenario must be one of: chat, comment, label")


def active_prompt_records(scenario: ScenarioType | None = None) -> list[dict[str, Any]]:
    records = [
        record
        for record in prompt_persona_registry.list_templates(
            "prompt",
            include_archived=False,
            scenario=scenario,
        )
        if not bool(record.get("archived", False))
    ]
    if scenario:
        records = [
            record
            for record in records
            if str(record.get("key", "") or "").startswith(f"{scenario}_")
        ]
    return records


def active_persona_records(scenario: ScenarioType | None = None) -> list[dict[str, Any]]:
    if scenario == "label":
        return []
    records = [
        record
        for record in prompt_persona_registry.list_templates(
            "persona",
            include_archived=False,
            scenario=scenario,
        )
        if not bool(record.get("archived", False))
    ]
    if scenario:
        records = [
            record
            for record in records
            if str(record.get("key", "") or "").startswith(f"{scenario}_")
        ]
    return records


def prompt_content_map(scenario: ScenarioType | None = None) -> dict[str, str]:
    return {
        str(record.get("key", "")): str(record.get("content", "") or "")
        for record in active_prompt_records(scenario)
        if str(record.get("key", "")).strip()
    }


def prompt_record_map(scenario: ScenarioType | None = None) -> dict[str, dict[str, Any]]:
    return {
        str(record.get("key", "")): record
        for record in active_prompt_records(scenario)
        if str(record.get("key", "")).strip()
    }


def persona_content_map(scenario: ScenarioType | None = None) -> dict[str, str]:
    return {
        str(record.get("key", "")): str(record.get("content", "") or "")
        for record in active_persona_records(scenario)
        if str(record.get("key", "")).strip()
    }


def _option_entries(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "key": str(record.get("key", "") or ""),
            "label": str(record.get("label", "") or ""),
            "description": str(record.get("description", "") or ""),
            "scenario": str(record.get("scenario", "") or "") or None,
        }
        for record in records
    ]


def prompt_option_entries(scenario: ScenarioType | None = None) -> list[dict[str, Any]]:
    return _option_entries(active_prompt_records(scenario))


def persona_option_entries(scenario: ScenarioType | None = None) -> list[dict[str, Any]]:
    return _option_entries(active_persona_records(scenario))


def resolve_default_prompt_key(prompt_options: list[dict[str, Any]], scenario: ScenarioType) -> str:
    preferred = SCENARIO_DEFAULTS[scenario]["prompt_key"]
    if any(str(option.get("key", "")) == preferred for option in prompt_options):
        return preferred
    return str(prompt_options[0].get("key", "") if prompt_options else "")


def resolve_default_persona_key(persona_options: list[dict[str, Any]], scenario: ScenarioType) -> str:
    preferred = SCENARIO_DEFAULTS[scenario]["persona_key"]
    if any(str(option.get("key", "")) == preferred for option in persona_options):
        return preferred
    return str(persona_options[0].get("key", "") if persona_options else "")
