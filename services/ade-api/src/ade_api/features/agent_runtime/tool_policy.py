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
- Subject-bound memory results describe the current user or account, not the
  assistant persona. Attribute them correctly and state relevant values directly.
- Never claim that a tool was called or succeeded without a corresponding tool result.
"""

_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.]{0,127}")
_CLAUSE_BOUNDARY = re.compile(r"[.!?;,。！？；，\n]+|\b(?:but|however|whereas)\b")
_ENGLISH_NEGATED_ACTION = re.compile(
    r"\b(?:do\s+not|don't|never|avoid|without|rather\s+than|stop|"
    r"no\s+need\s+to|needn't|cannot|can't|not)"
    r"(?:\s+[a-z][a-z'-]*){0,5}\s*$",
    re.IGNORECASE,
)
_CHINESE_NEGATED_ACTION = re.compile(
    r"(?:不要|别(?:再)?|勿|無需|无需|不(?:要|用|必|需|想|是))(?:.{0,12})$"
)


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
        return any(
            any(item in clause for item in self.capability_markers)
            and any(
                not _action_is_negated(clause, action_start)
                for marker in self.action_markers
                for action_start in _marker_offsets(clause, marker)
            )
            for clause in _CLAUSE_BOUNDARY.split(content)
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


def _marker_offsets(content: str, marker: str) -> tuple[int, ...]:
    """Return every literal marker occurrence so one negated action is not decisive."""

    offsets: list[int] = []
    start = content.find(marker)
    while start >= 0:
        offsets.append(start)
        start = content.find(marker, start + 1)
    return tuple(offsets)


def _action_is_negated(content: str, action_start: int) -> bool:
    """Recognize a direct opt-out in the action's local clause.

    This is intentionally a bounded syntactic check: it only suppresses a forced
    call. Ambiguous wording remains discretionary instead of inventing a tool
    requirement from keywords alone.
    """

    local_prefix = content[:action_start]
    return bool(
        _ENGLISH_NEGATED_ACTION.search(local_prefix)
        or _CHINESE_NEGATED_ACTION.search(local_prefix)
    )
