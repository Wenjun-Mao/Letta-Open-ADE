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
from ade_api.features.agent_runtime_v3.router_transport import RouterRequestError
from ade_api.native_main import app
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

    async def get_agent_studio_options(self):
        return {
            "runtime": "ade_native_v3",
            "default_bundle_key": "ade_native_dgx_v1",
            "bundles": [
                {
                    "key": "ade_native_dgx_v1",
                    "name": "ADE Native DGX",
                    "model_key": "dgx_vllm::qwen",
                    "reviewer_model_key": "dgx_vllm::qwen",
                    "embedding_model_key": "dgx_embedding::qwen",
                    "prompt_key": "chat_v20260516",
                    "persona_key": "chat_linxiaotang",
                    "tool_names": ["search_memory"],
                    "memory_policy_version": "typed-user-facts-v1",
                    "qualification_state": "qualified",
                    "deployments": [],
                }
            ],
            "default_timeout_seconds": 180,
            "default_retry_count": 0,
            "max_retry_count": 5,
        }

    async def create_agent_studio_session(self, request):
        assert request.idempotency_key == "studio-session-1"
        return _agent_studio_session()

    async def list_agent_studio_sessions(self, **kwargs):
        assert kwargs == {"include_archived": False, "limit": 100, "offset": 0}
        return {"total": 1, "items": [_agent_studio_session()]}

    async def get_agent_studio_conversation_state(self, conversation_id, **kwargs):
        assert conversation_id == "00000000-0000-0000-0000-000000000014"
        assert kwargs == {"message_limit": 50, "before_sequence": None}
        return {
            **_agent_studio_session()["conversation"],
            "messages": [],
            "message_total": 0,
            "messages_truncated": False,
            "next_before_sequence": None,
            "summary": None,
        }

    async def reset_agent_studio(self, request):
        assert request.confirmation == "RESET ADE AGENT STUDIO"
        return {
            "receipt_id": "00000000-0000-0000-0000-000000000015",
            "idempotent_replay": False,
            "reset_generation": 2,
            "deleted_counts": {"conversations": 1},
            "reset_at": NOW,
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
            "timeout_seconds": 180,
            "retry_count": 0,
            "created_at": NOW,
        }


def _agent_studio_session():
    return {
        "session_id": "00000000-0000-0000-0000-000000000014",
        "idempotent_replay": False,
        "agent_definition": {
            "id": "00000000-0000-0000-0000-000000000012",
            "agent_definition_id": "00000000-0000-0000-0000-000000000011",
            "definition_key": "default_companion",
            "version": 1,
            "name": "Default companion",
            "prompt_key": "chat_v20260516",
            "prompt_sha256": "a" * 64,
            "persona_key": "chat_linxiaotang",
            "persona_sha256": "b" * 64,
            "tool_names": ["search_memory"],
            "memory_policy_version": "typed-user-facts-v1",
            "qualification_state": "qualified",
            "deployments": [],
            "archived_at": None,
            "created_at": NOW,
        },
        "memory_subject": {
            "id": "00000000-0000-0000-0000-000000000013",
            "external_key": "local-user",
            "display_name": "Local user",
            "version": 1,
            "archived_at": None,
            "created_at": NOW,
            "updated_at": NOW,
        },
        "conversation": {
            "id": "00000000-0000-0000-0000-000000000014",
            "agent_definition_id": "00000000-0000-0000-0000-000000000012",
            "memory_subject_id": "00000000-0000-0000-0000-000000000013",
            "title": "First conversation",
            "purpose": "agent_studio",
            "version": 1,
            "archived_at": None,
            "created_at": NOW,
        },
        "latest_run": None,
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


def test_router_catalog_transport_failure_returns_stable_not_ready_error() -> None:
    class _UnavailableService(_FakeService):
        async def accept_turn(self, conversation_id, request):
            del conversation_id, request
            raise RouterRequestError(
                "transport timeout",
                retryable=True,
                error_code="transport_readtimeout",
            )

    app.dependency_overrides[authenticate_ade_request] = _principal
    app.dependency_overrides[get_agent_runtime_v3_service] = lambda: (
        _UnavailableService()
    )
    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v3/conversations/conversation-1/turns",
            json={"content": "hello", "idempotency_key": "turn-1"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "model_router_unavailable",
        "message": "Model Router is not ready",
    }


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


def test_run_response_exposes_the_controls_accepted_for_execution() -> None:
    app.dependency_overrides[authenticate_ade_request] = _principal
    app.dependency_overrides[get_agent_runtime_v3_service] = lambda: _FakeService()
    try:
        response = TestClient(app).get("/api/v3/runs/run-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["timeout_seconds"] == 180
    assert response.json()["retry_count"] == 0


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


def test_agent_studio_api_exposes_qualified_options_and_persisted_sessions() -> None:
    app.dependency_overrides[authenticate_ade_request] = _principal
    app.dependency_overrides[get_agent_runtime_v3_service] = lambda: _FakeService()
    try:
        client = TestClient(app)
        options = client.get("/api/v3/agent-studio/options")
        created = client.post(
            "/api/v3/agent-studio/sessions",
            json={
                "idempotency_key": "studio-session-1",
                "title": "First conversation",
                "agent_definition_id": "00000000-0000-0000-0000-000000000012",
                "memory_subject_id": "00000000-0000-0000-0000-000000000013",
            },
        )
        sessions = client.get("/api/v3/agent-studio/sessions")
        state = client.get(
            "/api/v3/agent-studio/sessions/"
            "00000000-0000-0000-0000-000000000014/state?message_limit=50"
        )
    finally:
        app.dependency_overrides.clear()

    assert options.status_code == 200
    assert options.json()["bundles"][0]["qualification_state"] == "qualified"
    assert created.status_code == 201
    assert created.json()["conversation"]["purpose"] == "agent_studio"
    assert sessions.json()["total"] == 1
    assert state.json()["message_total"] == 0


def test_agent_studio_reset_requires_admin_and_returns_durable_receipt() -> None:
    service = _FakeService()
    app.dependency_overrides[get_agent_runtime_v3_service] = lambda: service
    app.dependency_overrides[authenticate_ade_request] = lambda: AdePrincipal(
        role=AdeRole.OPERATOR, key_name="operator-test"
    )
    try:
        client = TestClient(app)
        forbidden = client.post(
            "/api/v3/agent-studio/reset",
            json={
                "idempotency_key": "reset-1",
                "confirmation": "RESET ADE AGENT STUDIO",
            },
        )
        app.dependency_overrides[authenticate_ade_request] = _principal
        accepted = client.post(
            "/api/v3/agent-studio/reset",
            json={
                "idempotency_key": "reset-1",
                "confirmation": "RESET ADE AGENT STUDIO",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert forbidden.status_code == 403
    assert accepted.status_code == 200
    assert accepted.json()["reset_generation"] == 2
    assert accepted.json()["deleted_counts"] == {"conversations": 1}
