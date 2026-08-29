from __future__ import annotations

from pathlib import Path

from workflows.evals.agent_runtime_study.config import load_config, with_overrides


def test_study_endpoint_environment_overrides_file(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "study.toml"
    config_path.write_text(
        "\n".join(
            (
                'router_v1_base_url = "http://model-router:8010/v1"',
                'ade_api_base_url = "http://ade-api:8000"',
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "AGENT_RUNTIME_STUDY_ROUTER_V1_BASE_URL",
        "http://127.0.0.1:18010/v1",
    )
    monkeypatch.setenv(
        "AGENT_RUNTIME_STUDY_ADE_API_BASE_URL",
        "http://127.0.0.1:18000",
    )

    config = load_config(config_path)

    assert config.router_v1_base_url == "http://127.0.0.1:18010/v1"
    assert config.ade_api_base_url == "http://127.0.0.1:18000"


def test_host_api_default_uses_configured_compose_port(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "study.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.delenv("AGENT_RUNTIME_STUDY_ADE_API_BASE_URL", raising=False)
    monkeypatch.setenv("ADE_API_PORT", "8123")

    config = load_config(config_path)

    assert config.ade_api_base_url == "http://127.0.0.1:8123"


def test_request_scoped_retry_override_does_not_change_the_default(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "study.toml"
    config_path.write_text("retry_count = 0\n", encoding="utf-8")

    config = load_config(config_path)
    overridden = with_overrides(config, retry_count=1)

    assert config.policy.retry_count == 0
    assert overridden.policy.retry_count == 1
