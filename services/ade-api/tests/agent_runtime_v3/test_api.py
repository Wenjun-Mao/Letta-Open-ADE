from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from ade_api.features.agent_runtime_v3 import flags
from ade_api.features.agent_runtime_v3 import worker_health
from ade_api.features.agent_runtime_v3.dependencies import (
    clear_agent_runtime_v3_service,
    get_agent_runtime_v3_health_service,
    get_agent_runtime_v3_service,
)
from ade_api.main import app
from ade_api.platform.auth import AdePrincipal, AdeRole, authenticate_ade_request


NOW = datetime(2026, 8, 29, tzinfo=UTC)


class _FakeService:
    health_ready = True

    async def get_health(self):
        return {
            "status": "ready" if self.health_ready else "not_ready",
            "database_ready": True,
            "worker_ready": self.health_ready,
            "compatible_worker_count": 1 if self.health_ready else 0,
            "matching_build_worker_count": 1 if self.health_ready else 0,
            "freshness_seconds": 45,
            "checked_at": NOW,
            "compatibility_fingerprint": "f" * 64,
            "source_revision": "test-revision",
            "source_dirty": False,
            "source_fingerprint": "s" * 64,
            "latest_heartbeat_at": NOW if self.health_ready else None,
        }

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


def test_runtime_health_is_200_only_when_a_fresh_worker_is_visible() -> None:
    service = _FakeService()
    app.dependency_overrides[authenticate_ade_request] = _principal
    app.dependency_overrides[get_agent_runtime_v3_health_service] = lambda: service
    try:
        ready = TestClient(app).get("/api/v3/worker-health")
        service.health_ready = False
        not_ready = TestClient(app).get("/api/v3/worker-health")
    finally:
        app.dependency_overrides.clear()

    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert not_ready.status_code == 503
    assert not_ready.json()["status"] == "not_ready"
    assert not_ready.json()["worker_ready"] is False


def test_disabled_runtime_health_returns_typed_not_ready_body(
    monkeypatch,
) -> None:
    settings = type(
        "Settings",
        (),
        {
            "agent_runtime_v3_enabled": False,
            "agent_runtime_v3_mode": "release",
            "agent_runtime_v3_worker_stale_seconds": 15.0,
            "database_url": None,
        },
    )()
    monkeypatch.setattr(worker_health, "get_settings", lambda: settings)
    monkeypatch.setenv("ADE_SOURCE_REVISION", "a" * 40)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "false")
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "b" * 64)
    clear_agent_runtime_v3_service()
    app.dependency_overrides[authenticate_ade_request] = _principal
    try:
        response = TestClient(app).get("/api/v3/worker-health")
    finally:
        app.dependency_overrides.clear()
        clear_agent_runtime_v3_service()

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database_ready": False,
        "worker_ready": False,
        "checked_at": response.json()["checked_at"],
        "freshness_seconds": 15.0,
        "compatible_worker_count": 0,
        "matching_build_worker_count": 0,
        "compatibility_fingerprint": response.json()["compatibility_fingerprint"],
        "source_revision": "a" * 40,
        "source_dirty": False,
        "source_fingerprint": "b" * 64,
        "latest_heartbeat_at": None,
        "failure_code": "runtime_disabled",
    }


def test_worker_health_openapi_documents_typed_not_ready_response() -> None:
    response_schema = app.openapi()["paths"]["/api/v3/worker-health"]["get"][
        "responses"
    ]["503"]["content"]["application/json"]["schema"]

    assert response_schema == {
        "$ref": "#/components/schemas/RuntimeWorkerHealthResponse"
    }
