"""Keep workflow safety tests on a declared campaign-relative wall clock."""

import time

import pytest

from workflows.evals.hindsight_memory_probe.campaign_clock import STARTED

SYNTHETIC_NOW = STARTED + 100


@pytest.fixture(autouse=True)
def synthetic_wall_clock(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: SYNTHETIC_NOW)
