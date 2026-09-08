from __future__ import annotations

import pytest

from workflows.smoke.ade_api_e2e_check import SmokeCheckError, _agent_studio_bundle


def _bundle(key: str) -> dict[str, object]:
    return {
        "key": key,
        "model_key": "chat_source::chat-model",
        "reviewer_model_key": "reviewer_source::reviewer-model",
        "embedding_model_key": "embedding_source::embedding-model",
    }


def test_agent_studio_bundle_uses_the_backend_default() -> None:
    fallback = _bundle("fallback")
    selected = _bundle("selected")

    result = _agent_studio_bundle(
        {"default_bundle_key": "selected", "bundles": [fallback, selected]}
    )

    assert result is selected


def test_agent_studio_bundle_rejects_an_empty_configuration() -> None:
    with pytest.raises(SmokeCheckError, match="no configured runtime bundle"):
        _agent_studio_bundle({"default_bundle_key": "missing", "bundles": []})
