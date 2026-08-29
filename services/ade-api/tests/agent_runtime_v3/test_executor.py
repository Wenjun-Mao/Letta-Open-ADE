from __future__ import annotations

import asyncio

import pytest

from ade_api.features.agent_runtime_v3.errors import RuntimeValidationError
from ade_api.features.agent_runtime_v3.executor import ConversationExecutor


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

    with pytest.raises(RuntimeValidationError, match="Only search_memory"):
        asyncio.run(
            ConversationExecutor(transport).execute(
                model_key="source::model",
                messages=[{"role": "user", "content": "hello"}],
                search_memory=search,
                timeout_seconds=30,
                max_output_tokens=100,
            )
        )
