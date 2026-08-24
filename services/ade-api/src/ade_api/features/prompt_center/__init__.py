"""Prompt Center public interface without runtime initialization side effects."""

from importlib import import_module
from typing import Any


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
__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(name)
    return getattr(import_module(module_name, __name__), name)
