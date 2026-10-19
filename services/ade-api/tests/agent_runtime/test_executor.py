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
    initial_conversation_request,
)
from ade_api.features.agent_runtime.context import estimate_tokens
from ade_api.features.agent_runtime.natural_attempt_evidence import (
    NaturalAttemptEvidence,
)
from ade_api.features.agent_runtime.tool_policy import (
    ToolRequirement,
)


from .executor_fakes import Transport as _Transport


def test_awaited_authorization_vetoes_dispatch_while_observation_cannot() -> None:
    response = {
        "id": "reply",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "Okay."},
            }
        ],
    }
    transport = _Transport([response])

    async def reject(_payload):
        raise RuntimeValidationError(
            "held H source missing", detail_code="natural_history_missing"
        )

    with pytest.raises(RuntimeValidationError) as error:
        asyncio.run(
            ConversationExecutor(transport).execute(
                model_key="source::model",
                messages=[{"role": "user", "content": "hello"}],
                timeout_seconds=30,
                max_output_tokens=100,
                authorize_request=reject,
            )
        )
    assert error.value.detail_code == "natural_history_missing"
    assert transport.calls == []

    async def allow(_payload):
        return None

    def bad_observer(_payload):
        raise OSError("optional trace write failed")

    result = asyncio.run(
        ConversationExecutor(transport).execute(
            model_key="source::model",
            messages=[{"role": "user", "content": "hello"}],
            timeout_seconds=30,
            max_output_tokens=100,
            authorize_request=allow,
            observe_request=bad_observer,
        )
    )
    assert result.assistant_text == "Okay."
    assert len(transport.calls) == 1


def test_history_stays_held_when_tool_continuation_exceeds_input_limit() -> None:
    transport = _Transport(
        [
            {
                "id": "tool-request",
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
                                        "arguments": '{"query":"tea","limit":1}',
                                    },
                                }
                            ],
                        },
                    }
                ],
            }
        ]
    )

    async def search(_query: str, _limit: int):
        return [{"value": "x" * 8000}]

    tools = curated_tools(("search_memory",), search_memory=search)
    messages = [
        {"role": "system", "content": "Historical evidence: H1 said 早上喝咖啡。"},
        {"role": "user", "content": "What happened?"},
    ]
    initial = initial_conversation_request(
        model_key="source::model",
        messages=messages,
        max_output_tokens=100,
        tools=tools,
        provider_adapter="",
    )
    limit = (
        estimate_tokens(json.dumps(initial, ensure_ascii=False, separators=(",", ":")))
        + 50
    )
    with pytest.raises(RuntimeValidationError) as error:
        asyncio.run(
            ConversationExecutor(transport).execute(
                model_key="source::model",
                messages=messages,
                tools=tools,
                timeout_seconds=30,
                max_output_tokens=100,
                input_token_limit=limit,
            )
        )
    assert error.value.detail_code == "natural_context_serialized_overflow"
    assert len(transport.calls) == 1
    assert "H1 said 早上喝咖啡。" in transport.calls[0][0]["messages"][0]["content"]


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
            tools=curated_tools(("search_memory",), search_memory=search),
            timeout_seconds=30,
            max_output_tokens=100,
        )
    )
    assert result.assistant_text == "Rocky 很可爱。"
    assert result.model_request_count == 2
    assert searches == [("Rocky", 3)]
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5}
    tool_payload = json.loads(transport.calls[1][0]["messages"][-1]["content"])
    assert tool_payload == {
        "ok": True,
        "scope": "current_user_character_relationship",
        "memories": [{"id": "fact-1", "value": "Rocky"}],
    }


def test_deepseek_required_search_uses_auto_and_replays_reasoning_with_tool_result() -> (
    None
):
    transport = _Transport(
        [
            {
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "reasoning_content": "private synthetic reasoning",
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {
                                        "name": "search_memory",
                                        "arguments": '{"query":"oolong"}',
                                    },
                                }
                            ],
                        },
                    }
                ],
            },
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "Your favorite tea is oolong.",
                        },
                    }
                ]
            },
        ]
    )

    async def search(query: str, limit: int):
        assert (query, limit) == ("oolong", 8)
        return [{"id": "fact-1", "value": "oolong"}]

    evidence = NaturalAttemptEvidence(
        run_id="synthetic-run", attempt=1, policy_binding="natural-user-assertions-v4-b"
    )
    result = asyncio.run(
        ConversationExecutor(transport, provider_adapter="deepseek_openai").execute(
            model_key="deepseek::deepseek-flash",
            messages=[{"role": "user", "content": "Search my older memory for tea."}],
            tools=curated_tools(("search_memory",), search_memory=search),
            tool_requirement=ToolRequirement(
                tool_name="search_memory", capability="memory.deep_search"
            ),
            timeout_seconds=30,
            max_output_tokens=100,
            observe_request=evidence.capture_generation_request,
        )
    )
    assert result.tool_requirement_satisfied is True
    assert result.assistant_text == "Your favorite tea is oolong."
    assert all(call[0]["tool_choice"] == "auto" for call in transport.calls)
    replay = transport.calls[1][0]["messages"]
    assert replay[-2]["reasoning_content"] == "private synthetic reasoning"
    assert replay[-1]["role"] == "tool"
    assert "private synthetic reasoning" not in result.assistant_text
    assert len(evidence.generation_requests) == 2
    assert evidence.generation_requests[1]["messages"][-1]["role"] == "tool"
    assert "private synthetic reasoning" not in str(evidence.generation_requests)
    assert result.tool_evidence[0]["content"]["memories"][0]["value"] == "oolong"
