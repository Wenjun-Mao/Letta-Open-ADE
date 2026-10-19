from __future__ import annotations

import asyncio
from types import SimpleNamespace
import pytest

import ade_api.features.agent_runtime.definition_service as definition_service
from ade_api.features.agent_runtime.agent_studio_sessions import PurposeSessionService
from ade_api.features.agent_runtime.definition_service import DefinitionService
from ade_api.features.agent_runtime.errors import UnqualifiedDeployment
from ade_api.platform.settings import AdeApiSettings


def _definition_service(*, mode: str) -> DefinitionService:
    return DefinitionService(
        database=None,  # type: ignore[arg-type]
        settings=AdeApiSettings(_env_file=None, agent_runtime_mode=mode),
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
                roles=("conversation", "compaction"),
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
    assert request.compaction_model_key == "local::chat"
    assert request.prompt_key == "chat_v20261019"
    assert request.persona_key == "chat_linxiaotang"
    assert request.tool_names == ["search_memory"]


def test_hindsight_cannot_inherit_native_release_qualification() -> None:
    with pytest.raises(UnqualifiedDeployment, match="not release-qualified"):
        _definition_service(mode="release").default_agent_studio_request()


def test_development_configured_bundle_comes_from_manifest_without_provider_io() -> (
    None
):
    bundle = _definition_service(mode="development").configured_agent_studio_bundle()

    assert bundle["key"] == "ade_hindsight_default"
    assert {deployment["role"] for deployment in bundle["deployments"]} == {
        "conversation",
        "compaction",
    }


class _PreparedDefinitions:
    def __init__(self, mode: str) -> None:
        self.settings = SimpleNamespace(agent_runtime_mode=mode)

    def configured_agent_studio_bundle(self):
        return {
            "key": "ade_hindsight_default",
            "name": "ADE Hindsight Default",
            "model_key": "local::chat",
            "compaction_model_key": "local::chat",
            "prompt_key": "chat_v20261019",
            "persona_key": "chat_linxiaotang",
            "tool_names": ["search_memory"],
            "memory_policy_version": "hindsight-message-v1",
            "qualification_state": "unqualified",
            "deployments": [],
        }


def test_development_options_expose_configured_unqualified_bundle() -> None:
    service = PurposeSessionService(
        database=None,  # type: ignore[arg-type]
        definitions=_PreparedDefinitions("development"),  # type: ignore[arg-type]
    )

    result = asyncio.run(service.options())

    assert result["default_bundle_key"] == "ade_hindsight_default"
    assert result["bundles"][0]["qualification_state"] == "unqualified"


def test_release_options_never_expose_an_unqualified_bundle() -> None:
    service = PurposeSessionService(
        database=None,  # type: ignore[arg-type]
        definitions=_PreparedDefinitions("release"),  # type: ignore[arg-type]
    )

    result = asyncio.run(service.options())

    assert result["bundles"] == []
