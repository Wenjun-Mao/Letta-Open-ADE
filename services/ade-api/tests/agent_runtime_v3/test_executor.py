from __future__ import annotations

import asyncio
import json

import pytest

from ade_api.features.agent_runtime_v3.errors import RuntimeValidationError
from ade_api.features.agent_runtime_v3.executor import (
    ConversationExecutor,
    curated_tools,
)


class _Transport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def chat_completion(self, payload, *, timeout_seconds):
        self.calls.append((payload, timeout_seconds))
        return self.responses.pop(0)


def test_executor_runs_only_subject_bound_memory_search() -> None:
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
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {
                                        "name": "search_memory",
                                        "arguments": '{"query":"Rocky","limit":3}',
                                    },
                                }
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 10},
            },
            {
                "id": "request-2",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "Rocky 很可爱。"},
                    }
                ],
                "usage": {"completion_tokens": 5},
            },
        ]
    )
    searches = []

    async def search(query: str, limit: int):
        searches.append((query, limit))
        return [{"id": "fact-1", "value": "Rocky"}]

    result = asyncio.run(
        ConversationExecutor(transport).execute(
            model_key="source::model",
            messages=[{"role": "user", "content": "我的狗叫什么？"}],
            search_memory=search,
            timeout_seconds=30,
            max_output_tokens=100,
        )
    )
    assert result.assistant_text == "Rocky 很可爱。"
    assert result.model_request_count == 2
    assert searches == [("Rocky", 3)]
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5}


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
                search_memory=search,
                timeout_seconds=30,
                max_output_tokens=100,
            )
        )


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
            tools=curated_tools(("get_weather",), search_memory=search),
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
            tools=curated_tools(("get_weather",), search_memory=search),
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
                tools=curated_tools(("get_weather",), search_memory=search),
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
