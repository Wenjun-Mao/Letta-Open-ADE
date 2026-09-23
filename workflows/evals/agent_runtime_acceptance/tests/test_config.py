from __future__ import annotations

import asyncio
import signal
from pathlib import Path

import pytest

from workflows.evals.agent_runtime_acceptance.config import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_LLAMA_COMPATIBILITY_MODEL,
    DEFAULT_PERSONA_KEY,
    DEFAULT_PROMPT_KEY,
    AcceptanceConfig,
    ConfigError,
    load_config,
    public_config,
)
from workflows.evals.agent_runtime_acceptance import run as run_module
from workflows.evals.agent_runtime_acceptance.run import parse_args


def test_defaults_match_production_qualification_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ACCEPTANCE_API_BASE_URL", "https://ade.test/")
    monkeypatch.setenv("AGENT_RUNTIME_ACCEPTANCE_API_KEY", "operator-key")

    config = load_config(tmp_path / "missing.toml")

    assert config.api_base_url == "https://ade.test"
    assert config.conversation_model_key == DEFAULT_CHAT_MODEL
    assert config.reviewer_model_key == DEFAULT_CHAT_MODEL
    assert config.embedding_model_key == DEFAULT_EMBEDDING_MODEL
    assert config.llama_compatibility_model_key == DEFAULT_LLAMA_COMPATIBILITY_MODEL
    assert config.llama_compatibility_model_key == "local_llama_server::qwen3527b"
    assert config.rounds == 3
    assert config.timeout_seconds == 180
    assert config.retry_count == 0
    assert config.prompt_key == DEFAULT_PROMPT_KEY
    assert config.persona_key == DEFAULT_PERSONA_KEY
    assert config.include_llama_compatibility is False
    assert config.case_keys == ()
    assert public_config(config)["prompt_key"] == DEFAULT_PROMPT_KEY
    assert public_config(config)["persona_key"] == DEFAULT_PERSONA_KEY


def test_case_keys_are_an_explicit_diagnostic_selection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ACCEPTANCE_API_BASE_URL", "https://ade.test")
    monkeypatch.setenv("AGENT_RUNTIME_ACCEPTANCE_API_KEY", "operator-key")
    monkeypatch.setenv(
        "AGENT_RUNTIME_ACCEPTANCE_CASE_KEYS",
        "old_memory_deep_search,weather_tool_failure",
    )

    config = load_config(tmp_path / "missing.toml")

    assert config.case_keys == ("old_memory_deep_search", "weather_tool_failure")


def test_container_environment_is_a_safe_api_key_fallback_for_ui_runs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("AGENT_RUNTIME_ACCEPTANCE_API_KEY", raising=False)
    monkeypatch.setenv("ADE_API_ADMIN_KEY", "container-admin-key")

    config = load_config(tmp_path / "missing.toml")

    assert config.api_key == "container-admin-key"


def test_rejects_invalid_qualification_round_count(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="between 1 and 3"):
        AcceptanceConfig(
            api_base_url="https://ade.test",
            api_key="operator-key",
            output_dir=tmp_path,
            rounds=4,
        ).validate()


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
            "--prompt-key",
            "chat_custom",
            "--persona-key",
            "chat_persona",
            "--rounds",
            "3",
            "--timeout-seconds",
            "180",
            "--retry-count",
            "0",
            "--case-key",
            "old_memory_deep_search",
            "--case-key",
            "weather_tool_failure",
            "--no-include-llama-compatibility",
        ]
    )

    assert args.config == "acceptance.toml"
    assert args.output_dir == "out"
    assert args.conversation_model_key == "chat"
    assert args.reviewer_model_key == "reviewer"
    assert args.embedding_model_key == "embed"
    assert args.prompt_key == "chat_custom"
    assert args.persona_key == "chat_persona"
    assert args.rounds == 3
    assert args.timeout_seconds == 180
    assert args.retry_count == 0
    assert args.case_keys == ["old_memory_deep_search", "weather_tool_failure"]
    assert args.include_llama_compatibility is False


def test_cli_cancellation_unwinds_through_session_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ACCEPTANCE_API_KEY", "operator-key")

    async def cancelled(_config: AcceptanceConfig) -> dict[str, object]:
        signal.raise_signal(signal.SIGTERM)
        await asyncio.sleep(0)
        raise AssertionError("SIGTERM did not cancel the acceptance task")

    monkeypatch.setattr(run_module, "run_acceptance", cancelled)

    assert run_module.main(["--config", str(tmp_path / "missing.toml")]) == 130


def test_cli_does_not_mask_session_cleanup_failure_as_successful_cancellation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ACCEPTANCE_API_KEY", "operator-key")

    async def session_cleanup_fails(_config: AcceptanceConfig) -> dict[str, object]:
        try:
            signal.raise_signal(signal.SIGTERM)
            await asyncio.sleep(0)
        finally:
            raise RuntimeError("session cleanup failed")

    monkeypatch.setattr(run_module, "run_acceptance", session_cleanup_fails)

    with pytest.raises(RuntimeError, match="session cleanup failed"):
        run_module.main(["--config", str(tmp_path / "missing.toml")])
