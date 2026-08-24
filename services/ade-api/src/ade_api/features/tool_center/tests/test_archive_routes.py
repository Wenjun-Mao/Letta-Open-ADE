from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import ade_api.platform.app as app_module
from ade_api.platform.app import create_app
from ade_api.platform.dependencies import (
    get_custom_tool_registry,
    get_letta_tool_service,
)


def _client(monkeypatch, *, registry: object, tool_service: object) -> TestClient:
    monkeypatch.setattr(
        app_module,
        "validate_capabilities_startup",
        lambda *_args: None,
    )
    app = create_app()
    app.dependency_overrides[get_custom_tool_registry] = lambda: registry
    app.dependency_overrides[get_letta_tool_service] = lambda: tool_service
    return TestClient(app)


def test_tool_archive_restore_and_purge_routes(monkeypatch) -> None:
    class _FakeCustomToolRegistry:
        def __init__(self) -> None:
            self.archived = False
            self.source_code = "def tool_impl():\n    return 'ok'\n"

        def get_tool(
            self, slug: str, include_source: bool = False
        ) -> dict[str, object]:
            return {
                "slug": slug,
                "tool_id": "tool-1",
                "name": "Tool One",
                "description": "Test tool",
                "tags": ["ade:managed"],
                "source_type": "python",
                "tool_type": "custom",
                "managed": True,
                "read_only": False,
                "archived": self.archived,
                "source_path": f"tools/{slug}.py",
                "source_code": self.source_code if include_source else None,
                "created_at": "2026-04-22T00:00:00+00:00",
                "last_updated_at": "2026-04-22T00:00:00+00:00",
                "updated_at": "2026-04-22T00:00:00+00:00",
                "archived_at": "2026-04-22T00:00:00+00:00" if self.archived else None,
            }

        def archive_tool(self, slug: str) -> dict[str, object]:
            self.archived = True
            return self.get_tool(slug, include_source=True)

        def restore_tool(
            self,
            *,
            slug: str,
            tool_id: str,
            name: str,
            description: str,
            tags: list[str],
            source_type: str,
            tool_type: str,
        ) -> dict[str, object]:
            self.archived = False
            record = self.get_tool(slug, include_source=True)
            record["tool_id"] = tool_id
            record["name"] = name
            record["description"] = description
            record["tags"] = tags
            record["source_type"] = source_type
            record["tool_type"] = tool_type
            return record

        def purge_tool(self, slug: str) -> None:
            self.archived = False

    deleted_tool_ids: list[str] = []
    created_tools: list[dict[str, object]] = []
    registry = _FakeCustomToolRegistry()

    tool_service = SimpleNamespace(
        delete_tool=lambda *, tool_id: deleted_tool_ids.append(tool_id),
        create_tool=lambda **kwargs: (
            created_tools.append(kwargs)
            or {
                "id": "tool-2",
                "name": "Restored Tool",
                "description": kwargs.get("description", ""),
                "tags": kwargs.get("tags", []),
                "source_type": kwargs.get("source_type", "python"),
                "tool_type": "custom",
            }
        ),
    )

    with _client(
        monkeypatch,
        registry=registry,
        tool_service=tool_service,
    ) as client:
        archive = client.post("/api/v2/tool-center/tools/demo_tool/archive")
        assert archive.status_code == 200
        assert archive.json()["archived"] is True
        assert deleted_tool_ids == ["tool-1"]

        restore = client.post("/api/v2/tool-center/tools/demo_tool/restore")
        assert restore.status_code == 200
        assert restore.json()["archived"] is False
        assert created_tools and created_tools[0]["source_code"] == registry.source_code

        archive_again = client.post("/api/v2/tool-center/tools/demo_tool/archive")
        assert archive_again.status_code == 200

        purge = client.delete("/api/v2/tool-center/tools/demo_tool/purge")
        assert purge.status_code == 200
        assert purge.json() == {"ok": True, "slug": "demo_tool", "kind": "custom_tool"}
