from __future__ import annotations

from fastapi.testclient import TestClient

import ade_api.platform.app as app_module
from ade_api.platform.app import create_app
from ade_api.platform.dependencies import get_prompt_persona_registry
from ade_api.features.prompt_center.registry import PromptPersonaRegistry


def _client(monkeypatch, registry: PromptPersonaRegistry) -> TestClient:
    monkeypatch.setattr(
        app_module,
        "validate_capabilities_startup",
        lambda *_args: None,
    )
    app = create_app()
    app.dependency_overrides[get_prompt_persona_registry] = lambda: registry
    return TestClient(app)


def test_update_persona_template_content_only_with_scenario(
    monkeypatch, tmp_path
) -> None:
    registry = PromptPersonaRegistry(tmp_path)
    registry.create_template(
        "persona",
        key="chat_patch_persona",
        content="1",
        label="Persona One",
        description="Initial persona",
    )

    with _client(monkeypatch, registry) as client:
        response = client.patch(
            "/api/v2/prompt-center/personas/chat_patch_persona?scenario=chat",
            json={"content": "2"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["key"] == "chat_patch_persona"
    assert payload["scenario"] == "chat"
    assert payload["content"] == "2"
    assert payload["label"] == "Persona One"
    assert payload["description"] == "Initial persona"


def test_update_prompt_template_content_only_with_scenario(
    monkeypatch, tmp_path
) -> None:
    registry = PromptPersonaRegistry(tmp_path)
    registry.create_template(
        "prompt",
        key="chat_patch_prompt",
        content="1",
        label="Prompt One",
        description="Initial prompt",
    )

    with _client(monkeypatch, registry) as client:
        response = client.patch(
            "/api/v2/prompt-center/prompts/chat_patch_prompt?scenario=chat",
            json={"content": "2"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["key"] == "chat_patch_prompt"
    assert payload["scenario"] == "chat"
    assert payload["content"] == "2"
    assert payload["label"] == "Prompt One"
    assert payload["description"] == "Initial prompt"


def test_update_label_persona_returns_clean_400(monkeypatch, tmp_path) -> None:
    registry = PromptPersonaRegistry(tmp_path)

    with _client(monkeypatch, registry) as client:
        response = client.patch(
            "/api/v2/prompt-center/personas/label_patch_persona?scenario=label",
            json={"content": "2"},
        )

    assert response.status_code == 400
    assert (
        response.json()["detail"] == "Label scenario does not support persona templates"
    )


def test_update_prompt_template_requires_at_least_one_field(
    monkeypatch, tmp_path
) -> None:
    registry = PromptPersonaRegistry(tmp_path)
    registry.create_template("prompt", key="chat_patch_empty", content="1")

    with _client(monkeypatch, registry) as client:
        response = client.patch(
            "/api/v2/prompt-center/prompts/chat_patch_empty?scenario=chat",
            json={},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "At least one field must be provided"


def test_list_personas_supports_search_query(monkeypatch, tmp_path) -> None:
    registry = PromptPersonaRegistry(tmp_path)
    registry.create_template(
        "persona",
        key="comment_search_persona",
        content="Gentle football fan who likes Messi.",
        label="Search Persona",
        scenario="comment",
    )
    registry.create_template(
        "persona",
        key="comment_other_persona",
        content="Different voice.",
        label="Other Persona",
        scenario="comment",
    )

    with _client(monkeypatch, registry) as client:
        response = client.get(
            "/api/v2/prompt-center/personas?scenario=comment&search=Messi",
        )

    assert response.status_code == 200
    payload = response.json()
    assert [item["key"] for item in payload["items"]] == ["comment_search_persona"]
