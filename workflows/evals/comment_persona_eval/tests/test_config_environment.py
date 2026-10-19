"""Comment evaluation credentials are explicit and never installed process-wide."""

from dataclasses import replace
import os

import pytest

from .. import config as configuration
from .. import workflow


@pytest.mark.parametrize("override", [None, "explicit", ""])
def test_comment_configuration_reads_private_defaults_without_environment_mutation(
    tmp_path, monkeypatch, override
):
    monkeypatch.setattr(configuration, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("ADE_API_ADMIN_KEY", raising=False)
    monkeypatch.delenv("COMPOSE_PROJECT_NAME", raising=False)
    (tmp_path / ".env").write_text(
        "ADE_API_ADMIN_KEY=synthetic-comment\nCOMPOSE_PROJECT_NAME=must-not-escape\n"
    )
    (tmp_path / "news.txt").write_text("synthetic article")
    path = tmp_path / "config.toml"
    path.write_text('news_path = "news.txt"\n')
    if override is not None:
        monkeypatch.setenv("ADE_API_ADMIN_KEY", override)
    before = dict(os.environ)
    config = configuration.load_config(path)
    unchanged = dict(os.environ) == before
    assert unchanged
    assert config.api_key == ("synthetic-comment" if override is None else override)
    assert "synthetic-comment" not in repr(config)


def test_comment_client_uses_bound_key_without_exporting_it(tmp_path, monkeypatch):
    path = tmp_path / "news.txt"
    path.write_text("synthetic article")
    config = configuration.EvalConfig(
        news_path=path, output_dir=tmp_path, api_key="synthetic-bound-comment"
    )
    monkeypatch.setenv("ADE_API_ADMIN_KEY", "different-later-key")
    headers = []

    def client(**kwargs):
        headers.append(kwargs["headers"])
        raise RuntimeError("controlled-stop-before-provider")

    monkeypatch.setattr(workflow.httpx, "Client", client)
    with pytest.raises(RuntimeError, match="controlled-stop"):
        workflow.run_evaluation(config)
    assert headers == [{"Authorization": "Bearer synthetic-bound-comment"}]
    assert replace(config, rounds=1).api_key == config.api_key
