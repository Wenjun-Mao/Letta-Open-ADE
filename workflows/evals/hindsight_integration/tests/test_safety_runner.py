"""Controller accounting and cleanup with explicit controlled scenario doubles."""

import asyncio
from contextlib import asynccontextmanager
import json

import pytest

from .. import safety_runner


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
    monkeypatch.setitem(safety_runner.PROXIED_SCENARIOS, "controlled", scenario)
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
