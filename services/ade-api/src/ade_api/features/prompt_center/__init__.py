"""Prompt Center public interface without runtime initialization side effects."""

from importlib import import_module
from pathlib import Path
from typing import Any, Protocol


class PromptTemplateReader(Protocol):
    """Read-only template lookup used by sibling ADE features."""

    def get_template(
        self,
        kind: str,
        key: str,
        *,
        archived: bool = False,
        scenario: str | None = None,
    ) -> dict[str, Any] | None: ...


def build_prompt_template_reader(
    project_root: Path,
    *,
    persona_db_path: Path | None = None,
    persona_seed_jsonl_path: Path | None = None,
) -> PromptTemplateReader:
    """Build the Prompt Center registry behind its read-only public contract."""

    from .registry import PromptPersonaRegistry

    return PromptPersonaRegistry(
        project_root,
        persona_db_path=persona_db_path,
        persona_seed_jsonl_path=persona_seed_jsonl_path,
    )


_EXPORT_MODULES = {
    "active_persona_records": ".template_options",
    "active_prompt_records": ".template_options",
    "append_prompt_persona_revision": ".revision_log",
    "normalize_scenario": ".template_options",
    "persona_content_map": ".template_options",
    "persona_option_entries": ".template_options",
    "prompt_content_map": ".template_options",
    "prompt_option_entries": ".template_options",
    "prompt_record_map": ".template_options",
    "read_prompt_persona_revisions": ".revision_log",
    "resolve_default_persona_key": ".template_options",
    "resolve_default_prompt_key": ".template_options",
}
__all__ = [
    *_EXPORT_MODULES,
    "PromptTemplateReader",
    "build_prompt_template_reader",
]


def __getattr__(name: str) -> Any:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(name)
    return getattr(import_module(module_name, __name__), name)
