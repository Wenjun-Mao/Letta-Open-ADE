"""Private defaults remain local inputs, not process-global configuration writes."""

from dataclasses import replace
import json
import os

import pytest

from .. import config as configuration
from .. import workflow


@pytest.mark.parametrize("override", [None, "explicit", ""])
def test_private_defaults_do_not_escape_and_explicit_environment_wins(
    tmp_path, monkeypatch, override
):
    monkeypatch.setattr(configuration, "PROJECT_ROOT", tmp_path)
    for key in (
        "ADE_API_ADMIN_KEY",
        "MODEL_ROUTER_API_KEY",
        "ADE_API_MODEL_ROUTER_BASE_URL",
        "COMPOSE_PROJECT_NAME",
    ):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text(
        "ADE_API_ADMIN_KEY=synthetic-ade\nMODEL_ROUTER_API_KEY=synthetic-router-secret\n"
        "ADE_API_MODEL_ROUTER_BASE_URL=http://synthetic-router\nCOMPOSE_PROJECT_NAME=must-not-escape\n"
    )
    path = tmp_path / "config.toml"
    path.write_text(f'fixtures_dir = "{tmp_path}"\n')
    if override is not None:
        monkeypatch.setenv("ADE_API_ADMIN_KEY", override)
        monkeypatch.setenv("ADE_API_MODEL_ROUTER_BASE_URL", override)
    before = dict(os.environ)
    config = configuration.load_config(path)
    unchanged = dict(os.environ) == before
    assert unchanged
    assert config.api_key == ("synthetic-ade" if override is None else override)
    assert config.model_router_base_url == (
        "http://synthetic-router" if override is None else override
    )
    assert config.model_router_api_key == "synthetic-router-secret"
    assert "synthetic-ade" not in repr(
        config
    ) and "synthetic-router-secret" not in repr(config)
    exported = json.dumps(workflow._config_payload(config))
    assert "synthetic-router-secret" not in exported
    assert (
        "synthetic-ade" not in exported and '"model_router_api_key": "***"' in exported
    )


def test_ade_client_receives_configured_key_not_later_ambient_credentials(
    tmp_path, monkeypatch
):
    config = configuration.load_config(configuration.WORKFLOW_ROOT / "config.toml")
    config = replace(config, api_key="synthetic-bound-ade", output_dir=tmp_path)
    monkeypatch.setenv("ADE_API_ADMIN_KEY", "different-later-key")
    received = []

    class Client:
        def __init__(self, **kwargs):
            received.append(kwargs["api_key"])

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def options(self):
            raise RuntimeError("controlled-stop-before-provider")

    monkeypatch.setattr(workflow, "AdeApiClient", Client)
    with pytest.raises(RuntimeError, match="controlled-stop"):
        workflow.run_evaluation(config)
    assert received == ["synthetic-bound-ade"]
