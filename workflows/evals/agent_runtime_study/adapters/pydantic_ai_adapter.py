from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any

import openai
from openai import AsyncOpenAI
from pydantic_core import to_jsonable_python

from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from ..contracts import ExecutorRequest, ExecutorResult, RunEventType, ToolDefinition
from .base import NonRetryableModelError, RetryableModelError


class PydanticAIAdapter:
    name = "pydantic_ai"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model_override: Model | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_override = model_override

    async def execute(self, request: ExecutorRequest) -> ExecutorResult:
        initial_event = (
            RunEventType.MODEL_REQUEST,
            {
                "adapter": self.name,
                "model_request_index": 1,
                "model_key": request.model_key,
                "tool_count": len(request.tools),
            },
        )
        if request.cancellation.is_set():
            raise NonRetryableModelError(
                "Run cancelled before model request", events=(initial_event,)
            )
        model = self.model_override or self._model(request)
        pydantic_tools = tuple(
            self._tool(definition, request) for definition in request.tools
        )
        agent = Agent(
            model,
            instructions=request.context.system_prompt,
            tools=pydantic_tools,
            retries={"tools": 0, "output": 0},
            tool_timeout=request.timeout_seconds,
        )
        try:
            result = await agent.run(
                request.context.user_prompt,
                retries={"tools": 0, "output": 0},
                usage_limits=UsageLimits(
                    request_limit=request.max_model_requests,
                    tool_calls_limit=request.max_model_requests
                    * max(1, len(request.tools)),
                ),
                model_settings={"max_tokens": request.max_output_tokens},
            )
        except asyncio.CancelledError:
            raise
        except ModelHTTPError as exc:
            error_type = (
                RetryableModelError
                if exc.status_code == 429 or exc.status_code >= 500
                else NonRetryableModelError
            )
            raise error_type(str(exc), events=(initial_event,)) from exc
        except (
            openai.APIConnectionError,
            openai.APITimeoutError,
            openai.RateLimitError,
            openai.InternalServerError,
        ) as exc:
            raise RetryableModelError(str(exc), events=(initial_event,)) from exc
        except UsageLimitExceeded as exc:
            raise NonRetryableModelError(str(exc), events=(initial_event,)) from exc
        except Exception as exc:
            raise NonRetryableModelError(
                f"PydanticAI executor failed: {exc}", events=(initial_event,)
            ) from exc

        messages = result.all_messages()
        events, reasoning = self._normalize_events(messages)
        usage = asdict(result.usage)
        usage["total_tokens"] = result.usage.total_tokens
        raw = to_jsonable_python(messages)
        raw_messages = tuple(raw) if isinstance(raw, list) else ()
        return ExecutorResult(
            assistant_text=str(result.output or ""),
            reasoning=tuple(reasoning),
            events=tuple(events),
            raw_messages=raw_messages,
            usage={
                str(key): int(value)
                for key, value in usage.items()
                if isinstance(value, (int, float))
            },
            model_request_count=int(result.usage.requests),
        )

    def _model(self, request: ExecutorRequest) -> Model:
        client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key or "local-study-key",
            timeout=request.timeout_seconds,
            max_retries=0,
        )
        return OpenAIChatModel(
            request.model_key,
            provider=OpenAIProvider(openai_client=client),
        )

    @staticmethod
    def _tool(definition: ToolDefinition, request: ExecutorRequest) -> Tool:
        async def invoke(context: RunContext[Any], **arguments: Any) -> dict[str, Any]:
            if request.cancellation.is_set():
                return {"ok": False, "error": "run cancelled"}
            call_id = context.tool_call_id or (
                f"pydantic_{definition.name}_"
                f"{len(getattr(request.tool_session, 'executions', [])) + 1}"
            )
            return await request.tool_session.execute(
                definition.name, arguments, call_id
            )

        return Tool.from_schema(
            invoke,
            name=definition.name,
            description=definition.description,
            json_schema=definition.parameters_json_schema,
            takes_ctx=True,
            sequential=True,
        )

    def _normalize_events(
        self, messages: list[ModelRequest | ModelResponse]
    ) -> tuple[list[tuple[RunEventType, dict[str, Any]]], list[str]]:
        events: list[tuple[RunEventType, dict[str, Any]]] = []
        reasoning: list[str] = []
        model_request_index = 0
        for message in messages:
            if isinstance(message, ModelRequest):
                tool_returns = [
                    part for part in message.parts if isinstance(part, ToolReturnPart)
                ]
                for part in tool_returns:
                    events.append(
                        (
                            RunEventType.TOOL_RESULT,
                            {
                                "call_id": part.tool_call_id,
                                "name": part.tool_name,
                                "succeeded": part.outcome == "success",
                                "result": to_jsonable_python(part.content),
                            },
                        )
                    )
                model_request_index += 1
                events.append(
                    (
                        RunEventType.MODEL_REQUEST,
                        {
                            "adapter": self.name,
                            "model_request_index": model_request_index,
                            "part_count": len(message.parts),
                        },
                    )
                )
                continue
            tool_calls = [
                part for part in message.parts if isinstance(part, ToolCallPart)
            ]
            thinking_parts = [
                part.content
                for part in message.parts
                if isinstance(part, ThinkingPart) and part.content.strip()
            ]
            reasoning.extend(thinking_parts)
            events.append(
                (
                    RunEventType.MODEL_RESPONSE,
                    {
                        "adapter": self.name,
                        "model_request_index": model_request_index,
                        "finish_reason": message.finish_reason,
                        "reasoning_length": sum(len(item) for item in thinking_parts),
                        "tool_call_count": len(tool_calls),
                    },
                )
            )
            for part in tool_calls:
                events.append(
                    (
                        RunEventType.TOOL_CALL,
                        {
                            "call_id": part.tool_call_id,
                            "name": part.tool_name,
                            "arguments": part.args_as_dict(),
                        },
                    )
                )
        return events, reasoning
