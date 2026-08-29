from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from ade_api.features.agent_runtime_v3 import flags
from ade_api.features.agent_runtime_v3.dependencies import get_agent_runtime_v3_service
from ade_api.main import app
from ade_api.platform.auth import AdePrincipal, AdeRole, authenticate_ade_request


NOW = datetime(2026, 8, 29, tzinfo=UTC)


class _FakeService:
    async def accept_turn(self, conversation_id, request):
        assert request.timeout_seconds == 180
        assert request.retry_count == 0
        return {
            "run_id": "00000000-0000-0000-0000-000000000004",
            "status": "pending",
            "events_url": "/api/v3/runs/00000000-0000-0000-0000-000000000004/events",
            "idempotent_replay": False,
        }

    async def get_run(self, run_id):
        return {
            "id": run_id,
            "conversation_id": "00000000-0000-0000-0000-000000000003",
            "status": "pending",
            "qualification_state": "unqualified",
            "attempt_count": 0,
            "created_at": NOW,
        }


def _principal() -> AdePrincipal:
    return AdePrincipal(role=AdeRole.ADMIN, key_name="test")


def test_disabled_v3_returns_stable_feature_error(monkeypatch) -> None:
    app.dependency_overrides[authenticate_ade_request] = _principal
    monkeypatch.setattr(
        flags,
        "get_settings",
        lambda: type("Settings", (), {"agent_runtime_v3_enabled": False})(),
    )
    try:
        response = TestClient(app).get("/api/v3/runs/run-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "agent_runtime_v3_disabled"


def test_turn_acceptance_is_async_and_uses_backend_defaults() -> None:
    app.dependency_overrides[authenticate_ade_request] = _principal
    app.dependency_overrides[get_agent_runtime_v3_service] = lambda: _FakeService()
    try:
        response = TestClient(app).post(
            "/api/v3/conversations/00000000-0000-0000-0000-000000000003/turns",
            json={"content": "hello", "idempotency_key": "turn-1"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    assert response.json()["idempotent_replay"] is False


def test_turn_rejects_model_and_subject_overrides() -> None:
    app.dependency_overrides[authenticate_ade_request] = _principal
    app.dependency_overrides[get_agent_runtime_v3_service] = lambda: _FakeService()
    try:
        response = TestClient(app).post(
            "/api/v3/conversations/conversation-1/turns",
            json={
                "content": "hello",
                "idempotency_key": "turn-1",
                "model_key": "source::override",
                "memory_subject_id": "subject-2",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
