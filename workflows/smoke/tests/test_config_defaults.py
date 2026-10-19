"""Importing an offline smoke helper must not load credentials into its caller."""

import os
from pathlib import Path
import runpy

import dotenv


def test_smoke_defaults_read_dotenv_without_mutating_process_environment(monkeypatch):
    values = {
        "ADE_API_BASE_URL": "http://synthetic-api:8000",
        "ADE_API_ADMIN_KEY": "synthetic-admin",
        "MODEL_ROUTER_API_KEY": "unrelated-synthetic-key",
    }
    monkeypatch.delenv("ADE_API_BASE_URL", raising=False)
    monkeypatch.delenv("ADE_API_ADMIN_KEY", raising=False)
    monkeypatch.delenv("MODEL_ROUTER_API_KEY", raising=False)
    monkeypatch.setattr(dotenv, "dotenv_values", lambda *args, **kwargs: values)
    monkeypatch.setattr(
        dotenv, "load_dotenv", lambda *args, **kwargs: os.environ.update(values)
    )
    before = dict(os.environ)
    result = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "config_defaults.py")
    )
    changed_keys = {
        key
        for key in set(before) | set(os.environ)
        if before.get(key) != os.environ.get(key)
    }
    assert changed_keys == set()
    assert result["DEFAULT_ADE_API_BASE_URL"] == "http://synthetic-api:8000"
    assert result["ade_api_headers"]() == {"Authorization": "Bearer synthetic-admin"}
