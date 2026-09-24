from __future__ import annotations

import pytest

from ade_api.features.agent_runtime.tool_policy import (
    TOOL_POLICY_VERSION,
    TOOL_USE_POLICY,
    ToolRequirement,
)


def test_caller_supplied_requirement_has_a_safe_structured_contract() -> None:
    requirement = ToolRequirement(
        tool_name="search_memory", capability="memory.deep_search"
    )

    assert requirement.tool_choice() == {
        "type": "function",
        "function": {"name": "search_memory"},
    }
    assert requirement.safe_payload() == {
        "mode": "explicit_action_required",
        "tool_name": "search_memory",
        "capability": "memory.deep_search",
        "source": "structured_requirement",
        "policy_version": TOOL_POLICY_VERSION,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tool_name", "get_weather\nprivate text"),
        ("capability", "weather current lookup"),
        ("source", ""),
        ("policy_version", "v2/override"),
    ],
)
def test_requirement_trace_identifiers_are_bounded(field: str, value: str) -> None:
    values = {
        "tool_name": "get_weather",
        "capability": "weather.current_lookup",
        "source": "structured_requirement",
        "policy_version": TOOL_POLICY_VERSION,
    }
    values[field] = value

    with pytest.raises(ValueError, match=f"{field} must be a bounded identifier"):
        ToolRequirement(**values)


def test_tool_instructions_leave_calls_to_model_discretion() -> None:
    assert "Choose whether to call one from context" in TOOL_USE_POLICY
    assert "Never claim that a tool was called or succeeded" in TOOL_USE_POLICY
