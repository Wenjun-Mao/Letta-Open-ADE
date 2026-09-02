from __future__ import annotations

from pathlib import Path

import pytest

from workflows.evals.agent_runtime_parity.config import ConfigError
from workflows.evals.agent_runtime_parity.run import config_from_args, parse_args


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_PARITY_LEGACY_API_KEY", "legacy")
    monkeypatch.setenv("AGENT_RUNTIME_PARITY_NATIVE_API_KEY", "native")
    monkeypatch.setenv(
        "AGENT_RUNTIME_PARITY_DATABASE_URL", "postgresql://ade:password@localhost/ade"
    )


def test_cli_constructs_a_fully_scoped_config_without_live_calls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _credentials(monkeypatch)
    args = parse_args(
        [
            "--config",
            str(PROJECT_ROOT / "workflows/evals/agent_runtime_parity/config.toml"),
            "--output-dir",
            str(tmp_path),
            "--legacy-api-base-url",
            "http://legacy.test",
            "--native-api-base-url",
            "http://native.test",
            "--timeout-seconds",
            "180",
            "--retry-count",
            "0",
        ]
    )

    config = config_from_args(args)

    assert config.output_dir == tmp_path
    assert config.legacy_api_base_url == "http://legacy.test"
    assert config.native_api_base_url == "http://native.test"
    assert config.retry_count == 0


def test_cli_rejects_nonzero_retry_before_any_live_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _credentials(monkeypatch)
    args = parse_args(["--retry-count", "1"])

    with pytest.raises(ConfigError, match="retry_count must be 0"):
        config_from_args(args)
