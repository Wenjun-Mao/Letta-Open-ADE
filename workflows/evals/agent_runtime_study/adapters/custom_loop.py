from __future__ import annotations

import json
from typing import Any

from ..contracts import ExecutorRequest, ExecutorResult, RunEventType
from .base import (
    ExecutorError,
    ModelProtocolError,
    NonRetryableModelError,
    with_trace,
)
from .transport import ChatCompletionsTransport


def _text_content(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
        return "".join(parts)
    return "" if value is None else str(value)


def _usage(payload: object) -> dict[str, int]:
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, int] = {}
    for key, value in payload.items():
        if isinstance(value, (int, float)):
            normalized[str(key)] = int(value)
    return normalized


def _merge_usage(target: dict[str, int], incoming: dict[str, int]) -> None:
    for key, value in incoming.items():
        target[key] = target.get(key, 0) + value


class CustomLoopAdapter:
    name = "custom_loop"

    def __init__(self, transport: ChatCompletionsTransport) -> None:
        self.transport = transport

    async def execute(self, request: ExecutorRequest) -> ExecutorResult:
        events: list[tuple[RunEventType, dict[str, Any]]] = []
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": request.context.system_prompt},
            {"role": "user", "content": request.context.user_prompt},
        ]
        raw_messages: list[dict[str, Any]] = list(messages)
        reasoning: list[str] = []
        usage: dict[str, int] = {}
        tools = [definition.openai_payload() for definition in request.tools]

        for model_request_index in range(1, request.max_model_requests + 1):
            if request.cancellation.is_set():
                raise NonRetryableModelError(
                    "Run cancelled before model request",
                    events=tuple(events),
                    raw_messages=tuple(raw_messages),
                )
            events.append(
                (
                    RunEventType.MODEL_REQUEST,
                    {
                        "adapter": self.name,
                        "model_request_index": model_request_index,
                        "model_key": request.model_key,
                        "message_count": len(messages),
                        "tool_count": len(tools),
                    },
                )
            )
            try:
                payload = await self.transport.complete(
                    model_key=request.model_key,
                    messages=messages,
                    tools=tools,
                    timeout_seconds=request.timeout_seconds,
                    max_output_tokens=request.max_output_tokens,
                )
            except ExecutorError as exc:
                raise with_trace(exc, events=events, raw_messages=raw_messages) from exc
            choice = self._first_choice(payload, events, raw_messages)
            message = choice.get("message")
            if not isinstance(message, dict):
                raise ModelProtocolError(
                    "Chat completion choice has no message object",
                    events=tuple(events),
                    raw_messages=tuple(raw_messages),
                )
            assistant_text = _text_content(message.get("content"))
            reasoning_text = _text_content(
                message.get("reasoning_content") or message.get("reasoning")
            ).strip()
            if reasoning_text:
                reasoning.append(reasoning_text)
            tool_calls = message.get("tool_calls") or []
            if not isinstance(tool_calls, list):
                raise ModelProtocolError(
                    "assistant tool_calls must be an array",
                    events=tuple(events),
                    raw_messages=tuple(raw_messages),
                )
            events.append(
                (
                    RunEventType.MODEL_RESPONSE,
                    {
                        "adapter": self.name,
                        "model_request_index": model_request_index,
                        "finish_reason": choice.get("finish_reason"),
                        "text_length": len(assistant_text),
                        "reasoning_length": len(reasoning_text),
                        "tool_call_count": len(tool_calls),
                    },
                )
            )
            _merge_usage(usage, _usage(payload.get("usage")))
            assistant_wire = {
                "role": "assistant",
                "content": assistant_text or None,
            }
            if reasoning_text:
                assistant_wire["reasoning_content"] = reasoning_text
            if tool_calls:
                assistant_wire["tool_calls"] = tool_calls
            messages.append(assistant_wire)
            raw_messages.append(dict(assistant_wire))

            if not tool_calls:
                if not assistant_text.strip():
                    events.append(
                        (
                            RunEventType.PROTOCOL_REPAIR,
                            {
                                "model_request_index": model_request_index,
                                "reason": "reasoning_only_or_empty_completion",
                            },
                        )
                    )
                    repair_message = {
                        "role": "user",
                        "content": (
                            "Your previous completion contained no user-visible "
                            "answer or tool call. Continue the same turn now: call "
                            "a required tool, or provide the final answer."
                        ),
                    }
                    messages.append(repair_message)
                    raw_messages.append(dict(repair_message))
                    continue
                return ExecutorResult(
                    assistant_text=assistant_text,
                    reasoning=tuple(reasoning),
                    events=tuple(events),
                    raw_messages=tuple(raw_messages),
                    usage=usage,
                    model_request_count=model_request_index,
                )

            for position, raw_call in enumerate(tool_calls, 1):
                if request.cancellation.is_set():
                    raise NonRetryableModelError(
                        "Run cancelled before tool execution",
                        events=tuple(events),
                        raw_messages=tuple(raw_messages),
                    )
                call_id, name, arguments = self._tool_call(
                    raw_call, model_request_index, position
                )
                events.append(
                    (
                        RunEventType.TOOL_CALL,
                        {"call_id": call_id, "name": name, "arguments": arguments},
                    )
                )
                result = await request.tool_session.execute(name, arguments, call_id)
                events.append(
                    (
                        RunEventType.TOOL_RESULT,
                        {
                            "call_id": call_id,
                            "name": name,
                            "succeeded": bool(result.get("ok", True)),
                            "result": result,
                        },
                    )
                )
                tool_message = {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
                messages.append(tool_message)
                raw_messages.append(dict(tool_message))

        raise NonRetryableModelError(
            f"Model exceeded {request.max_model_requests} requests",
            events=tuple(events),
            raw_messages=tuple(raw_messages),
        )

    @staticmethod
    def _first_choice(
        payload: dict[str, Any],
        events: list[tuple[RunEventType, dict[str, Any]]],
        raw_messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ModelProtocolError(
                "Chat completion has no choices",
                events=tuple(events),
                raw_messages=tuple(raw_messages),
            )
        choice = choices[0]
        if not isinstance(choice, dict):
            raise ModelProtocolError(
                "Chat completion choice is not an object",
                events=tuple(events),
                raw_messages=tuple(raw_messages),
            )
        return choice

    @staticmethod
    def _tool_call(
        raw_call: object, model_request_index: int, position: int
    ) -> tuple[str, str, dict[str, Any]]:
        fallback_id = f"call_{model_request_index}_{position}"
        if not isinstance(raw_call, dict):
            return fallback_id, "unknown_tool", {"_malformed_call": str(raw_call)}
        call_id = str(raw_call.get("id") or fallback_id)
        function = raw_call.get("function")
        if not isinstance(function, dict):
            return call_id, "unknown_tool", {"_malformed_call": raw_call}
        name = str(function.get("name") or "unknown_tool")
        raw_arguments = function.get("arguments") or "{}"
        if isinstance(raw_arguments, dict):
            return call_id, name, raw_arguments
        try:
            arguments = json.loads(str(raw_arguments))
        except json.JSONDecodeError:
            return call_id, name, {"_malformed_arguments": str(raw_arguments)}
        if not isinstance(arguments, dict):
            return call_id, name, {"_malformed_arguments": arguments}
        return call_id, name, arguments
