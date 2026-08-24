from __future__ import annotations

import pytest

from ade_api.features.tool_center.registry import CustomToolRegistry, ToolRegistryError


def test_custom_tool_registry_persists_source_through_archive_lifecycle(
    tmp_path,
) -> None:
    registry = CustomToolRegistry(tmp_path)
    created = registry.create_tool(
        slug="greet_user",
        tool_id="tool-1",
        name="Greet User",
        description="Returns a greeting.",
        source_code="def greet_user(name: str) -> str:\n    return f'Hello {name}'\n",
        tags=["ade:managed", "demo"],
    )

    assert created["source_code"].startswith("def greet_user")
    assert "source_code" not in registry.list_tools(include_source=False)[0]

    archived = registry.archive_tool("greet_user")
    assert archived["archived"] is True
    assert registry.list_tools() == []

    restored = registry.restore_tool(
        slug="greet_user",
        tool_id="tool-2",
        name="Greet User",
        description="Returns a greeting.",
        tags=["ade:managed", "demo"],
    )
    assert restored["tool_id"] == "tool-2"
    assert restored["source_code"] == created["source_code"]

    registry.archive_tool("greet_user")
    registry.purge_tool("greet_user")
    assert registry.list_tools(include_archived=True) == []


def test_custom_tool_registry_rejects_invalid_slug(tmp_path) -> None:
    registry = CustomToolRegistry(tmp_path)

    with pytest.raises(ToolRegistryError, match="Invalid slug"):
        registry.get_tool("Not Valid")
