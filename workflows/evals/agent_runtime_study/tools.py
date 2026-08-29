from __future__ import annotations

import asyncio
from typing import Any

from .contracts import (
    ToolDefinition,
    ToolExecution,
)
from .memory import MemoryRetriever

MEMORY_SEARCH_TOOL = ToolDefinition(
    name="search_memory",
    description=(
        "Search older committed memory for the current subject. The subject is "
        "bound by the runtime and cannot be selected by model arguments."
    ),
    parameters_json_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    },
)

WEATHER_TOOL = ToolDefinition(
    name="get_weather",
    description="Return deterministic study weather for a named city.",
    parameters_json_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {"city": {"type": "string", "minLength": 1}},
        "required": ["city"],
    },
)

CURATED_TOOL_DEFINITIONS = (
    MEMORY_SEARCH_TOOL,
    WEATHER_TOOL,
)

_WEATHER_FIXTURES = {
    "toronto": {"condition": "clear", "temperature_c": 21},
    "beijing": {"condition": "partly cloudy", "temperature_c": 26},
    "北京": {"condition": "partly cloudy", "temperature_c": 26},
    "多伦多": {"condition": "clear", "temperature_c": 21},
}


class TurnToolSession:
    """Subject-bound, attempt-local access to curated conversational tools."""

    def __init__(
        self,
        *,
        subject_id: str,
        memory_retriever: MemoryRetriever,
        search_limit: int,
        include_episodes: bool,
    ) -> None:
        self.subject_id = subject_id
        self.memory_retriever = memory_retriever
        self.search_limit = search_limit
        self.include_episodes = include_episodes
        self.executions: list[ToolExecution] = []

    async def execute(
        self, name: str, arguments: dict[str, Any], call_id: str
    ) -> dict[str, Any]:
        try:
            if "subject_id" in arguments or "memory_subject_id" in arguments:
                raise ValueError(
                    "subject selection is forbidden in model-controlled arguments"
                )
            if name == MEMORY_SEARCH_TOOL.name:
                result = await self._search(arguments)
            elif name == WEATHER_TOOL.name:
                result = self._weather(arguments)
            else:
                raise ValueError(f"Unknown curated tool: {name}")
            succeeded = bool(result.get("ok", True))
        except Exception as exc:
            result = {
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            succeeded = False
        self.executions.append(
            ToolExecution(
                call_id=call_id,
                name=name,
                arguments=dict(arguments),
                result=result,
                succeeded=succeeded,
            )
        )
        return result

    async def _search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        requested_limit = int(arguments.get("limit") or self.search_limit)
        limit = max(1, min(self.search_limit, requested_limit))
        facts = await asyncio.to_thread(
            self.memory_retriever.search_facts,
            self.subject_id,
            query,
            limit=limit,
            minimum_score=None,
        )
        episodes = (
            await asyncio.to_thread(
                self.memory_retriever.search_episodes,
                self.subject_id,
                query,
                limit=limit,
                minimum_score=None,
            )
            if self.include_episodes
            else ()
        )
        return {
            "ok": True,
            "facts": [
                {
                    "id": fact.id,
                    "key": fact.key,
                    "value": fact.value,
                    "version": fact.version,
                }
                for fact in facts
            ],
            "episodes": [
                {"id": episode.id, "content": episode.content} for episode in episodes
            ],
        }

    @staticmethod
    def _weather(arguments: dict[str, Any]) -> dict[str, Any]:
        city = str(arguments.get("city") or "").strip()
        if not city:
            raise ValueError("city is required")
        if city.casefold() in {"fail_city", "failure", "故障城市"}:
            raise RuntimeError("deterministic weather provider failure")
        weather = _WEATHER_FIXTURES.get(city.casefold()) or {
            "condition": "unknown",
            "temperature_c": None,
        }
        return {"ok": True, "city": city, **weather}


def curated_tools(names: tuple[str, ...]) -> tuple[ToolDefinition, ...]:
    allowed = {definition.name: definition for definition in CURATED_TOOL_DEFINITIONS}
    unknown = sorted(set(names) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown curated tool definitions: {unknown}")
    return tuple(allowed[name] for name in names)
