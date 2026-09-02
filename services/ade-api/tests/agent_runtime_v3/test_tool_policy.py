from __future__ import annotations

import pytest

from ade_api.features.agent_runtime_v3.tool_policy import (
    TOOL_POLICY_VERSION,
    resolve_tool_requirement,
)


@pytest.mark.parametrize(
    ("content", "enabled", "expected_name", "expected_capability"),
    [
        (
            "Please check the weather in Toronto.",
            ("get_weather",),
            "get_weather",
            "weather.current_lookup",
        ),
        (
            "Weather in Toronto?",
            ("get_weather",),
            "get_weather",
            "weather.current_lookup",
        ),
        (
            "请查询多伦多现在的天气。",
            ("get_weather",),
            "get_weather",
            "weather.current_lookup",
        ),
        (
            "Please search your memory for the museum I mentioned.",
            ("search_memory",),
            "search_memory",
            "memory.deep_search",
        ),
        (
            "如果当前资料没有，请搜索记忆。",
            ("search_memory",),
            "search_memory",
            "memory.deep_search",
        ),
    ],
)
def test_explicit_external_actions_resolve_to_one_typed_requirement(
    content: str,
    enabled: tuple[str, ...],
    expected_name: str,
    expected_capability: str,
) -> None:
    requirement = resolve_tool_requirement(content, enabled)

    assert requirement is not None
    assert requirement.tool_name == expected_name
    assert requirement.capability == expected_capability
    assert requirement.policy_version == TOOL_POLICY_VERSION
    assert requirement.safe_payload() == {
        "mode": "explicit_action_required",
        "tool_name": expected_name,
        "capability": expected_capability,
        "source": "free_form_explicit_request",
        "policy_version": TOOL_POLICY_VERSION,
    }


@pytest.mark.parametrize(
    "content",
    [
        "I like talking about weather.",
        "Do you like weather conversations?",
        "我喜欢下雨天的天气。",
        "That memory makes me smile.",
        "这段记忆很温暖。",
    ],
)
def test_benign_capability_mentions_remain_discretionary(content: str) -> None:
    assert resolve_tool_requirement(content, ("get_weather", "search_memory")) is None


def test_disabled_or_ambiguous_actions_are_not_forced() -> None:
    assert resolve_tool_requirement("Please check the weather.", ()) is None
    assert (
        resolve_tool_requirement(
            "Please check Toronto weather and search memory for my old address.",
            ("get_weather", "search_memory"),
        )
        is None
    )


def test_fault_fixture_values_do_not_drive_policy_resolution() -> None:
    ordinary = resolve_tool_requirement(
        "Please check Toronto weather.", ("get_weather",)
    )
    failure = resolve_tool_requirement(
        "Please check FAIL_CITY weather.", ("get_weather",)
    )

    assert ordinary is not None and failure is not None
    assert ordinary.safe_payload() == failure.safe_payload()
