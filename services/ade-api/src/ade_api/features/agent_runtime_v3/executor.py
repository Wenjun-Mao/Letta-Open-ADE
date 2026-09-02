from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Collection, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from .compaction import (
    COMPACTION_RESPONSE_SCHEMA,
    COMPACTION_SYSTEM,
    CompactionPlan,
    ModelCompaction,
    compaction_content_sha256,
    compaction_input_sha256,
    compaction_model_input_json,
    compaction_policy_sha256,
    compaction_prompt_sha256,
    parse_compaction_response,
)
from .errors import RuntimeValidationError
from .provider_tracing import safe_provider_request_id
from .router_transport import RouterTransport
from .tool_policy import TOOL_USE_POLICY, ToolRequirement


SEARCH_MEMORY_TOOL = {
    "type": "function",
    "function": {
        "name": "search_memory",
        "description": (
            "Search older committed facts for the current memory subject. Call this "
            "for every explicit deep-memory search request; do not invent results."
        ),
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


_WEATHER_FIXTURES = {
    "toronto": {"condition": "clear", "temperature_c": 21},
    "beijing": {"condition": "partly cloudy", "temperature_c": 26},
    "北京": {"condition": "partly cloudy", "temperature_c": 26},
    "多伦多": {"condition": "clear", "temperature_c": 21},
}
_WEATHER_FAILURE_FIXTURES = frozenset({"fail_city"})
_WEATHER_CITY_ENUM = (
    "Toronto",
    "toronto",
    "Beijing",
    "beijing",
    "北京",
    "多伦多",
    "FAIL_CITY",
    "fail_city",
)


WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "Return deterministic fixture weather for one supported city identifier. "
            "Call this for every explicit weather lookup and copy one exact identifier "
            "from the schema; do not abbreviate a city or invent a result."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "city": {
                    "type": "string",
                    "enum": list(_WEATHER_CITY_ENUM),
                    "description": "Exact supported fixture city identifier.",
                }
            },
            "required": ["city"],
        },
    },
}


class SearchMemoryHandler(Protocol):
    async def __call__(self, query: str, limit: int) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class ToolResult:
    arguments: dict[str, Any]
    content: dict[str, Any]
    result_count: int = 0
    succeeded: bool = True
    error_type: str | None = None


ToolHandler = Callable[[dict[str, Any]], Awaitable[ToolResult]]
ArgumentValidator = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class CuratedTool:
    definition: dict[str, Any]
    validate_arguments: ArgumentValidator
    handler: ToolHandler

    @property
    def name(self) -> str:
        return str(self.definition["function"]["name"])


@dataclass(frozen=True)
class ExecutorResult:
    assistant_text: str
    usage: dict[str, int]
    model_request_count: int
    tool_events: list[dict[str, Any]]
    finish_reason: str
    provider_request_ids: list[str | None]
    tool_requirement: ToolRequirement | None = None
    tool_requirement_satisfied: bool = False


def curated_tools(
    names: Collection[str],
    *,
    search_memory: SearchMemoryHandler | None = None,
) -> dict[str, CuratedTool]:
    """Construct the exact allow-list for one bound conversation execution."""

    requested = tuple(str(name) for name in names)
    if len(requested) != len(set(requested)):
        raise RuntimeValidationError(
            "Conversation tool names must not contain duplicates",
            detail_code="curated_tool_registry_invalid",
        )
    available: dict[str, CuratedTool] = {"get_weather": _weather_tool()}
    if search_memory is not None:
        available["search_memory"] = _search_memory_tool(search_memory)
    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise RuntimeValidationError(
            f"Unknown or unavailable curated tools: {unknown}",
            detail_code="curated_tool_registry_invalid",
        )
    return {name: available[name] for name in requested}


class ConversationExecutor:
    def __init__(self, transport: RouterTransport) -> None:
        self.transport = transport

    async def execute(
        self,
        *,
        model_key: str,
        messages: list[dict[str, Any]],
        timeout_seconds: float,
        max_output_tokens: int,
        tools: Mapping[str, CuratedTool] | None = None,
        tool_requirement: ToolRequirement | None = None,
        max_model_requests: int = 6,
        # Kept for focused executor tests and study adapters. Product execution
        # supplies ``tools`` and therefore never selects behavior by a boolean.
        search_memory: SearchMemoryHandler | None = None,
        enable_search_memory: bool = True,
    ) -> ExecutorResult:
        enabled_tools = (
            dict(tools)
            if tools is not None
            else curated_tools(
                ("search_memory",) if enable_search_memory else (),
                search_memory=search_memory,
            )
        )
        _validate_registry(enabled_tools)
        _validate_tool_requirement(tool_requirement, enabled_tools)
        working_messages = (
            _with_tool_policy(messages)
            if enabled_tools
            else [dict(message) for message in messages]
        )
        total_usage: dict[str, int] = {}
        tool_events: list[dict[str, Any]] = []
        request_ids: list[str | None] = []
        requirement_satisfied = False
        for request_number in range(1, max_model_requests + 1):
            payload: dict[str, Any] = {
                "model": model_key,
                "messages": working_messages,
                "max_tokens": max_output_tokens,
                "stream": False,
            }
            if enabled_tools:
                payload.update(
                    {
                        "tools": [tool.definition for tool in enabled_tools.values()],
                        "tool_choice": (
                            tool_requirement.tool_choice()
                            if tool_requirement is not None
                            and not requirement_satisfied
                            else "auto"
                        ),
                    }
                )
            response = await self.transport.chat_completion(
                payload, timeout_seconds=timeout_seconds
            )
            _merge_usage(total_usage, response.get("usage"))
            request_id = safe_provider_request_id(response.get("id"))
            request_ids.append(request_id)
            message, finish_reason = _first_choice(response)
            tool_calls = message.get("tool_calls")
            if isinstance(tool_calls, list) and tool_calls:
                if not enabled_tools:
                    raise RuntimeValidationError(
                        "Conversation model called a tool that is not enabled",
                        detail_code="conversation_tool_unexpected",
                    )
                parsed_calls = [
                    _parse_tool_call(raw_call, enabled_tools) for raw_call in tool_calls
                ]
                if tool_requirement is not None and not requirement_satisfied:
                    if (
                        len(parsed_calls) != 1
                        or parsed_calls[0][1] != tool_requirement.tool_name
                    ):
                        raise RuntimeValidationError(
                            "Conversation model did not call the required curated tool",
                            detail_code="conversation_required_tool_mismatch",
                        )
                working_messages.append(message)
                for call_id, name, arguments in parsed_calls:
                    result = await _execute_tool(enabled_tools[name], arguments)
                    tool_events.append(
                        {
                            "request_number": request_number,
                            "call_id": call_id,
                            "name": name,
                            "arguments": result.arguments,
                            "result_count": result.result_count,
                            "succeeded": result.succeeded,
                            "error_type": result.error_type,
                        }
                    )
                    if (
                        tool_requirement is not None
                        and name == tool_requirement.tool_name
                    ):
                        requirement_satisfied = True
                    working_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": name,
                            "content": json.dumps(
                                result.content, ensure_ascii=False, default=str
                            ),
                        }
                    )
                continue
            if tool_requirement is not None and not requirement_satisfied:
                raise RuntimeValidationError(
                    "Conversation model returned final text before the required tool call",
                    detail_code="conversation_required_tool_missing",
                )
            content = str(message.get("content", "") or "").strip()
            if not content:
                raise RuntimeValidationError(
                    "Conversation model returned neither dialogue nor a tool call",
                    detail_code="conversation_output_empty",
                )
            return ExecutorResult(
                assistant_text=content,
                usage=total_usage,
                model_request_count=request_number,
                tool_events=tool_events,
                finish_reason=finish_reason,
                provider_request_ids=request_ids,
                tool_requirement=tool_requirement,
                tool_requirement_satisfied=requirement_satisfied,
            )
        raise RuntimeValidationError(
            "Conversation model exceeded its tool-step budget",
            detail_code="conversation_tool_step_budget_exceeded",
        )

    async def compact(
        self,
        *,
        model_key: str,
        model_fingerprint: str,
        plan: CompactionPlan,
        timeout_seconds: float,
        max_output_tokens: int,
        summary_token_budget: int,
    ) -> ModelCompaction:
        response = await self.transport.chat_completion(
            {
                "model": model_key,
                "messages": [
                    {"role": "system", "content": COMPACTION_SYSTEM},
                    {
                        "role": "user",
                        "content": compaction_model_input_json(plan),
                    },
                ],
                "max_tokens": max(256, min(max_output_tokens, 1024)),
                "stream": False,
                "temperature": 0,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "ade_conversation_compaction",
                        "strict": True,
                        "schema": COMPACTION_RESPONSE_SCHEMA,
                    },
                },
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout_seconds=timeout_seconds,
        )
        message, _ = _first_choice(response)
        content = parse_compaction_response(
            str(message.get("content", "") or "").strip(),
            summary_token_budget=summary_token_budget,
        )
        usage: dict[str, int] = {}
        _merge_usage(usage, response.get("usage"))
        provider_request_id = safe_provider_request_id(response.get("id"))
        return ModelCompaction(
            plan=plan,
            content=content,
            model_key=model_key,
            model_fingerprint=model_fingerprint,
            provider_request_id=provider_request_id,
            content_sha256=compaction_content_sha256(content),
            prompt_sha256=compaction_prompt_sha256(),
            input_sha256=compaction_input_sha256(plan),
            policy_sha256=compaction_policy_sha256(),
            usage=usage,
        )


def _search_memory_tool(search_memory: SearchMemoryHandler) -> CuratedTool:
    async def handler(arguments: dict[str, Any]) -> ToolResult:
        facts = await search_memory(arguments["query"], arguments["limit"])
        return ToolResult(
            arguments=arguments,
            content={"ok": True, "facts": facts},
            result_count=len(facts),
        )

    return CuratedTool(
        definition=SEARCH_MEMORY_TOOL,
        validate_arguments=_validate_search_memory_arguments,
        handler=handler,
    )


def _weather_tool() -> CuratedTool:
    async def handler(arguments: dict[str, Any]) -> ToolResult:
        city = arguments["city"]
        normalized_city = city.casefold()
        if normalized_city in _WEATHER_FAILURE_FIXTURES:
            raise RuntimeError("deterministic weather provider failure")
        weather = _WEATHER_FIXTURES[normalized_city]
        return ToolResult(
            arguments={"city": city},
            content={"ok": True, "city": city, **weather},
        )

    return CuratedTool(
        definition=WEATHER_TOOL,
        validate_arguments=_validate_weather_arguments,
        handler=handler,
    )


async def _execute_tool(tool: CuratedTool, arguments: dict[str, Any]) -> ToolResult:
    try:
        validated = tool.validate_arguments(arguments)
    except (TypeError, ValueError) as exc:
        raise RuntimeValidationError(
            f"{tool.name} arguments failed closed validation: {exc}",
            detail_code="curated_tool_arguments_invalid",
        ) from exc
    try:
        return await tool.handler(validated)
    except Exception as exc:
        return ToolResult(
            arguments=validated,
            content={
                "ok": False,
                "error_type": "provider_failure",
                "error": f"{tool.name} provider is unavailable",
            },
            succeeded=False,
            error_type=type(exc).__name__,
        )


def _validate_search_memory_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    unknown = set(arguments) - {"query", "limit"}
    if unknown:
        raise ValueError(f"unexpected fields: {sorted(unknown)}")
    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    raw_limit = arguments.get("limit", 8)
    if isinstance(raw_limit, bool) or not isinstance(raw_limit, int):
        raise ValueError("limit must be an integer")
    if not 1 <= raw_limit <= 20:
        raise ValueError("limit must be between 1 and 20")
    return {"query": query.strip(), "limit": raw_limit}


def _validate_weather_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    unknown = set(arguments) - {"city"}
    if unknown:
        raise ValueError(f"unexpected fields: {sorted(unknown)}")
    city = arguments.get("city")
    if not isinstance(city, str) or not city.strip():
        raise ValueError("city must be a non-empty string")
    city = city.strip()
    if (
        city.casefold() not in _WEATHER_FIXTURES
        and city.casefold() not in _WEATHER_FAILURE_FIXTURES
    ):
        raise ValueError("city must be a supported deterministic weather fixture")
    return {"city": city}


def _validate_registry(tools: Mapping[str, CuratedTool]) -> None:
    for name, tool in tools.items():
        if name != tool.name:
            raise RuntimeValidationError(
                "Curated tool registry key does not match tool schema",
                detail_code="curated_tool_registry_invalid",
            )


def _validate_tool_requirement(
    requirement: ToolRequirement | None, tools: Mapping[str, CuratedTool]
) -> None:
    if requirement is not None and requirement.tool_name not in tools:
        raise RuntimeValidationError(
            "Required curated tool is not enabled for this conversation",
            detail_code="curated_tool_requirement_invalid",
        )


def _with_tool_policy(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    working = [dict(message) for message in messages]
    if any(
        message.get("role") == "system"
        and TOOL_USE_POLICY in str(message.get("content") or "")
        for message in working
    ):
        return working
    if working and working[0].get("role") == "system":
        working[0]["content"] = (
            f"{str(working[0].get('content') or '').rstrip()}\n\n{TOOL_USE_POLICY}"
        )
    else:
        working.insert(0, {"role": "system", "content": TOOL_USE_POLICY})
    return working


def _first_choice(response: dict[str, Any]) -> tuple[dict[str, Any], str]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise RuntimeValidationError(
            "Model response did not contain a choice",
            detail_code="model_response_choice_missing",
        )
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        raise RuntimeValidationError(
            "Model response choice did not contain a message",
            detail_code="model_response_message_missing",
        )
    return dict(message), str(choice.get("finish_reason", "") or "")


def _parse_tool_call(
    raw_call: object, enabled_tools: Mapping[str, CuratedTool]
) -> tuple[str, str, dict[str, Any]]:
    if not isinstance(raw_call, dict):
        raise RuntimeValidationError(
            "Tool call must be an object",
            detail_code="conversation_tool_call_malformed",
        )
    call_id = str(raw_call.get("id", "") or "").strip()
    function = raw_call.get("function")
    if not call_id or not isinstance(function, dict):
        raise RuntimeValidationError(
            "Tool call requires id and function",
            detail_code="conversation_tool_call_malformed",
        )
    name = str(function.get("name", "") or "").strip()
    if name not in enabled_tools:
        raise RuntimeValidationError(
            f"Tool '{name}' is not enabled for this conversation",
            detail_code="conversation_tool_not_enabled",
        )
    raw_arguments = function.get("arguments", "{}")
    try:
        arguments = (
            json.loads(raw_arguments)
            if isinstance(raw_arguments, str)
            else raw_arguments
        )
    except json.JSONDecodeError as exc:
        raise RuntimeValidationError(
            f"{name} arguments are invalid JSON",
            detail_code="conversation_tool_arguments_invalid_json",
        ) from exc
    if not isinstance(arguments, dict):
        raise RuntimeValidationError(
            f"{name} arguments must be an object",
            detail_code="conversation_tool_arguments_not_object",
        )
    return call_id, name, arguments


def _merge_usage(total: dict[str, int], raw_usage: object) -> None:
    if not isinstance(raw_usage, dict):
        return
    for key, value in raw_usage.items():
        if isinstance(value, int) and not isinstance(value, bool):
            total[str(key)] = total.get(str(key), 0) + value
