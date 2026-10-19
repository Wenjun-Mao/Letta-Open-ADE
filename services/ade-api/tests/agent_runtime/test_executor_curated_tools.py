from __future__ import annotations

import asyncio

import pytest

from ade_api.features.agent_runtime.errors import (
    RuntimeValidationError,
)
from ade_api.features.agent_runtime.executor import (
    ConversationExecutor,
    curated_tools,
)
from ade_api.features.agent_runtime.evaluation_tools import (
    WEATHER_TOOL,
    evaluation_tool_registry,
)
from ade_api.features.agent_runtime.tool_policy import (
    TOOL_USE_POLICY,
    ToolRequirement,
)


from .executor_fakes import Transport as _Transport


def test_executor_rejects_arbitrary_tool_names() -> None:
    transport = _Transport(
        [
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "function": {"name": "shell", "arguments": "{}"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    )

    async def search(query: str, limit: int):
        return []

    with pytest.raises(RuntimeValidationError, match="not enabled"):
        asyncio.run(
            ConversationExecutor(transport).execute(
                model_key="source::model",
                messages=[{"role": "user", "content": "hello"}],
                tools=curated_tools(("search_memory",), search_memory=search),
                timeout_seconds=30,
                max_output_tokens=100,
            )
        )


def test_weather_fixture_registry_is_not_available_without_evaluation() -> None:
    with pytest.raises(RuntimeValidationError, match="Unknown or unavailable"):
        curated_tools(("get_weather",))


def test_search_memory_arguments_cannot_select_another_subject() -> None:
    transport = _Transport(
        [
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "subject-override",
                                    "function": {
                                        "name": "search_memory",
                                        "arguments": (
                                            '{"query":"Rocky",'
                                            '"memory_subject_id":"other-subject"}'
                                        ),
                                    },
                                }
                            ]
                        }
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
                messages=[{"role": "user", "content": "hello"}],
                tools=curated_tools(("search_memory",), search_memory=search),
                timeout_seconds=30,
                max_output_tokens=100,
            )
        )

    assert exc_info.value.detail_code == "curated_tool_arguments_invalid"


def test_executor_dispatches_the_enabled_curated_weather_tool() -> None:
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
                                    "id": "weather-1",
                                    "type": "function",
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": '{"city":"Toronto"}',
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
                            "content": "Toronto is clear at 21 C.",
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
            messages=[{"role": "user", "content": "Weather in Toronto?"}],
            tools=curated_tools(
                ("get_weather",), additional_tools=evaluation_tool_registry()
            ),
            timeout_seconds=30,
            max_output_tokens=100,
        )
    )

    assert [tool["function"]["name"] for tool in transport.calls[0][0]["tools"]] == [
        "get_weather"
    ]
    assert result.tool_events == [
        {
            "request_number": 1,
            "call_id": "weather-1",
            "name": "get_weather",
            "arguments": {"city": "Toronto"},
            "result_count": 0,
            "succeeded": True,
            "error_type": None,
        }
    ]


def test_weather_tool_schema_declares_its_finite_fixture_domain() -> None:
    city_schema = WEATHER_TOOL["function"]["parameters"]["properties"]["city"]

    assert set(city_schema["enum"]) == {
        "Toronto",
        "toronto",
        "Beijing",
        "beijing",
        "北京",
        "多伦多",
        "FAIL_CITY",
        "fail_city",
    }


def test_enabled_tool_remains_discretionary_for_a_free_form_lookup_request() -> None:
    transport = _Transport(
        [
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "Hello."},
                    }
                ]
            }
        ]
    )

    result = asyncio.run(
        ConversationExecutor(transport).execute(
            model_key="source::model",
            messages=[
                {"role": "system", "content": "persona"},
                {"role": "user", "content": "Please check Toronto weather."},
            ],
            tools=curated_tools(
                ("get_weather",), additional_tools=evaluation_tool_registry()
            ),
            timeout_seconds=30,
            max_output_tokens=100,
        )
    )

    payload = transport.calls[0][0]
    assert payload["tool_choice"] == "auto"
    assert result.assistant_text == "Hello."
    assert result.tool_events == []
    assert result.tool_requirement is None
    assert payload["messages"] == [
        {"role": "system", "content": f"persona\n\n{TOOL_USE_POLICY}"},
        {"role": "user", "content": "Please check Toronto weather."},
    ]


def test_required_tool_is_forced_once_and_a_failed_result_can_be_explained() -> None:
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
                                    "id": "weather-required",
                                    "type": "function",
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": '{"city":"FAIL_CITY"}',
                                    },
                                }
                            ],
                        },
                    }
                ]
            },
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "The weather provider is unavailable.",
                        },
                    }
                ]
            },
        ]
    )
    requirement = ToolRequirement(
        tool_name="get_weather", capability="weather.current_lookup"
    )

    result = asyncio.run(
        ConversationExecutor(transport).execute(
            model_key="source::model",
            messages=[{"role": "user", "content": "Check FAIL_CITY weather."}],
            tools=curated_tools(
                ("get_weather",), additional_tools=evaluation_tool_registry()
            ),
            tool_requirement=requirement,
            timeout_seconds=30,
            max_output_tokens=100,
        )
    )

    assert transport.calls[0][0]["tool_choice"] == {
        "type": "function",
        "function": {"name": "get_weather"},
    }
    assert transport.calls[1][0]["tool_choice"] == "auto"
    assert result.tool_requirement == requirement
    assert result.tool_requirement_satisfied is True
    assert result.tool_events[0]["succeeded"] is False
