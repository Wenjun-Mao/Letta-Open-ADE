"""Keep workflow safety tests on a declared campaign-relative wall clock."""

import time

import pytest

from workflows.evals.hindsight_memory_probe.campaign_clock import STARTED
from workflows.evals.hindsight_memory_probe import campaign_clock, supervisor

SYNTHETIC_NOW = STARTED + 100


@pytest.fixture(autouse=True)
def synthetic_wall_clock(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: SYNTHETIC_NOW)


@pytest.fixture(autouse=True)
def synthetic_activation_namespace(monkeypatch, tmp_path):
    namespace = {
        "activation_id": campaign_clock.ACTIVATION_ID,
        "receipts_root": str(tmp_path),
        "supervisor_state": str(tmp_path),
    }
    monkeypatch.setattr(supervisor, "activation_namespace", lambda _release: namespace)
