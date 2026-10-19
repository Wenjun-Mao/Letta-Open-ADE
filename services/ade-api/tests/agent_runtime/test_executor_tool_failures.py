from __future__ import annotations

import asyncio
import json

import pytest

from ade_api.features.agent_runtime.errors import (
    RuntimeValidationError,
)
from ade_api.features.agent_runtime.executor import (
    ConversationExecutor,
    curated_tools,
)
from ade_api.features.agent_runtime.evaluation_tools import (
    evaluation_tool_registry,
)
from ade_api.features.agent_runtime.tool_policy import (
    ToolRequirement,
)


from .executor_fakes import Transport as _Transport


def test_required_tool_cannot_be_replaced_by_plausible_final_text() -> None:
    transport = _Transport(
        [
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "The weather tool failed.",
                        },
                    }
                ]
            }
        ]
    )

    with pytest.raises(RuntimeValidationError) as exc_info:
        asyncio.run(
            ConversationExecutor(transport).execute(
                model_key="source::model",
                messages=[{"role": "user", "content": "Check the weather."}],
                tools=curated_tools(
                    ("get_weather",), additional_tools=evaluation_tool_registry()
                ),
                tool_requirement=ToolRequirement(
                    tool_name="get_weather", capability="weather.current_lookup"
                ),
                timeout_seconds=30,
                max_output_tokens=100,
            )
        )

    assert exc_info.value.detail_code == "conversation_required_tool_missing"
    assert len(transport.calls) == 1


def test_required_tool_rejects_a_different_model_selected_tool() -> None:
    transport = _Transport(
        [
            {
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "wrong-tool",
                                    "type": "function",
                                    "function": {
                                        "name": "search_memory",
                                        "arguments": '{"query":"weather"}',
                                    },
                                }
                            ],
                        },
                    }
                ]
            }
        ]
    )

    async def search(_query: str, _limit: int):
        return []

    with pytest.raises(RuntimeValidationError) as exc_info:
        asyncio.run(
            ConversationExecutor(transport).execute(
                model_key="source::model",
                messages=[{"role": "user", "content": "Check the weather."}],
                tools=curated_tools(
                    ("get_weather", "search_memory"),
                    search_memory=search,
                    additional_tools=evaluation_tool_registry(),
                ),
                tool_requirement=ToolRequirement(
                    tool_name="get_weather", capability="weather.current_lookup"
                ),
                timeout_seconds=30,
                max_output_tokens=100,
            )
        )

    assert exc_info.value.detail_code == "conversation_required_tool_mismatch"
    assert len(transport.calls) == 1


def test_weather_provider_failure_is_visible_and_conversation_continues() -> None:
    transport = _Transport(
        [
            {
                "id": "request-1",
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "weather-failure",
                                    "type": "function",
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": '{"city":"FAIL_CITY"}',
                                    },
                                }
                            ],
                        },
                    }
                ],
            },
            {
                "id": "request-2",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "The weather provider is unavailable.",
                        },
                    }
                ],
            },
        ]
    )

    async def search(query: str, limit: int):
        raise AssertionError("weather must not invoke memory search")

    result = asyncio.run(
        ConversationExecutor(transport).execute(
            model_key="source::model",
            messages=[{"role": "user", "content": "Weather in FAIL_CITY?"}],
            tools=curated_tools(
                ("get_weather",), additional_tools=evaluation_tool_registry()
            ),
            timeout_seconds=30,
            max_output_tokens=100,
        )
    )

    tool_payload = json.loads(transport.calls[1][0]["messages"][-1]["content"])
    assert tool_payload["ok"] is False
    assert tool_payload == {
        "ok": False,
        "error_type": "provider_failure",
        "error": "get_weather provider is unavailable",
    }
    assert result.assistant_text == "The weather provider is unavailable."
    assert result.tool_events[0]["succeeded"] is False
    assert result.tool_events[0]["error_type"] == "RuntimeError"


def test_malformed_curated_tool_arguments_fail_the_attempt() -> None:
    transport = _Transport(
        [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "weather-invalid",
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": '{"city":"Toronto","unit":"C"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    )

    async def search(query: str, limit: int):
        return []

    with pytest.raises(
        RuntimeValidationError, match="failed closed validation"
    ) as exc_info:
        asyncio.run(
            ConversationExecutor(transport).execute(
                model_key="source::model",
                messages=[{"role": "user", "content": "hello"}],
                tools=curated_tools(
                    ("get_weather",), additional_tools=evaluation_tool_registry()
                ),
                timeout_seconds=30,
                max_output_tokens=100,
            )
        )
    assert exc_info.value.detail_code == "curated_tool_arguments_invalid"
    assert len(transport.calls) == 1


def test_unsupported_weather_fixture_argument_fails_the_attempt() -> None:
    transport = _Transport(
        [
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "weather-unsupported",
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": '{"city":"多伦"}',
                                    },
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    )

    with pytest.raises(
        RuntimeValidationError, match="supported deterministic weather fixture"
    ) as exc_info:
        asyncio.run(
            ConversationExecutor(transport).execute(
                model_key="source::model",
                messages=[{"role": "user", "content": "请查一下多伦多的天气。"}],
                tools=curated_tools(
                    ("get_weather",), additional_tools=evaluation_tool_registry()
                ),
                tool_requirement=ToolRequirement(
                    tool_name="get_weather", capability="weather.current_lookup"
                ),
                timeout_seconds=30,
                max_output_tokens=100,
            )
        )

    assert exc_info.value.detail_code == "curated_tool_arguments_invalid"
    assert len(transport.calls) == 1


def test_empty_conversation_output_has_a_stable_safe_detail_code() -> None:
    transport = _Transport(
        [
            {
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "reasoning_content": "private reasoning must not escape",
                        },
                    }
                ]
            }
        ]
    )

    with pytest.raises(RuntimeValidationError, match="neither dialogue") as exc_info:
        asyncio.run(
            ConversationExecutor(transport).execute(
                model_key="source::model",
                messages=[{"role": "user", "content": "hello"}],
                tools={},
                timeout_seconds=30,
                max_output_tokens=100,
            )
        )

    assert exc_info.value.detail_code == "conversation_output_empty"
