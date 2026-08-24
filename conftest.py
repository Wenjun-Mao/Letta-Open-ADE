from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ade_api.platform.settings import clear_settings_cache


@pytest.fixture(autouse=True)
def _disable_live_router_by_default(monkeypatch):
    monkeypatch.setenv("ADE_API_AUTH_ENABLED", "false")
    monkeypatch.setenv("ADE_API_MODEL_ROUTER_BASE_URL", "")
    clear_settings_cache()
    yield
    clear_settings_cache()
