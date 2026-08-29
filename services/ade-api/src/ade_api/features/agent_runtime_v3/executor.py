from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from .errors import RuntimeValidationError
from .router_transport import RouterTransport


SEARCH_MEMORY_TOOL = {
    "type": "function",
    "function": {
        "name": "search_memory",
        "description": "Search older committed facts for the current memory subject.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["query"],
        },
    },
}


class SearchMemoryHandler(Protocol):
    async def __call__(self, query: str, limit: int) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class ExecutorResult:
    assistant_text: str
    usage: dict[str, int]
    model_request_count: int
    tool_events: list[dict[str, Any]]
    finish_reason: str
    provider_request_ids: list[str]


class ConversationExecutor:
    def __init__(self, transport: RouterTransport) -> None:
        self.transport = transport

    async def execute(
        self,
        *,
        model_key: str,
        messages: list[dict[str, Any]],
        search_memory: SearchMemoryHandler,
        timeout_seconds: float,
        max_output_tokens: int,
        max_model_requests: int = 6,
        enable_search_memory: bool = True,
    ) -> ExecutorResult:
        working_messages = [dict(message) for message in messages]
        total_usage: dict[str, int] = {}
        tool_events: list[dict[str, Any]] = []
        request_ids: list[str] = []
        for request_number in range(1, max_model_requests + 1):
            payload: dict[str, Any] = {
                "model": model_key,
                "messages": working_messages,
                "max_tokens": max_output_tokens,
                "stream": False,
            }
            if enable_search_memory:
                payload.update({"tools": [SEARCH_MEMORY_TOOL], "tool_choice": "auto"})
            response = await self.transport.chat_completion(
                payload, timeout_seconds=timeout_seconds
            )
            _merge_usage(total_usage, response.get("usage"))
            request_id = str(response.get("id", "") or "")
            if request_id:
                request_ids.append(request_id)
            message, finish_reason = _first_choice(response)
            tool_calls = message.get("tool_calls")
            if isinstance(tool_calls, list) and tool_calls:
                if not enable_search_memory:
                    raise RuntimeValidationError(
                        "Conversation model called a tool that is not enabled"
                    )
                working_messages.append(message)
                for raw_call in tool_calls:
                    call_id, arguments = _parse_search_call(raw_call)
                    result = await search_memory(
                        str(arguments["query"]), int(arguments.get("limit", 8))
                    )
                    tool_events.append(
                        {
                            "call_id": call_id,
                            "name": "search_memory",
                            "arguments": arguments,
                            "result_count": len(result),
                        }
                    )
                    working_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": "search_memory",
                            "content": json.dumps(
                                {"facts": result}, ensure_ascii=False, default=str
                            ),
                        }
                    )
                continue
            content = str(message.get("content", "") or "").strip()
            if not content:
                raise RuntimeValidationError(
                    "Conversation model returned neither dialogue nor a tool call"
                )
            return ExecutorResult(
                assistant_text=content,
                usage=total_usage,
                model_request_count=request_number,
                tool_events=tool_events,
                finish_reason=finish_reason,
                provider_request_ids=request_ids,
            )
        raise RuntimeValidationError("Conversation model exceeded its tool-step budget")


def _first_choice(response: dict[str, Any]) -> tuple[dict[str, Any], str]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise RuntimeValidationError("Model response did not contain a choice")
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        raise RuntimeValidationError("Model response choice did not contain a message")
    return dict(message), str(choice.get("finish_reason", "") or "")


def _parse_search_call(raw_call: object) -> tuple[str, dict[str, Any]]:
    if not isinstance(raw_call, dict):
        raise RuntimeValidationError("Tool call must be an object")
    call_id = str(raw_call.get("id", "") or "").strip()
    function = raw_call.get("function")
    if not call_id or not isinstance(function, dict):
        raise RuntimeValidationError("Tool call requires id and function")
    if str(function.get("name", "")) != "search_memory":
        raise RuntimeValidationError("Only search_memory is available in v3 preview")
    raw_arguments = function.get("arguments", "{}")
    try:
        arguments = (
            json.loads(raw_arguments)
            if isinstance(raw_arguments, str)
            else raw_arguments
        )
    except json.JSONDecodeError as exc:
        raise RuntimeValidationError(
            "search_memory arguments are invalid JSON"
        ) from exc
    if not isinstance(arguments, dict) or not str(arguments.get("query", "")).strip():
        raise RuntimeValidationError("search_memory requires a non-empty query")
    unknown = set(arguments) - {"query", "limit"}
    if unknown:
        raise RuntimeValidationError(
            f"search_memory received unexpected arguments: {sorted(unknown)}"
        )
    limit = int(arguments.get("limit", 8))
    if not 1 <= limit <= 20:
        raise RuntimeValidationError("search_memory limit must be between 1 and 20")
    return call_id, {"query": str(arguments["query"]), "limit": limit}


def _merge_usage(total: dict[str, int], raw_usage: object) -> None:
    if not isinstance(raw_usage, dict):
        return
    for key, value in raw_usage.items():
        if isinstance(value, int) and not isinstance(value, bool):
            total[str(key)] = total.get(str(key), 0) + value
