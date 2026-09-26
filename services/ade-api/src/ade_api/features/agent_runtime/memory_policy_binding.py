"""Executable memory policy bindings for fresh turns and worker attempts."""

from .errors import RuntimeValidationError
from .natural_context import HISTORY_PROBE_POLICY, NATURAL_POLICY_BINDINGS


TYPED_MEMORY_POLICY_VERSION = "typed-user-facts-v2"


def require_executable_memory_policy(
    binding: str, *, purpose: str | None = None, runtime_mode: str | None = None
) -> None:
    if binding == HISTORY_PROBE_POLICY:
        if purpose == "evaluation" and runtime_mode == "development":
            return
        raise RuntimeValidationError(
            "History probe policy is restricted to development evaluation",
            detail_code="natural_history_binding",
        )
    if binding == TYPED_MEMORY_POLICY_VERSION or binding in NATURAL_POLICY_BINDINGS:
        return
    raise RuntimeValidationError(
        "Obsolete memory policy binding is read-only for fresh sends",
        detail_code="obsolete_memory_policy_binding",
    )
