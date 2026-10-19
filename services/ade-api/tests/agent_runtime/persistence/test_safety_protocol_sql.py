"""Safety controller public readbacks with normal SQL/Router and controlled inference."""

import asyncio
import time

import httpx
import pytest

from workflows.evals.hindsight_integration.safety_protocol import SafetyContext
from workflows.evals.hindsight_integration.host_scenarios import recall_outage
from ade_api.integrations.hindsight import HindsightError

from .hindsight_support import DATABASE_URL, engine
from .product_actor_fixture import actor_fixture
from .test_product_actor_sql import runtime


pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Disposable SQL not configured"
)


@pytest.mark.parametrize("corrupt_document", [False, True])
def test_safety_controller_reads_exact_normal_product_sources(
    monkeypatch, tmp_path, corrupt_document
):
    monkeypatch.setenv("ADE_SOURCE_REVISION", "f" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "e" * 64)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "false")
    asyncio.run(check(monkeypatch, tmp_path, corrupt_document))


async def check(monkeypatch, root, corrupt_document):
    db = engine()
    async with actor_fixture(monkeypatch, root, db) as fixture:
        out = root / "safety"
        out.mkdir(mode=0o700)
        async with (
            httpx.AsyncClient(
                base_url="http://ade",
                transport=fixture.transport_factory(out / "api-http"),
            ) as api,
            httpx.AsyncClient(
                base_url="http://router",
                transport=fixture.transport_factory(out / "router-http"),
                headers={"Authorization": "Bearer controlled-router"},
            ) as router,
        ):
            context = SafetyContext(
                api=api,
                router=router,
                fault=None,
                root=out,
                deadline=time.monotonic() + 30,
                runtime=runtime(),
            )
            session = await context.session("controlled SQL safety")
            receipt = await context.accept(
                session, "Controlled safety input, not observed semantics."
            )
            await context.terminal(receipt["run_id"], expected="succeeded")
            await context.messages(session, users=1, assistants=1)
            await context.retained(session)
            fixture.native.delivery.corrupt_document = corrupt_document
            if corrupt_document:
                with pytest.raises(httpx.HTTPStatusError) as error:
                    await context.retained(session)
                assert error.value.response.status_code == 503
            else:
                retained = await context.retained(session)
                assert len(retained["sources"]) == 2
                capture = (await context.capture())["payload"]["runs"][0]
                assert capture["run"]["id"] == receipt["run_id"]
                assert len(capture["wires"]) == len(fixture.calls) == 1


def test_outage_controller_uses_one_saved_input_and_explicit_retry(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("ADE_SOURCE_REVISION", "f" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "e" * 64)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "false")
    asyncio.run(outage(monkeypatch, tmp_path))


async def outage(monkeypatch, root):
    db = engine()
    async with actor_fixture(monkeypatch, root, db) as fixture:
        offline, actions = False, []
        original = fixture.native.bank_config

        async def bank_config(bank):
            if offline:
                raise HindsightError("hindsight_unavailable")
            return await original(bank)

        monkeypatch.setattr(fixture.native, "bank_config", bank_config)

        async def host(action, details=None):
            nonlocal offline
            actions.append(action)
            assert action in {"stop-native", "start-native"}
            offline = action == "stop-native"
            return {"controlled_host_action": action}

        out = root / "safety"
        out.mkdir(mode=0o700)
        async with (
            httpx.AsyncClient(
                base_url="http://ade",
                transport=fixture.transport_factory(out / "api-http"),
            ) as api,
            httpx.AsyncClient(
                base_url="http://router",
                transport=fixture.transport_factory(out / "router-http"),
                headers={"Authorization": "Bearer controlled-router"},
            ) as router,
        ):
            context = SafetyContext(
                api=api,
                router=router,
                fault=None,
                root=out,
                deadline=time.monotonic() + 30,
                runtime=runtime(),
            )
            context.host = host
            result = await recall_outage(context)
            assert actions == ["stop-native", "start-native"]
            assert result["paused"]["status"] == "paused"
            assert result["succeeded"]["attempt_count"] == 2
            capture = (await context.capture())["payload"]["runs"][0]
            assert [
                row["status"] for row in capture["private_export"]["saved_attempts"]
            ] == ["failed", "succeeded"]
            assert len(fixture.calls) == 1
            assert len(fixture.native.delivery.submissions) == 2
