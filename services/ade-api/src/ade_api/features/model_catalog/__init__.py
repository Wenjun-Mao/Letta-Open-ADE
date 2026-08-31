"""Model Catalog's side-effect-free public interface.

Other features consume these exports instead of interpreting router configuration.
"""

from importlib import import_module
from typing import Any


_EXPORT_MODULES = {
    "agent_studio_llm_config_for_model": ".agent_studio",
    "commenting_runtime_defaults": ".runtime_defaults",
    "enriched_catalog_items": ".catalog",
    "labeling_runtime_defaults": ".runtime_defaults",
    "missing_required_capabilities": ".capabilities",
    "model_option_identity_sha256": ".identity",
    "model_catalog": ".catalog",
    "resolve_comment_model_selection": ".selection",
    "resolve_label_model_selection": ".selection",
    "runtime_options": ".resolution",
    "SCENARIO_DEFAULTS": ".defaults",
    "validate_capabilities_startup": ".capabilities",
}
__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(name)
    return getattr(import_module(module_name, __name__), name)
