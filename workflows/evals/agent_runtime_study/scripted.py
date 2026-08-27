from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelResponse, TextPart, ThinkingPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from .adapters import CustomLoopAdapter, PydanticAIAdapter


@dataclass(frozen=True)
class ScriptToolCall:
    name: str
    arguments: dict[str, Any] | str
    call_id: str


@dataclass(frozen=True)
class ScriptStep:
    text: str = ""
    reasoning: str = ""
    tool_calls: tuple[ScriptToolCall, ...] = ()
    error_status: int | None = None
    delay_seconds: float = 0.0


class SharedScript:
    def __init__(self, steps: tuple[ScriptStep, ...]) -> None:
        self.steps = list(steps)
        self.request_count = 0
        self._lock = asyncio.Lock()

    async def next_step(self) -> ScriptStep:
        async with self._lock:
            self.request_count += 1
            if not self.steps:
                raise RuntimeError("Script has no remaining model steps")
            step = self.steps.pop(0)
        if step.delay_seconds:
            await asyncio.sleep(step.delay_seconds)
        if step.error_status is not None:
            raise ModelHTTPError(
                status_code=step.error_status,
                model_name="scripted-model",
                body={"error": "scripted provider error"},
            )
        return step


class ScriptedTransport:
    def __init__(self, script: SharedScript) -> None:
        self.script = script

    async def complete(
        self,
        *,
        model_key: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> dict[str, Any]:
        try:
            step = await self.script.next_step()
        except ModelHTTPError as exc:
            from .adapters.base import NonRetryableModelError, RetryableModelError

            error_type = (
                RetryableModelError
                if exc.status_code == 429 or exc.status_code >= 500
                else NonRetryableModelError
            )
            raise error_type(str(exc)) from exc
        tool_calls = [
            {
                "id": call.call_id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": (
                        call.arguments
                        if isinstance(call.arguments, str)
                        else json.dumps(call.arguments, ensure_ascii=False)
                    ),
                },
            }
            for call in step.tool_calls
        ]
        return {
            "id": f"scripted-{self.script.request_count}",
            "model": model_key,
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "tool_calls" if tool_calls else "stop",
                    "message": {
                        "role": "assistant",
                        "content": step.text or None,
                        "reasoning_content": step.reasoning or None,
                        "tool_calls": tool_calls,
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        }


def function_model(script: SharedScript) -> FunctionModel:
    async def respond(_messages, _agent_info: AgentInfo) -> ModelResponse:
        step = await script.next_step()
        parts = []
        if step.reasoning:
            parts.append(ThinkingPart(step.reasoning))
        parts.extend(
            ToolCallPart(
                tool_name=call.name,
                args=call.arguments,
                tool_call_id=call.call_id,
            )
            for call in step.tool_calls
        )
        if step.text:
            parts.append(TextPart(step.text))
        return ModelResponse(parts=parts)

    return FunctionModel(respond, model_name="scripted-model")


def scripted_adapter(adapter_name: str, script: SharedScript):
    if adapter_name == "custom_loop":
        return CustomLoopAdapter(ScriptedTransport(script))
    if adapter_name == "pydantic_ai":
        return PydanticAIAdapter(
            base_url="http://unused.invalid/v1",
            api_key="unused",
            model_override=function_model(script),
        )
    raise ValueError(adapter_name)
