"""Synthetic launch identity; never reads credentials or starts a service."""

import asyncio

import pytest

from .. import receipts, runner
from ..contracts import load_prepared


@pytest.fixture
def launch(tmp_path, monkeypatch):
    monkeypatch.setattr(receipts, "OUTPUTS", tmp_path)
    directory = tmp_path / "d04-comparison"
    origin = {
        "head": "synthetic-committed-head",
        "requests_sha256": load_prepared()["requests_sha256"],
    }
    config = {
        "source_head": origin["head"],
        "isolated_loopback": True,
        "router_request_timeout_seconds": 180,
        "transport_retries": 0,
        "configuration_sha256": load_prepared()["configuration_sha256"],
    }

    def execute(router, source=lambda: origin):
        return asyncio.run(runner.run(directory, router, config, source=source))

    return directory, execute, origin
