from __future__ import annotations

from typing import Any, cast

from ade_api.registries.persona_records import PersonaValues
from ade_api.registries.prompt_persona_store.types import (
    KEY_PATTERN,
    KNOWN_SCENARIOS,
    RegistryError,
    ScenarioKind,
)


class PersonaRules:
    """Domain validation and normalization shared by registry operations and seed projection."""

    def normalize_key(self, key: str) -> str:
        normalized = str(key or "").strip().lower()
        if not KEY_PATTERN.fullmatch(normalized):
            raise RegistryError(
                "Invalid key. Use 2-64 chars with lowercase letters, numbers, underscores, or hyphens; must start with a letter."
            )
        return normalized

    def normalize_scenario(
        self, scenario: str | None, *, allow_none: bool = False
    ) -> ScenarioKind | None:
        if scenario is None:
            return None if allow_none else "chat"
        normalized = str(scenario or "").strip().lower()
        if not normalized:
            return None if allow_none else "chat"
        if normalized not in KNOWN_SCENARIOS:
            raise RegistryError(f"Unsupported scenario: {scenario}")
        return cast(ScenarioKind, normalized)

    def create_values(
        self,
        *,
        key: str,
        content: str,
        label: str | None,
        description: str | None,
        scenario: str | None,
        tags: list[str] | None,
        metadata: dict[str, Any] | None,
        archived: bool = False,
    ) -> PersonaValues:
        normalized_key = self.normalize_key(key)
        resolved_scenario = self.normalize_scenario(
            scenario, allow_none=True
        ) or self.infer_scenario_from_key(normalized_key)
        self.ensure_supported_scenario(resolved_scenario)
        self.validate_key_scenario(normalized_key, resolved_scenario)

        normalized_content = str(content or "")
        if not normalized_content.strip():
            raise RegistryError("content is required")

        return PersonaValues(
            key=normalized_key,
            scenario=resolved_scenario,
            label=str(label or "").strip(),
            description=str(description or "").strip(),
            content=normalized_content,
            tags=self.normalize_tags(tags),
            metadata=self.normalize_metadata(metadata),
            archived=archived,
        )

    def update_values(
        self,
        existing: dict[str, Any],
        *,
        content: str | None,
        label: str | None,
        description: str | None,
        tags: list[str] | None,
        metadata: dict[str, Any] | None,
    ) -> PersonaValues:
        return self.create_values(
            key=str(existing["key"]),
            scenario=str(existing["scenario"]),
            content=str(existing.get("content", "") if content is None else content),
            label=str(existing.get("label", "") if label is None else label),
            description=str(
                existing.get("description", "") if description is None else description
            ),
            tags=existing.get("tags", []) if tags is None else tags,
            metadata=existing.get("metadata", {}) if metadata is None else metadata,
            archived=bool(existing.get("archived")),
        )

    def values_from_seed_payload(
        self, payload: dict[str, Any], *, line_number: int
    ) -> PersonaValues:
        key = str(payload.get("key", "") or "")
        if not key.strip():
            raise RegistryError(
                f"Invalid seed JSONL at line {line_number}: key is required"
            )
        try:
            return self.create_values(
                key=key,
                scenario=payload.get("scenario"),
                content=str(payload.get("content", "") or ""),
                label=str(payload.get("label", "") or ""),
                description=str(payload.get("description", "") or ""),
                tags=self.coerce_tags(payload.get("tags")),
                metadata=self.coerce_metadata(payload.get("metadata")),
                archived=bool(payload.get("archived", False)),
            )
        except RegistryError as exc:
            raise RegistryError(
                f"Invalid seed JSONL at line {line_number}: {exc}"
            ) from exc

    def infer_scenario_from_key(self, key: str) -> ScenarioKind:
        normalized = self.normalize_key(key)
        if normalized.startswith("label_"):
            raise RegistryError("Label scenario does not support persona templates.")
        if normalized.startswith("comment_"):
            return "comment"
        if normalized.startswith("chat_"):
            return "chat"
        raise RegistryError(
            "Unable to infer scenario from key. Prefix persona keys with 'chat_' or 'comment_'."
        )

    @staticmethod
    def validate_key_scenario(key: str, scenario: ScenarioKind) -> None:
        required_prefix = f"{scenario}_"
        if not key.startswith(required_prefix):
            raise RegistryError(
                f"Key '{key}' must start with '{required_prefix}' for scenario '{scenario}'."
            )

    @staticmethod
    def ensure_supported_scenario(scenario: ScenarioKind | None) -> None:
        if scenario == "label":
            raise RegistryError("Label scenario does not support persona templates.")

    @staticmethod
    def normalize_tags(value: list[str] | None) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(str(item).strip() for item in value if str(item).strip())

    @staticmethod
    def normalize_metadata(value: dict[str, Any] | None) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    @staticmethod
    def coerce_tags(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    @staticmethod
    def coerce_metadata(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}
