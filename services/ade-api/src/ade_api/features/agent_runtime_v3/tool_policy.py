from __future__ import annotations

import re
import unicodedata
from collections.abc import Collection
from dataclasses import dataclass
from typing import Any, Final


TOOL_POLICY_VERSION: Final = "curated_tool_invocation_v1"
TOOL_USE_POLICY: Final = """Tool rules:
- Enabled tools are the authority for external lookups; do not invent their results.
- When an explicit external action is required, call the selected tool before giving
  a final answer, even when an argument is unfamiliar or the tool may fail.
- Treat the returned tool result as evidence. Explain a failed result honestly.
- Never claim that a tool was called or succeeded without a corresponding tool result.
"""

_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.]{0,127}")


@dataclass(frozen=True)
class ToolRequirement:
    tool_name: str
    capability: str
    source: str = "free_form_explicit_request"
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


@dataclass(frozen=True)
class _FreeFormRule:
    tool_name: str
    capability: str
    capability_markers: tuple[str, ...]
    action_markers: tuple[str, ...]

    def matches(self, content: str) -> bool:
        return any(item in content for item in self.capability_markers) and any(
            item in content for item in self.action_markers
        )


_RULES: Final = (
    _FreeFormRule(
        tool_name="get_weather",
        capability="weather.current_lookup",
        capability_markers=(
            "weather",
            "forecast",
            "temperature",
            "天气",
            "天氣",
            "气象",
            "氣象",
            "温度",
            "氣溫",
            "气温",
            "预报",
            "預報",
        ),
        action_markers=(
            "please",
            "check",
            "look up",
            "lookup",
            "find",
            "get the",
            "show me",
            "tell me",
            "what is",
            "what's",
            "how is",
            "how's",
            "weather in",
            "forecast for",
            "temperature in",
            "请",
            "請",
            "查",
            "查询",
            "查詢",
            "搜索",
            "搜尋",
            "看看",
            "告诉",
            "告訴",
            "什么",
            "什麼",
            "怎么样",
            "怎麼樣",
            "如何",
            "多少",
        ),
    ),
    _FreeFormRule(
        tool_name="search_memory",
        capability="memory.deep_search",
        capability_markers=(
            "memory",
            "memories",
            "older fact",
            "past conversation",
            "记忆",
            "記憶",
        ),
        action_markers=(
            "search",
            "look up",
            "lookup",
            "find",
            "retrieve",
            "deep search",
            "查找",
            "搜索",
            "搜尋",
            "检索",
            "檢索",
            "搜一下",
            "查一下",
        ),
    ),
)


def resolve_tool_requirement(
    current_user_content: str, enabled_tool_names: Collection[str]
) -> ToolRequirement | None:
    """Resolve one unambiguous free-form external action without model inference."""

    enabled = {str(name) for name in enabled_tool_names}
    content = unicodedata.normalize("NFKC", str(current_user_content)).casefold()
    matches = [
        rule for rule in _RULES if rule.tool_name in enabled and rule.matches(content)
    ]
    if len(matches) != 1:
        return None
    selected = matches[0]
    return ToolRequirement(
        tool_name=selected.tool_name,
        capability=selected.capability,
    )
