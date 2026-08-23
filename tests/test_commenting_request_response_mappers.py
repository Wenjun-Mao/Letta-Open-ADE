from __future__ import annotations

import pytest

from agent_platform_api.services.commenting_requests import (
    build_comment_request_payload,
    build_structured_output_compatibility_payload,
)
from agent_platform_api.services.commenting_responses import (
    map_comment_provider_response,
)


def test_comment_request_builder_preserves_structured_and_vllm_controls() -> None:
    payload = build_comment_request_payload(
        model="qwen",
        system_prompt="System prompt",
        persona_prompt="Persona prompt",
        news_input="News input",
        task_shape="structured_output",
        max_tokens=0,
        cache_prompt=False,
        source_adapter="vllm_openai",
        enable_thinking=True,
        enable_thinking_is_explicit=True,
        temperature=0.8,
        top_p=0.9,
        top_k=32,
    )

    assert payload["model"] == "qwen"
    assert "max_tokens" not in payload
    assert payload["temperature"] == 0.8
    assert payload["top_p"] == 0.9
    assert payload["top_k"] == 32
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["chat_template_kwargs"] == {"enable_thinking": True}
    assert "cache_prompt" not in payload


def test_comment_request_builder_keeps_llama_cache_and_omits_implicit_thinking() -> (
    None
):
    payload = build_comment_request_payload(
        model="gemma",
        system_prompt="System prompt",
        persona_prompt="Persona prompt",
        news_input="News input",
        task_shape="all_in_system",
        max_tokens=128,
        cache_prompt=True,
        source_adapter="llama_cpp_server",
        enable_thinking=False,
        enable_thinking_is_explicit=False,
        temperature=0.6,
        top_p=1.0,
        top_k=None,
    )

    assert payload["cache_prompt"] is True
    assert "chat_template_kwargs" not in payload
    assert "[Persona]" in payload["messages"][0]["content"]


def test_structured_output_compatibility_payload_removes_only_response_format() -> None:
    primary = build_comment_request_payload(
        model="qwen",
        system_prompt="System prompt",
        persona_prompt="Persona prompt",
        news_input="News input",
        task_shape="structured_output",
        max_tokens=256,
        cache_prompt=False,
        source_adapter=None,
        enable_thinking=False,
        enable_thinking_is_explicit=False,
        temperature=0.6,
        top_p=1.0,
        top_k=None,
    )

    fallback = build_structured_output_compatibility_payload(primary)

    assert "response_format" in primary
    assert "response_format" not in fallback
    assert fallback["model"] == primary["model"]
    assert fallback["messages"] == primary["messages"]
    assert fallback["max_tokens"] == primary["max_tokens"]


def test_comment_response_mapper_returns_structured_reasoning_and_diagnostics() -> None:
    raw_request = {"model": "qwen", "response_format": {"type": "json_schema"}}
    raw_reply = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "reasoning_content": '{"comment":"这是一条可发布的评论。"}',
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"total_tokens": 12},
    }
    runtime = {"timeout_seconds": 180.0, "retry_count": 0}

    result = map_comment_provider_response(
        data=raw_reply,
        payload=raw_request,
        runtime=runtime,
        task_shape="structured_output",
        max_tokens=256,
    )

    assert result["content"] == "这是一条可发布的评论。"
    assert result["content_source"] == "structured_json_reasoning_content"
    assert result["selected_attempt"] == "structured_output"
    assert result["finish_reason"] == "stop"
    assert result["usage"] == {"total_tokens": 12}
    assert result["raw_request"] is raw_request
    assert result["raw_reply"] is raw_reply
    assert result["timeout_seconds"] == 180.0
    assert result["retry_count"] == 0


def test_comment_response_mapper_preserves_missing_choice_error() -> None:
    with pytest.raises(
        ValueError,
        match="Comment provider returned no choices; task_shape=classic; max_tokens=64",
    ):
        map_comment_provider_response(
            data={"choices": []},
            payload={"model": "qwen"},
            runtime={},
            task_shape="classic",
            max_tokens=64,
        )


def test_comment_response_mapper_preserves_non_stop_finish_reason_error() -> None:
    with pytest.raises(
        ValueError,
        match="finish_reason=length.*task_shape=classic.*max_tokens=64",
    ):
        map_comment_provider_response(
            data={
                "choices": [
                    {
                        "message": {"content": ""},
                        "finish_reason": "length",
                    }
                ]
            },
            payload={"model": "qwen"},
            runtime={},
            task_shape="classic",
            max_tokens=64,
        )
