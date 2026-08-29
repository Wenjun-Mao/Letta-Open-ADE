from __future__ import annotations

from pathlib import Path

import pytest

from workflows.evals.agent_runtime_v3_acceptance.config import (
    DEFAULT_DGX_CHAT_MODEL,
    DEFAULT_DGX_EMBEDDING_MODEL,
    AcceptanceConfig,
    ConfigError,
    load_config,
)
from workflows.evals.agent_runtime_v3_acceptance.run import parse_args


def test_defaults_match_production_qualification_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_V3_ACCEPTANCE_API_BASE_URL", "https://ade.test/")
    monkeypatch.setenv("AGENT_RUNTIME_V3_ACCEPTANCE_API_KEY", "operator-key")

    config = load_config(tmp_path / "missing.toml")

    assert config.api_base_url == "https://ade.test"
    assert config.conversation_model_key == DEFAULT_DGX_CHAT_MODEL
    assert config.reviewer_model_key == DEFAULT_DGX_CHAT_MODEL
    assert config.embedding_model_key == DEFAULT_DGX_EMBEDDING_MODEL
    assert config.rounds == 3
    assert config.timeout_seconds == 180
    assert config.retry_count == 0
    assert config.include_llama_compatibility is True


def test_rejects_unsafe_cleanup_configuration(tmp_path: Path) -> None:
    config = AcceptanceConfig(
        api_base_url="https://ade.test",
        api_key="operator-key",
        output_dir=tmp_path,
        database_url="postgresql://example",
        cleanup_owner="wrong-owner",
    )

    with pytest.raises(ConfigError, match="cleanup_owner"):
        config.validate()


def test_runner_exposes_exact_test_center_flags() -> None:
    args = parse_args(
        [
            "--config",
            "acceptance.toml",
            "--output-dir",
            "out",
            "--conversation-model-key",
            "chat",
            "--reviewer-model-key",
            "reviewer",
            "--embedding-model-key",
            "embed",
            "--rounds",
            "3",
            "--timeout-seconds",
            "180",
            "--retry-count",
            "0",
            "--no-include-llama-compatibility",
        ]
    )

    assert args.config == "acceptance.toml"
    assert args.output_dir == "out"
    assert args.conversation_model_key == "chat"
    assert args.reviewer_model_key == "reviewer"
    assert args.embedding_model_key == "embed"
    assert args.rounds == 3
    assert args.timeout_seconds == 180
    assert args.retry_count == 0
    assert args.include_llama_compatibility is False
