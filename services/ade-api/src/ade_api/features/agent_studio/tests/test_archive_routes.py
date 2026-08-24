from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import ade_api.platform.app as app_module
from ade_api.platform.app import create_app
from ade_api.platform.dependencies import (
    get_agent_lifecycle_registry,
    get_letta_agent_service,
    get_letta_client,
    get_prompt_persona_registry,
)
from ade_api.features.agent_studio import lifecycle_api


def _client(monkeypatch, **dependency_values: object) -> TestClient:
    monkeypatch.setattr(
        app_module,
        "validate_capabilities_startup",
        lambda *_args: None,
    )
    app = create_app()
    dependency_getters = {
        "client": get_letta_client,
        "lifecycle_registry": get_agent_lifecycle_registry,
        "agent_service": get_letta_agent_service,
        "prompt_registry": get_prompt_persona_registry,
    }

    def constant_dependency(value: object):
        def dependency() -> object:
            return value

        return dependency

    for name, value in dependency_values.items():
        app.dependency_overrides[dependency_getters[name]] = constant_dependency(value)
    return TestClient(app)


def test_agent_archive_restore_and_purge_routes(monkeypatch) -> None:
    class _FakeLifecycleRegistry:
        def __init__(self) -> None:
            self.records: dict[str, dict[str, object]] = {}

        def archive_agent(
            self, *, agent_id: str, name: str = "", model: str = ""
        ) -> dict[str, object]:
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

    monkeypatch.setattr(lifecycle_api, "ensure_ade_api_enabled", lambda: None)
    monkeypatch.setattr(
        lifecycle_api,
        "fetch_agent_or_404",
        lambda agent_id, _client: SimpleNamespace(
            id=agent_id,
            name="Archived Agent",
            model="openai-proxy/model",
        ),
    )
    monkeypatch.setattr(lifecycle_api, "is_not_found_error", lambda exc: False)

    with _client(
        monkeypatch,
        client=object(),
        lifecycle_registry=lifecycle_registry,
        agent_service=SimpleNamespace(
            delete_agent=lambda *, agent_id: deleted_ids.append(agent_id)
        ),
    ) as client:
        purge_before_archive = client.delete(
            "/api/v2/agent-studio/agents/agent-1/purge"
        )
        assert purge_before_archive.status_code == 400

        archive = client.post("/api/v2/agent-studio/agents/agent-1/archive")
        assert archive.status_code == 200
        assert archive.json()["archived"] is True
        assert lifecycle_registry.get_record("agent-1") is not None

        restore = client.post("/api/v2/agent-studio/agents/agent-1/restore")
        assert restore.status_code == 200, restore.text
        assert restore.json()["archived"] is False

        archive_again = client.post("/api/v2/agent-studio/agents/agent-1/archive")
        assert archive_again.status_code == 200

        purge = client.delete("/api/v2/agent-studio/agents/agent-1/purge")
        assert purge.status_code == 200
        assert purge.json() == {"ok": True, "id": "agent-1", "kind": "agent"}
        assert deleted_ids == ["agent-1"]

        restore_after_purge = client.post("/api/v2/agent-studio/agents/agent-1/restore")
        assert restore_after_purge.status_code == 400


def test_prompt_and_persona_archive_routes(monkeypatch) -> None:
    class _FakePromptPersonaRegistry:
        def archive_template(
            self, kind: str, key: str, scenario: str | None = None
        ) -> dict[str, object]:
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

        def restore_template(
            self, kind: str, key: str, scenario: str | None = None
        ) -> dict[str, object]:
            record = self.archive_template(kind, key, scenario)
            record["archived"] = False
            return record

        def purge_template(
            self, kind: str, key: str, scenario: str | None = None
        ) -> None:
            return None

    with _client(
        monkeypatch,
        prompt_registry=_FakePromptPersonaRegistry(),
    ) as client:
        prompt_archive = client.post(
            "/api/v2/prompt-center/prompts/chat_demo/archive?scenario=chat"
        )
        assert prompt_archive.status_code == 200
        assert prompt_archive.json()["archived"] is True

        prompt_restore = client.post(
            "/api/v2/prompt-center/prompts/chat_demo/restore?scenario=chat"
        )
        assert prompt_restore.status_code == 200
        assert prompt_restore.json()["archived"] is False

        prompt_purge = client.delete(
            "/api/v2/prompt-center/prompts/chat_demo/purge?scenario=chat"
        )
        assert prompt_purge.status_code == 200
        assert prompt_purge.json() == {"ok": True, "key": "chat_demo", "kind": "prompt"}

        persona_archive = client.post(
            "/api/v2/prompt-center/personas/chat_demo/archive?scenario=chat"
        )
        assert persona_archive.status_code == 200
        assert persona_archive.json()["archived"] is True

        persona_restore = client.post(
            "/api/v2/prompt-center/personas/chat_demo/restore?scenario=chat"
        )
        assert persona_restore.status_code == 200
        assert persona_restore.json()["archived"] is False

        persona_purge = client.delete(
            "/api/v2/prompt-center/personas/chat_demo/purge?scenario=chat"
        )
        assert persona_purge.status_code == 200
        assert persona_purge.json() == {
            "ok": True,
            "key": "chat_demo",
            "kind": "persona",
        }
