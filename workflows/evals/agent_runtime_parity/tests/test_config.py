from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from workflows.evals.agent_runtime_parity.config import (
    ConfigError,
    ParityConfig,
    load_config,
    validate_config,
    validate_run_id,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _config() -> ParityConfig:
    return ParityConfig(
        legacy_api_key="legacy",
        native_api_key="native",
        database_url="postgresql://ade:password@localhost/ade",
        fixture_path=PROJECT_ROOT
        / "workflows/evals/chat_memory_eval/fixtures/recent_user_chat_turns.json",
    )


def test_config_loads_required_dgx_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_PARITY_LEGACY_API_KEY", "legacy")
    monkeypatch.setenv("AGENT_RUNTIME_PARITY_NATIVE_API_KEY", "native")
    monkeypatch.setenv(
        "AGENT_RUNTIME_PARITY_DATABASE_URL", "postgresql://ade:password@localhost/ade"
    )

    config = load_config(
        PROJECT_ROOT / "workflows/evals/agent_runtime_parity/config.toml"
    )

    assert config.rounds == 3
    assert config.timeout_seconds == 180
    assert config.retry_count == 0
    assert config.legacy_model == "openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8"
    assert config.native_conversation_model == "dgx_vllm::qwen3.6-35b-a3b-fp8"
    assert config.native_embedding_model == (
        "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B"
    )


def test_config_rejects_retries_and_round_counts_outside_diagnostic_range() -> None:
    config = _config()

    with pytest.raises(ConfigError, match="retry_count must be 0"):
        validate_config(replace(config, retry_count=1))
    validate_config(replace(config, rounds=1))
    with pytest.raises(ConfigError, match="rounds must be between 1 and 3"):
        validate_config(replace(config, rounds=4))


def test_run_id_remains_safe_for_scoped_cleanup() -> None:
    assert validate_run_id("parity-20260902t120000z-a1b2c3d4") == (
        "parity-20260902t120000z-a1b2c3d4"
    )
    with pytest.raises(ConfigError, match="cleanup keys"):
        validate_run_id("Bad run id")
