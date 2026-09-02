from __future__ import annotations

from ade_api.features.model_catalog.contracts import ApiOptionEntryResponse
from ade_api.features.model_catalog.identity import (
    attach_model_option_identity,
    model_option_identity_sha256,
)


def test_model_option_identity_ignores_display_and_availability_fields() -> None:
    option = {
        "key": "openai-proxy/dgx::qwen",
        "label": "Qwen",
        "description": "Local model",
        "available": True,
        "source_id": "dgx",
        "provider_model_id": "dgx::qwen",
        "sampling_defaults": {"temperature": 1.0},
        "deployment": {"fingerprint": {"artifact_revision": "rev-1"}},
    }

    baseline = model_option_identity_sha256(option)
    changed_display = {
        **option,
        "label": "Renamed Qwen",
        "description": "Updated copy",
        "available": False,
    }

    assert model_option_identity_sha256(changed_display) == baseline


def test_model_option_identity_changes_with_execution_inputs() -> None:
    option = {
        "key": "openai-proxy/dgx::qwen",
        "source_id": "dgx",
        "provider_model_id": "dgx::qwen",
        "sampling_defaults": {"temperature": 1.0},
        "deployment": {"fingerprint": {"artifact_revision": "rev-1"}},
    }

    assert model_option_identity_sha256(
        {**option, "sampling_defaults": {"temperature": 0.7}}
    ) != model_option_identity_sha256(option)
    assert model_option_identity_sha256(
        {**option, "deployment": {"fingerprint": {"artifact_revision": "rev-2"}}}
    ) != model_option_identity_sha256(option)
    assert model_option_identity_sha256(
        {**option, "tool_call_thinking_default_enabled": False}
    ) != model_option_identity_sha256(option)


def test_attached_identity_survives_public_embedding_option_serialization() -> None:
    sparse_embedding_option = {
        "key": "letta/letta-free",
        "label": "Letta Free",
        "description": "Shared embedding model",
        "source_id": "letta",
        "provider_model_id": "letta-free",
    }

    attached_option = attach_model_option_identity(sparse_embedding_option)
    public_option = ApiOptionEntryResponse.model_validate(attached_option).model_dump()

    assert public_option["sampling_defaults"] == {}
    assert public_option["scenario_sampling_defaults"] == {}
    assert public_option["identity_sha256"] == model_option_identity_sha256(
        public_option
    )
