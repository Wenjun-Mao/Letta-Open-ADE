"""Fresh catalog and absolute public-request deadline failures."""

import asyncio

import httpx
import pytest

from .. import runner, transport
from .test_runner import Scripted, raw


@pytest.mark.parametrize(
    "preflight",
    [raw({"error": "auth"}, 401), raw(b"malformed"), raw({"sources": [], "items": []})],
)
def test_catalog_failure_stops_without_chat(launch, preflight):
    directory, execute, _ = launch
    script = Scripted(preflight=preflight)
    result = execute(script)
    assert all(row["disposition"] == "unrun" for row in result.values())
    assert not script.sent
    assert (directory / "preflight-01.raw.json").exists()
    with pytest.raises(ValueError, match="stop"):
        execute(script)


def test_preflight_capture_interruption_refuses(launch, monkeypatch):
    _, execute, _ = launch
    original = runner.write_once

    def interrupted(path, value):
        if path.name == "preflight-01.raw.json":
            raise KeyboardInterrupt()
        return original(path, value)

    monkeypatch.setattr(runner, "write_once", interrupted)
    script = Scripted()
    with pytest.raises(KeyboardInterrupt):
        execute(script)
    with pytest.raises(ValueError, match="preflight capture"):
        execute(script)
    assert script.catalogs == 1 and not script.sent


def test_absolute_deadline_cancels_single_http_attempt(monkeypatch):
    observed = []
    actual_timeout = asyncio.timeout
    deadlines = []

    def short_timeout(seconds):
        deadlines.append(seconds)
        return actual_timeout(0.001)

    monkeypatch.setattr(transport.asyncio, "timeout", short_timeout)

    async def handler(request):
        observed.append(request)
        await asyncio.sleep(60)
        return httpx.Response(200, json={})

    async def exercise():
        router = transport.Router(
            "http://127.0.0.1:9999", "synthetic", transport=httpx.MockTransport(handler)
        )
        try:
            with pytest.raises(TimeoutError):
                await router.send({"model": "synthetic"})
        finally:
            await router.close()

    asyncio.run(exercise())
    assert deadlines == [180] and len(observed) == 1
