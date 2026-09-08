from __future__ import annotations

import asyncio
from types import SimpleNamespace

import ade_api.features.agent_runtime.definition_service as definition_service
from ade_api.features.agent_runtime.agent_studio_sessions import PurposeSessionService
from ade_api.features.agent_runtime.definition_service import DefinitionService


def _definition_service(*, mode: str) -> DefinitionService:
    return DefinitionService(
        database=None,  # type: ignore[arg-type]
        settings=SimpleNamespace(agent_runtime_mode=mode),  # type: ignore[arg-type]
        prompt_registry=None,  # type: ignore[arg-type]
        router_transport=None,  # type: ignore[arg-type]
    )


def test_development_default_bundle_uses_active_manifest_routes(monkeypatch) -> None:
    manifest = SimpleNamespace(
        deployments=(
            SimpleNamespace(
                route_aliases=("retired::chat",),
                roles=("conversation",),
                lifecycle="deprecated",
            ),
            SimpleNamespace(
                route_aliases=("local::chat",),
                roles=("conversation", "reviewer"),
                lifecycle="candidate",
            ),
            SimpleNamespace(
                route_aliases=("local::embedding",),
                roles=("retriever",),
                lifecycle="candidate",
            ),
        )
    )
    monkeypatch.setattr(
        definition_service,
        "load_deployment_manifest",
        lambda *_args, **_kwargs: manifest,
    )

    request = _definition_service(mode="development").default_agent_studio_request()

    assert request.model_key == "local::chat"
    assert request.reviewer_model_key == "local::chat"
    assert request.embedding_model_key == "local::embedding"
    assert request.prompt_key == "chat_v20260516"
    assert request.persona_key == "chat_linxiaotang"
    assert request.tool_names == ["search_memory"]


def test_release_default_bundle_uses_validated_release_evidence(monkeypatch) -> None:
    release = SimpleNamespace(
        route_aliases={
            "conversation": "release::chat",
            "reviewer": "release::reviewer",
            "retriever": "release::embedding",
        },
        agent_bundle=SimpleNamespace(
            prompt_key="chat_release",
            persona_key="persona_release",
            tool_names=("search_memory",),
        ),
    )
    monkeypatch.setattr(
        definition_service,
        "load_validated_agent_studio_release",
        lambda: release,
    )

    request = _definition_service(mode="release").default_agent_studio_request()

    assert request.model_key == "release::chat"
    assert request.reviewer_model_key == "release::reviewer"
    assert request.embedding_model_key == "release::embedding"
    assert request.prompt_key == "chat_release"
    assert request.persona_key == "persona_release"


class _PreparedDefinitions:
    def __init__(self, mode: str) -> None:
        self.settings = SimpleNamespace(agent_runtime_mode=mode)

    def default_agent_studio_request(self):
        return SimpleNamespace()

    async def prepare(self, _request, *, purpose: str):
        assert purpose == "agent_studio"
        return {
            "model_key": "local::chat",
            "reviewer_model_key": "local::chat",
            "embedding_model_key": "local::embedding",
            "prompt_key": "chat_v20260516",
            "persona_key": "chat_linxiaotang",
            "tool_names": ["search_memory"],
            "memory_policy_version": "typed-user-facts-v1",
            "qualification_state": "unqualified",
            "deployment_snapshot": [],
        }


def test_development_options_expose_configured_unqualified_bundle() -> None:
    service = PurposeSessionService(
        database=None,  # type: ignore[arg-type]
        definitions=_PreparedDefinitions("development"),  # type: ignore[arg-type]
    )

    result = asyncio.run(service.options())

    assert result["default_bundle_key"] == "ade_native_default"
    assert result["bundles"][0]["qualification_state"] == "unqualified"


def test_release_options_never_expose_an_unqualified_bundle() -> None:
    service = PurposeSessionService(
        database=None,  # type: ignore[arg-type]
        definitions=_PreparedDefinitions("release"),  # type: ignore[arg-type]
    )

    result = asyncio.run(service.options())

    assert result["bundles"] == []
