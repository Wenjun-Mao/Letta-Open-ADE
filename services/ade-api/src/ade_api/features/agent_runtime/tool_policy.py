"""Curated tool instructions and explicit structured requirement contract."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Final


TOOL_POLICY_VERSION: Final = "curated_tool_invocation_v2"
TOOL_USE_POLICY: Final = """Tool rules:
- Enabled tools are available for external lookups when their results would
  help answer the current request. Choose whether to call one from context.
- Treat a returned tool result as evidence. Explain a failed result honestly.
- Subject-bound memory results describe the current user or account, not the
  assistant persona. Attribute them correctly and state relevant values directly.
- Never claim that a tool was called or succeeded without a corresponding result.
"""

_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.]{0,127}")


@dataclass(frozen=True)
class ToolRequirement:
    """A caller-supplied requirement, never inferred from conversational text."""

    tool_name: str
    capability: str
    source: str = "structured_requirement"
    policy_version: str = TOOL_POLICY_VERSION

    def __post_init__(self) -> None:
        for label, value in (
            ("tool_name", self.tool_name),
            ("capability", self.capability),
            ("source", self.source),
            ("policy_version", self.policy_version),
        ):
            if not _IDENTIFIER.fullmatch(value):
                raise ValueError(f"{label} must be a bounded identifier")

    def tool_choice(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {"name": self.tool_name},
        }

    def safe_payload(self) -> dict[str, str]:
        return {
            "mode": "explicit_action_required",
            "tool_name": self.tool_name,
            "capability": self.capability,
            "source": self.source,
            "policy_version": self.policy_version,
        }
