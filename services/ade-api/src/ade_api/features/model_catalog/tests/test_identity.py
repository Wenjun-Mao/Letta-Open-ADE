from __future__ import annotations

from ade_api.features.model_catalog.identity import model_option_identity_sha256


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
