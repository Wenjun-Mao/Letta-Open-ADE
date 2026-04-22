from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import agent_platform_api.app as app_module
from agent_platform_api.app import create_app
from agent_platform_api.routers import agents, prompt_center, tool_center


def _client(monkeypatch) -> TestClient:
    monkeypatch.setattr(app_module, "validate_platform_capabilities_startup", lambda: None)
    return TestClient(create_app())


def test_agent_archive_restore_and_purge_routes(monkeypatch) -> None:
    class _FakeLifecycleRegistry:
        def __init__(self) -> None:
            self.records: dict[str, dict[str, object]] = {}

        def archive_agent(self, *, agent_id: str, name: str = "", model: str = "") -> dict[str, object]:
            record = {
                "id": agent_id,
                "name": name,
                "model": model,
                "archived": True,
                "archived_at": "2026-04-22T00:00:00+00:00",
                "updated_at": "2026-04-22T00:00:00+00:00",
            }
            self.records[agent_id] = record
            return record

        def get_record(self, agent_id: str) -> dict[str, object] | None:
            return self.records.get(agent_id)

        def restore_agent(self, agent_id: str) -> dict[str, object]:
            record = dict(self.records[agent_id])
            record["archived"] = False
            record["archived_at"] = None
            record["updated_at"] = "2026-04-22T00:05:00+00:00"
            self.records[agent_id] = record
            return record

        def purge_agent(self, agent_id: str) -> None:
            self.records.pop(agent_id, None)

    deleted_ids: list[str] = []
    lifecycle_registry = _FakeLifecycleRegistry()

    monkeypatch.setattr(agents, "ensure_platform_api_enabled", lambda: None)
    monkeypatch.setattr(
        agents,
        "fetch_agent_or_404",
        lambda agent_id: SimpleNamespace(id=agent_id, name="Archived Agent", model="openai-proxy/model"),
    )
    monkeypatch.setattr(agents, "agent_lifecycle_registry", lifecycle_registry)
    monkeypatch.setattr(
        agents,
        "agent_platform",
        SimpleNamespace(delete_agent=lambda *, agent_id: deleted_ids.append(agent_id)),
    )
    monkeypatch.setattr(agents, "is_not_found_error", lambda exc: False)

    with _client(monkeypatch) as client:
        purge_before_archive = client.delete("/api/v1/platform/agents/agent-1/purge")
        assert purge_before_archive.status_code == 400

        archive = client.post("/api/v1/platform/agents/agent-1/archive")
        assert archive.status_code == 200
        assert archive.json()["archived"] is True

        restore = client.post("/api/v1/platform/agents/agent-1/restore")
        assert restore.status_code == 200
        assert restore.json()["archived"] is False

        archive_again = client.post("/api/v1/platform/agents/agent-1/archive")
        assert archive_again.status_code == 200

        purge = client.delete("/api/v1/platform/agents/agent-1/purge")
        assert purge.status_code == 200
        assert purge.json() == {"ok": True, "id": "agent-1", "kind": "agent"}
        assert deleted_ids == ["agent-1"]

        restore_after_purge = client.post("/api/v1/platform/agents/agent-1/restore")
        assert restore_after_purge.status_code == 400


def test_prompt_and_persona_archive_routes(monkeypatch) -> None:
    class _FakePromptPersonaRegistry:
        def archive_template(self, kind: str, key: str, scenario: str | None = None) -> dict[str, object]:
            return {
                "kind": kind,
                "scenario": scenario or "chat",
                "key": key,
                "label": key.title(),
                "description": "",
                "content": f"{kind} content",
                "preview": f"{kind} preview",
                "length": 12,
                "archived": True,
                "source_path": f"prompts/{kind}/{key}.py",
                "updated_at": "2026-04-22T00:00:00+00:00",
            }

        def restore_template(self, kind: str, key: str, scenario: str | None = None) -> dict[str, object]:
            record = self.archive_template(kind, key, scenario)
            record["archived"] = False
            return record

        def purge_template(self, kind: str, key: str, scenario: str | None = None) -> None:
            return None

    invalidate_calls: list[str] = []

    monkeypatch.setattr(prompt_center, "ensure_platform_api_enabled", lambda: None)
    monkeypatch.setattr(prompt_center, "prompt_persona_registry", _FakePromptPersonaRegistry())
    monkeypatch.setattr(prompt_center, "invalidate_options_cache", lambda: invalidate_calls.append("called"))

    with _client(monkeypatch) as client:
        prompt_archive = client.post("/api/v1/platform/prompt-center/prompts/chat_demo/archive?scenario=chat")
        assert prompt_archive.status_code == 200
        assert prompt_archive.json()["archived"] is True

        prompt_restore = client.post("/api/v1/platform/prompt-center/prompts/chat_demo/restore?scenario=chat")
        assert prompt_restore.status_code == 200
        assert prompt_restore.json()["archived"] is False

        prompt_purge = client.delete("/api/v1/platform/prompt-center/prompts/chat_demo/purge?scenario=chat")
        assert prompt_purge.status_code == 200
        assert prompt_purge.json() == {"ok": True, "key": "chat_demo", "kind": "prompt"}

        persona_archive = client.post("/api/v1/platform/prompt-center/personas/chat_demo/archive?scenario=chat")
        assert persona_archive.status_code == 200
        assert persona_archive.json()["archived"] is True

        persona_restore = client.post("/api/v1/platform/prompt-center/personas/chat_demo/restore?scenario=chat")
        assert persona_restore.status_code == 200
        assert persona_restore.json()["archived"] is False

        persona_purge = client.delete("/api/v1/platform/prompt-center/personas/chat_demo/purge?scenario=chat")
        assert persona_purge.status_code == 200
        assert persona_purge.json() == {"ok": True, "key": "chat_demo", "kind": "persona"}

    assert len(invalidate_calls) == 6


def test_tool_archive_restore_and_purge_routes(monkeypatch) -> None:
    class _FakeCustomToolRegistry:
        def __init__(self) -> None:
            self.archived = False
            self.source_code = "def tool_impl():\n    return 'ok'\n"

        def get_tool(self, slug: str, include_source: bool = False) -> dict[str, object]:
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

    monkeypatch.setattr(tool_center, "ensure_platform_api_enabled", lambda: None)
    monkeypatch.setattr(tool_center, "custom_tool_registry", registry)
    monkeypatch.setattr(
        tool_center,
        "agent_platform",
        SimpleNamespace(
            delete_tool=lambda *, tool_id: deleted_tool_ids.append(tool_id),
            create_tool=lambda **kwargs: created_tools.append(kwargs) or {
                "id": "tool-2",
                "name": "Restored Tool",
                "description": kwargs.get("description", ""),
                "tags": kwargs.get("tags", []),
                "source_type": kwargs.get("source_type", "python"),
                "tool_type": "custom",
            },
        ),
    )

    with _client(monkeypatch) as client:
        archive = client.post("/api/v1/platform/tool-center/tools/demo_tool/archive")
        assert archive.status_code == 200
        assert archive.json()["archived"] is True
        assert deleted_tool_ids == ["tool-1"]

        restore = client.post("/api/v1/platform/tool-center/tools/demo_tool/restore")
        assert restore.status_code == 200
        assert restore.json()["archived"] is False
        assert created_tools and created_tools[0]["source_code"] == registry.source_code

        archive_again = client.post("/api/v1/platform/tool-center/tools/demo_tool/archive")
        assert archive_again.status_code == 200

        purge = client.delete("/api/v1/platform/tool-center/tools/demo_tool/purge")
        assert purge.status_code == 200
        assert purge.json() == {"ok": True, "slug": "demo_tool", "kind": "custom_tool"}
