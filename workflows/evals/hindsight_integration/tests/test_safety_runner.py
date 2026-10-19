"""Controller accounting and cleanup with explicit controlled scenario doubles."""

import asyncio
from contextlib import asynccontextmanager
import json
import time
from types import SimpleNamespace

import pytest

from .. import safety_runner
from ..safety_protocol import SafetyContext
from ..records import write_new


@pytest.mark.parametrize("failure", ["scenario", "capture", None])
def test_case_keeps_failure_and_releases_rules_even_when_capture_fails(
    tmp_path, monkeypatch, failure
):
    released = []

    @asynccontextmanager
    async def client(*args):
        yield object()

    class Context:
        def __init__(self, **kwargs):
            self.rules = ["controlled-fault"]

        async def release(self, identity):
            released.append(identity)

        async def restore_host(self):
            pass

        async def capture(self):
            if failure == "capture":
                raise ValueError("controlled_capture_failure")
            return {"runs": []}

    async def scenario(context):
        if failure == "scenario":
            raise ValueError("controlled_scenario_failure")
        return {"controlled": True}

    monkeypatch.setattr(safety_runner, "client", client)
    monkeypatch.setattr(safety_runner, "SafetyContext", Context)
    monkeypatch.setitem(safety_runner.SCENARIOS, "controlled", scenario)
    result = asyncio.run(
        safety_runner.one_case(tmp_path / "case", "controlled", None, {}, {})
    )
    assert result["status"] == ("failed" if failure else "passed")
    assert released == ["controlled-fault"]
    saved = json.loads((tmp_path / "case/outcome.json").read_text())["payload"]
    assert saved == result
    if failure == "scenario":
        assert not (tmp_path / "case/evidence.json").exists()
    if failure == "capture":
        assert (tmp_path / "case/evidence.json").exists()
        assert "capture_error" in saved


@pytest.mark.parametrize(
    "scenarios", [[], ["undeclared"], ["cancellation", "cancellation"]]
)
def test_refuse_unplanned_or_duplicate_safety_cases_before_external_actions(
    tmp_path, scenarios
):
    with pytest.raises(ValueError, match="predeclared"):
        asyncio.run(
            safety_runner.run_safety(
                tmp_path / "run",
                activation_root=tmp_path / "absent",
                controller_revision="a" * 40,
                scenarios=scenarios,
            )
        )
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize("mismatch", [None, "id", "product_revision", "status"])
def test_host_receipt_requires_request_and_product_identity(tmp_path, mismatch):
    async def check():
        context = SafetyContext(
            api=None,
            router=None,
            fault=None,
            root=tmp_path,
            deadline=time.monotonic() + 3,
            runtime=SimpleNamespace(product_revision="a" * 40),
        )
        task = asyncio.create_task(context.host("stop-native"))
        request = tmp_path / "host-requests/0001.json"
        while not request.exists():
            await asyncio.sleep(0)
        value = json.loads(request.read_text())
        response = {
            "id": value["id"],
            "product_revision": value["product_revision"],
            "status": "ok",
        }
        if mismatch:
            response[mismatch] = "different"
        write_new(tmp_path / "host-responses/0001.json", response)
        if mismatch:
            with pytest.raises(ValueError, match="owned_host_control_failed"):
                await task
        else:
            assert await task == response

    asyncio.run(check())
