"""Deterministic tool fixtures available only to evaluation sessions."""

from __future__ import annotations

from typing import Any

from .executor import CuratedTool, ToolResult


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
            "When calling it, copy one exact identifier from the schema; do not "
            "abbreviate a city or invent a result."
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


def evaluation_tool_registry() -> dict[str, CuratedTool]:
    return {"get_weather": _weather_tool()}


def _weather_tool() -> CuratedTool:
    async def handler(arguments: dict[str, Any]) -> ToolResult:
        city = arguments["city"]
        normalized_city = city.casefold()
        if normalized_city in _WEATHER_FAILURE_FIXTURES:
            raise RuntimeError("deterministic weather provider failure")
        return ToolResult(
            arguments={"city": city},
            content={"ok": True, "city": city, **_WEATHER_FIXTURES[normalized_city]},
        )

    return CuratedTool(
        definition=WEATHER_TOOL,
        validate_arguments=_validate_weather_arguments,
        handler=handler,
    )


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
