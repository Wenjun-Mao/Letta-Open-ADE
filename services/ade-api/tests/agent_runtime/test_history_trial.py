from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import ade_api.platform.app as app_module
import ade_api.platform.auth as auth_module
from ade_api.features.agent_runtime.agent_studio_sessions import PurposeSessionService
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.definition_service import DefinitionService
from ade_api.features.agent_runtime.history_trial import (
    HistoryTrialDefinitions,
    HistoryTrialService,
    HistoryTrialSessionService,
    TRIAL_DEEPSEEK_FINGERPRINT,
    TRIAL_QWEN_FINGERPRINT,
    require_trial_definition,
    trial_definition_request,
)
from ade_api.features.agent_runtime.natural_context import HISTORY_PROBE_POLICY
from ade_api.platform.settings import AdeApiSettings


def _prepared_definition() -> dict:
    request = trial_definition_request()
    return {
        **request.model_dump(),
        "memory_policy_version": "typed-user-facts-v2",
        "deployment_snapshot": [
            {
                "role": role,
                "route_alias": request.embedding_model_key if role == "retriever" else request.model_key,
                "fingerprint": (
                    TRIAL_QWEN_FINGERPRINT if role == "retriever" else TRIAL_DEEPSEEK_FINGERPRINT
                ),
                "fingerprint_payload": {
                    "context_settings": {
                        "total_tokens": 16384,
                        "max_output_tokens": 4096,
                        "max_model_requests": 6,
                        "reviewer_repair_count": 0,
                    }
                },
            }
            for role in ("conversation", "reviewer", "retriever")
        ],
    }


def test_trial_routes_are_off_by_default_and_require_development_auth(monkeypatch) -> None:
    settings = AdeApiSettings(
        _env_file=None,
        auth_enabled=True,
        reader_key="reader-test",
        operator_key="operator-test",
        agent_runtime_enabled=True,
        agent_runtime_mode="development",
    )
    monkeypatch.setattr(app_module, "get_settings", lambda: settings)
    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)
    assert not any(
        route.path.startswith("/api/v3/history-trial")
        for route in app_module.create_app().routes
    )
    settings.history_trial_enabled = True
    app = app_module.create_app()
    paths = {route.path for route in app.routes}
    assert "/api/v3/history-trial/sessions" in paths
    with TestClient(app) as client:
        assert client.get("/api/v3/history-trial/options").status_code == 401
        assert client.post(
            "/api/v3/history-trial/sessions",
            headers={"Authorization": "Bearer reader-test"},
            json={},
        ).status_code == 403
    settings.agent_runtime_mode = "release"
    with pytest.raises(RuntimeError, match="development"):
        app_module.create_app()


def test_trial_preparation_binds_evaluation_capacity_before_version_creation() -> None:
    class Base:
        settings = SimpleNamespace(agent_runtime_mode="development")
        async def prepare(self, request, *, purpose):
            assert purpose == "evaluation"
            return _prepared_definition()

    definitions = HistoryTrialDefinitions(Base())  # type: ignore[arg-type]
    bound = asyncio.run(definitions.prepare(trial_definition_request(), purpose="evaluation"))
    assert bound["memory_policy_version"] == HISTORY_PROBE_POLICY
    require_trial_definition(bound)
    assert bound["deployment_snapshot"][0]["natural_evaluation_capacity"]["contract"] == "natural-history-probe-h4-v2"
    with pytest.raises(RuntimeValidationError, match="evaluation purpose"):
        asyncio.run(definitions.prepare(trial_definition_request(), purpose="agent_studio"))
    with pytest.raises(RuntimeValidationError, match="differs"):
        asyncio.run(definitions.prepare(
            trial_definition_request().model_copy(update={"prompt_key": "chat_v20260516"}),
            purpose="evaluation",
        ))


def test_trial_options_expose_candidate_without_changing_ordinary_default() -> None:
    base = DefinitionService(
        database=None, settings=SimpleNamespace(agent_runtime_mode="development"),
        prompt_registry=None, router_transport=None,
    )  # type: ignore[arg-type]
    trial = HistoryTrialSessionService(
        database=None, definitions=HistoryTrialDefinitions(base), purpose="evaluation",
    )  # type: ignore[arg-type]
    options = asyncio.run(trial.options())
    assert options["bundles"][0]["prompt_key"] == "chat_v20260926"
    assert options["bundles"][0]["memory_policy_version"] == HISTORY_PROBE_POLICY
    assert base.default_agent_studio_request().prompt_key == "chat_v20260516"


def test_selected_definition_and_reads_keep_evaluation_scope(monkeypatch) -> None:
    async def parent_resolve(*_args):
        return _prepared_definition()

    monkeypatch.setattr(PurposeSessionService, "_resolve_definition", parent_resolve)
    sessions = HistoryTrialSessionService(
        database=None, definitions=None, purpose="evaluation"
    )  # type: ignore[arg-type]
    with pytest.raises(RuntimeValidationError):
        asyncio.run(sessions._resolve_definition(None, None, None, None))

    captured: list[tuple[str, str]] = []

    class Resources:
        async def get_subject_memories(self, subject_id, *, required_purpose):
            captured.append((subject_id, required_purpose))
            return {"subject_id": subject_id}

        async def get_conversation_state(self, conversation_id, *, required_purpose, **_kwargs):
            captured.append((conversation_id, required_purpose))
            return {"id": conversation_id}

    service = HistoryTrialService(
        database=None,
        definitions=SimpleNamespace(settings=SimpleNamespace(agent_runtime_mode="development")),
        resources=Resources(),
    )  # type: ignore[arg-type]

    async def get(_conversation_id):
        return {"conversation": {"purpose": "evaluation"}}

    service.sessions.get = get  # type: ignore[method-assign]
    asyncio.run(service.subject_memories("subject-1"))
    asyncio.run(service.conversation_state("chat-1", message_limit=10, before_sequence=None))
    assert captured == [("subject-1", "evaluation"), ("chat-1", "evaluation")]
