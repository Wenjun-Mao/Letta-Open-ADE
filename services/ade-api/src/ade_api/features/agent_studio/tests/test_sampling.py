from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from ade_api.features.agent_studio.agents_api import (
    _verify_created_agent_state,
    _verify_expected_identities,
)
from ade_api.features.agent_studio.contracts import AgentCreateRequest
from ade_api.features.model_catalog import agent_studio_llm_config_for_model
from ade_api.platform.settings import clear_settings_cache


def test_router_llm_config_includes_create_time_sampling(monkeypatch) -> None:
    monkeypatch.setenv("ADE_API_MODEL_ROUTER_BASE_URL", "http://model_router:8290")
    clear_settings_cache()

    config = agent_studio_llm_config_for_model(
        "openai-proxy/local_llama_server::gemma4",
        temperature=0.7,
        top_p=0.85,
        top_k=64,
    )

    assert config is not None
    assert config["model"] == "local_llama_server::gemma4"
    assert config["temperature"] == 0.7
    assert config["top_p"] == 0.85
    assert config["top_k"] == 64


def test_router_llm_config_omits_unspecified_sampling(monkeypatch) -> None:
    monkeypatch.setenv("ADE_API_MODEL_ROUTER_BASE_URL", "http://model_router:8290")
    clear_settings_cache()

    config = agent_studio_llm_config_for_model(
        "openai-proxy/local_llama_server::gemma4"
    )

    assert config is not None
    assert "temperature" not in config
    assert "top_p" not in config
    assert "top_k" not in config


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("temperature", -0.1),
        ("temperature", 2.1),
        ("top_p", 0),
        ("top_p", 1.1),
        ("top_k", 0),
    ],
)
def test_agent_create_request_rejects_invalid_sampling_ranges(
    field: str, value: float | int
) -> None:
    kwargs = {
        "name": "agent",
        "model": "openai-proxy/local_llama_server::gemma4",
        field: value,
    }
    with pytest.raises(ValidationError):
        AgentCreateRequest(**kwargs)


def test_agent_create_request_validates_expected_identity_hashes() -> None:
    with pytest.raises(ValidationError):
        AgentCreateRequest(
            model="openai-proxy/test::model",
            prompt_content_sha256="not-a-sha",
        )


def test_agent_creation_rejects_stale_evaluation_identity() -> None:
    request = AgentCreateRequest(
        model="openai-proxy/test::model",
        prompt_content_sha256="a" * 64,
    )

    with pytest.raises(HTTPException) as error:
        _verify_expected_identities(
            request,
            {
                "model_identity_sha256": "b" * 64,
                "embedding_identity_sha256": None,
                "prompt_content_sha256": "c" * 64,
                "persona_content_sha256": "d" * 64,
            },
        )

    assert error.value.status_code == 409
    assert "changed after" in str(error.value.detail)


def _created_agent_client(
    *,
    model: str = "openai-proxy/test::model",
    embedding: str = "letta/test-embedding",
    system: str = "System prompt",
    persona: str = "Persona prompt",
):
    agent = SimpleNamespace(
        id="agent-1",
        model=model,
        embedding=embedding,
        system=system,
    )
    blocks = SimpleNamespace(
        list=lambda **_: [SimpleNamespace(label="persona", value=persona)]
    )
    agents = SimpleNamespace(retrieve=lambda **_: agent, blocks=blocks)
    return SimpleNamespace(agents=agents)


def test_created_agent_state_is_confirmed_from_letta() -> None:
    identities = {
        "model_identity_sha256": "a" * 64,
        "embedding_identity_sha256": "b" * 64,
        "prompt_content_sha256": "c" * 64,
        "persona_content_sha256": "d" * 64,
    }

    confirmed = _verify_created_agent_state(
        client=_created_agent_client(),
        agent_id="agent-1",
        request=AgentCreateRequest(
            model="openai-proxy/test::model",
            embedding="letta/test-embedding",
        ),
        prompt_content="System prompt",
        persona_content="Persona prompt",
        catalog_identities=identities,
    )

    assert confirmed["model_identity_sha256"] == "a" * 64
    assert confirmed["prompt_content_sha256"] != "c" * 64
    assert confirmed["persona_content_sha256"] != "d" * 64


def test_created_agent_state_rejects_effective_content_drift() -> None:
    with pytest.raises(HTTPException) as error:
        _verify_created_agent_state(
            client=_created_agent_client(persona="Unexpected persona"),
            agent_id="agent-1",
            request=AgentCreateRequest(
                model="openai-proxy/test::model",
                embedding="letta/test-embedding",
            ),
            prompt_content="System prompt",
            persona_content="Persona prompt",
            catalog_identities={
                "model_identity_sha256": "a" * 64,
                "embedding_identity_sha256": "b" * 64,
                "prompt_content_sha256": "c" * 64,
                "persona_content_sha256": "d" * 64,
            },
        )

    assert error.value.status_code == 409
    assert "persona memory content" in str(error.value.detail)
