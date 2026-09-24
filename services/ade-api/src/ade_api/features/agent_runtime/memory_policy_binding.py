"""Executable memory policy bindings for fresh turns and worker attempts."""

from .errors import RuntimeValidationError
from .natural_context import NATURAL_POLICY_BINDINGS


TYPED_MEMORY_POLICY_VERSION = "typed-user-facts-v2"


def require_executable_memory_policy(binding: str) -> None:
    if binding == TYPED_MEMORY_POLICY_VERSION or binding in NATURAL_POLICY_BINDINGS:
        return
    raise RuntimeValidationError(
        "Obsolete memory policy binding is read-only for fresh sends",
        detail_code="obsolete_memory_policy_binding",
    )
