from __future__ import annotations

import asyncio
import json

import pytest

import ade_api.features.agent_runtime_v3.turn_execution as turn_execution_module
from ade_api.features.agent_runtime_v3.errors import (
    RuntimeNotReady,
    RuntimeValidationError,
)
from ade_api.features.agent_runtime_v3.executor import (
    ConversationExecutor,
    curated_tools,
)
from ade_api.features.agent_runtime_v3.provider_tracing import AttemptTrace
from ade_api.features.agent_runtime_v3.turn_execution import TurnExecution
from ade_api.features.agent_runtime_v3.tool_policy import (
    TOOL_USE_POLICY,
    ToolRequirement,
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


def test_enabled_tools_add_an_evidence_bound_usage_policy() -> None:
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

    asyncio.run(
        ConversationExecutor(transport).execute(
            model_key="source::model",
            messages=[
                {"role": "system", "content": "persona"},
                {"role": "user", "content": "ordinary dialogue"},
            ],
            tools=curated_tools(("get_weather",)),
            timeout_seconds=30,
            max_output_tokens=100,
        )
    )

    payload = transport.calls[0][0]
    assert payload["tool_choice"] == "auto"
    assert payload["messages"] == [
        {"role": "system", "content": f"persona\n\n{TOOL_USE_POLICY}"},
        {"role": "user", "content": "ordinary dialogue"},
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
            tools=curated_tools(("get_weather",)),
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
                tools=curated_tools(("get_weather",)),
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
                    ("get_weather", "search_memory"), search_memory=search
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


def test_agent_studio_execution_rechecks_release_evidence_before_provider_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _NoProviderTransport:
        async def catalog(self, **_kwargs):
            raise AssertionError("provider work must not begin before the release gate")

    class _Settings:
        agent_runtime_v3_mode = "release"
        model_discovery_timeout_seconds = 5.0

    execution = TurnExecution(
        engine=object(),  # type: ignore[arg-type]
        transport=_NoProviderTransport(),  # type: ignore[arg-type]
        settings=_Settings(),  # type: ignore[arg-type]
    )

    async def _load_state(_run):
        return {
            "conversation": {"purpose": "agent_studio"},
            "definition": {},
        }

    monkeypatch.setattr(execution, "_load_state", _load_state)

    def _reject_release(_mode: str) -> None:
        raise RuntimeNotReady("cutover evidence was withdrawn")

    monkeypatch.setattr(
        turn_execution_module,
        "ensure_agent_studio_release_ready",
        _reject_release,
        raising=False,
    )

    with pytest.raises(RuntimeNotReady, match="withdrawn"):
        asyncio.run(
            execution.execute(
                {"id": "run-1"},
                deadline=10_000_000.0,
                trace=AttemptTrace(attempt=1),
            )
        )
