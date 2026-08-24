"""Schema Center's side-effect-free public interface."""

from importlib import import_module
from typing import Any


_EXPORT_MODULES = {
    "build_label_output_schema": ".schema_contract",
    "default_label_output_schema": ".schema_contract",
    "label_schema_option_entries": ".options",
    "label_schema_record_map": ".options",
    "resolve_default_label_schema_key": ".options",
    "schema_preview_text": ".schema_contract",
    "validate_label_output_schema_contract": ".schema_contract",
}
__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(name)
    return getattr(import_module(module_name, __name__), name)
