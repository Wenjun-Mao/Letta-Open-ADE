from __future__ import annotations

from fastapi.testclient import TestClient

from agent_platform_api.main import app
from agent_platform_api.settings import clear_settings_cache


def _configure_auth(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_PLATFORM_AUTH_ENABLED", "true")
    monkeypatch.setenv("AGENT_PLATFORM_API_KEY", "admin-test-key")
    monkeypatch.setenv("AGENT_PLATFORM_OPERATOR_API_KEY", "operator-test-key")
    monkeypatch.setenv("AGENT_PLATFORM_READ_API_KEY", "reader-test-key")
    clear_settings_cache()


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


def test_health_is_public_when_authentication_is_enabled(monkeypatch) -> None:
    _configure_auth(monkeypatch)

    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_rejects_missing_and_invalid_credentials(monkeypatch) -> None:
    _configure_auth(monkeypatch)
    client = TestClient(app)

    missing = client.get("/api/v1/options?scenario=chat")
    invalid = client.get("/api/v1/options?scenario=chat", headers=_headers("wrong-key"))

    assert missing.status_code == 401
    assert invalid.status_code == 401


def test_api_fails_closed_when_enabled_without_keys(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_PLATFORM_AUTH_ENABLED", "true")
    monkeypatch.setenv("AGENT_PLATFORM_API_KEY", "")
    monkeypatch.setenv("AGENT_PLATFORM_OPERATOR_API_KEY", "")
    monkeypatch.setenv("AGENT_PLATFORM_READ_API_KEY", "")
    clear_settings_cache()

    response = TestClient(app).get("/api/v1/options?scenario=chat")

    assert response.status_code == 503


def test_reader_operator_and_admin_roles_are_ordered(monkeypatch) -> None:
    _configure_auth(monkeypatch)
    client = TestClient(app)

    reader_options = client.get(
        "/api/v1/platform/metadata/prompts-personas?scenario=chat",
        headers=_headers("reader-test-key"),
    )
    reader_chat = client.post(
        "/api/v1/chat",
        headers=_headers("reader-test-key"),
        json={"agent_id": "agent-test", "message": "hello"},
    )
    operator_admin_route = client.get(
        "/api/v1/platform/prompt-center/prompts?scenario=chat",
        headers=_headers("operator-test-key"),
    )
    admin_route = client.get(
        "/api/v1/platform/prompt-center/prompts?scenario=chat",
        headers=_headers("admin-test-key"),
    )

    assert reader_options.status_code == 200
    assert reader_chat.status_code == 403
    assert operator_admin_route.status_code == 403
    assert admin_route.status_code == 200


def test_raw_provider_diagnostics_require_admin_role(monkeypatch) -> None:
    _configure_auth(monkeypatch)

    response = TestClient(app).post(
        "/api/v1/commenting/generate",
        headers=_headers("operator-test-key"),
        json={
            "input": "diagnostic request",
            "prompt_key": "comment_v20260418",
            "persona_key": "comment_linxiaotang",
            "include_diagnostics": True,
        },
    )

    assert response.status_code == 403
