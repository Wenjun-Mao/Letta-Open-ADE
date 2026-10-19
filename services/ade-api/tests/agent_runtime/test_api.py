from __future__ import annotations

from fastapi.testclient import TestClient

from ade_api.features.agent_runtime import flags
from ade_api.features.agent_runtime import worker_health
from ade_api.features.agent_runtime.dependencies import (
    clear_agent_runtime_service,
    get_agent_runtime_health_service,
    get_agent_runtime_service,
)
from ade_api.features.agent_runtime.router_transport import RouterRequestError
from ade_api.main import app
from ade_api.platform.auth import AdePrincipal, AdeRole, authenticate_ade_request


from .api_fakes import _FakeService


def _principal() -> AdePrincipal:
    return AdePrincipal(role=AdeRole.ADMIN, key_name="test")


def test_disabled_v3_returns_stable_feature_error(monkeypatch) -> None:
    app.dependency_overrides[authenticate_ade_request] = _principal
    monkeypatch.setattr(
        flags,
        "get_settings",
        lambda: type("Settings", (), {"agent_runtime_enabled": False})(),
    )
    try:
        response = TestClient(app).get("/api/v3/runs/run-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "agent_runtime_disabled"


def test_turn_acceptance_is_async_and_uses_backend_defaults() -> None:
    app.dependency_overrides[authenticate_ade_request] = _principal
    app.dependency_overrides[get_agent_runtime_service] = lambda: _FakeService()
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


def test_deferred_manual_memory_removal_has_no_public_route() -> None:
    path = (
        "/api/v3/agent-studio/subjects/"
        "00000000-0000-0000-0000-000000000013/memory-removals"
    )
    payload = {
        "idempotency_key": "remove-1",
        "expected_memory_generation": 2,
        "targets": [
            {
                "fact_id": "00000000-0000-0000-0000-000000000018",
                "expected_version": 1,
            }
        ],
    }
    app.dependency_overrides[get_agent_runtime_service] = lambda: _FakeService()
    try:
        app.dependency_overrides[authenticate_ade_request] = lambda: AdePrincipal(
            role=AdeRole.READER, key_name="reader"
        )
        denied = TestClient(app).post(path, json=payload)
        app.dependency_overrides[authenticate_ade_request] = _principal
        accepted = TestClient(app).post(path, json=payload)
    finally:
        app.dependency_overrides.clear()

    assert denied.status_code == accepted.status_code == 404


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
    app.dependency_overrides[get_agent_runtime_service] = lambda: _UnavailableService()
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
    app.dependency_overrides[get_agent_runtime_service] = lambda: _FakeService()
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


def test_evaluation_session_owns_chat_state_without_sql_only_purge() -> None:
    app.dependency_overrides[authenticate_ade_request] = _principal
    app.dependency_overrides[get_agent_runtime_service] = lambda: _FakeService()
    try:
        client = TestClient(app)
        created = client.post(
            "/api/v3/evaluation-sessions",
            json={
                "idempotency_key": "evaluation-session-1",
                "model_key": "dgx_vllm::qwen",
                "compaction_model_key": "dgx_vllm::qwen",
                "tool_names": ["search_memory", "get_weather"],
            },
        )
        state = client.get(
            "/api/v3/evaluation-sessions/"
            "00000000-0000-0000-0000-000000000024/state?message_limit=50"
        )
        purged = client.delete(
            "/api/v3/evaluation-sessions/00000000-0000-0000-0000-000000000024"
        )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["conversation"]["purpose"] == "evaluation"
    assert state.status_code == 200
    assert "memories" not in state.json()
    assert state.json()["conversation"]["messages"] == []
    assert purged.status_code == 404


def test_generic_resource_harness_routes_are_not_public() -> None:
    app.dependency_overrides[authenticate_ade_request] = _principal
    try:
        client = TestClient(app)
        responses = [
            client.post("/api/v3/agent-definitions", json={}),
            client.post("/api/v3/memory-subjects", json={}),
            client.post("/api/v3/conversations", json={}),
            client.get("/api/v3/conversations/conversation-1/state"),
        ]
    finally:
        app.dependency_overrides.clear()

    assert [response.status_code for response in responses] == [404, 404, 404, 404]


def test_run_response_exposes_the_controls_accepted_for_execution() -> None:
    app.dependency_overrides[authenticate_ade_request] = _principal
    app.dependency_overrides[get_agent_runtime_service] = lambda: _FakeService()
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
    app.dependency_overrides[get_agent_runtime_health_service] = lambda: service
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
            "agent_runtime_enabled": False,
            "agent_runtime_mode": "release",
            "agent_runtime_worker_stale_seconds": 15.0,
            "agent_runtime_workspace_key": "controlled-api-test",
            "hindsight_base_url": "http://controlled-native",
            "database_url": None,
        },
    )()
    monkeypatch.setattr(worker_health, "get_settings", lambda: settings)
    monkeypatch.setenv("ADE_SOURCE_REVISION", "a" * 40)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "false")
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "b" * 64)
    clear_agent_runtime_service()
    app.dependency_overrides[authenticate_ade_request] = _principal
    try:
        response = TestClient(app).get("/api/v3/worker-health")
    finally:
        app.dependency_overrides.clear()
        clear_agent_runtime_service()

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
    app.dependency_overrides[get_agent_runtime_service] = lambda: _FakeService()
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


def test_agent_studio_sql_only_reset_is_not_public_even_for_admin() -> None:
    service = _FakeService()
    app.dependency_overrides[get_agent_runtime_service] = lambda: service
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

    assert forbidden.status_code == accepted.status_code == 404
