"""Full actor/sidecar mechanics with real SQL/Router and explicitly controlled inference."""

import asyncio

import pytest

from ade_api.integrations.hindsight_bank import bank_configuration_sha256
from content.prompts.system.chat.chat_v20261019 import PROMPT
from workflows.evals.hindsight_integration.casebook import load_suite
from workflows.evals.hindsight_integration.models import RuntimeBinding
from workflows.evals.hindsight_integration.offline import scripted_runtime
from workflows.evals.hindsight_integration.product_slot import run_product_slot
from workflows.evals.hindsight_integration.runs import (
    prepare_run,
    start_attempt,
    load_capture,
)

from .hindsight_support import DATABASE_URL, engine
from .product_actor_fixture import actor_fixture


pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Disposable SQL not configured"
)


def runtime():
    values = scripted_runtime().model_dump()
    values.update(
        product_revision="f" * 40,
        system_prompt=PROMPT,
        prompt_version="chat_v20261019",
        character_route="fake::character",
        character_identity_sha256="c" * 64,
        context_compaction_identity_sha256="c" * 64,
        character_settings={"controlled_recording_provider": True},
        memory_implementation="hindsight",
        memory_config_sha256=bank_configuration_sha256(),
    )
    return RuntimeBinding(**values)


@pytest.mark.parametrize("case_id", ["q01-relevant", "q02-correction", "q02-change"])
def test_whole_product_slot_and_reloaded_sidecar_mechanics(
    monkeypatch, tmp_path, case_id
):
    monkeypatch.setenv("ADE_SOURCE_REVISION", "f" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "e" * 64)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "false")
    asyncio.run(_slot(monkeypatch, tmp_path, case_id))


@pytest.mark.parametrize("private_reasoning", [False, True])
def test_tool_continuation_and_private_reasoning_capture_boundary(
    monkeypatch, tmp_path, private_reasoning
):
    monkeypatch.setenv("ADE_SOURCE_REVISION", "f" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "e" * 64)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "false")
    asyncio.run(
        _slot(
            monkeypatch,
            tmp_path,
            "q01-relevant",
            tool_on_probe=True,
            private_reasoning=private_reasoning,
        )
    )


async def _slot(
    monkeypatch, root, case_id, *, tool_on_probe=False, private_reasoning=False
):
    db = engine()
    binding = runtime()
    plan_root = root / "run"
    prepare_run(
        plan_root,
        run_id="controlled-product-actor",
        mode="live_capture",
        runtime=binding,
        repeats=1,
        case_ids=[case_id],
        evaluator_revision="f" * 40,
    )
    path = start_attempt(plan_root, case_id, 1)
    async with actor_fixture(
        monkeypatch,
        root,
        db,
        tool_on_probe=tool_on_probe,
        private_tool_reasoning=private_reasoning,
    ) as fixture:
        observation, issues = await run_product_slot(
            path=path,
            case=load_suite()["cases"][case_id],
            repeat=1,
            runtime=binding,
            source=fixture.source,
            api_url="http://ade",
            api_key="controlled-api",
            router_url="http://router",
            router_key="controlled-router",
            timeout=60,
            transport_factory=fixture.transport_factory,
        )
        if private_reasoning:
            assert observation.status == "failed"
            assert observation.stage == "capture"
            assert not observation.input_complete
            assert observation.reply_committed
            assert observation.reply == "Controlled recording-provider response"
            assert observation.product_capture is None
            assert issues and load_capture(path)[-1]
            assert not any(
                b"PRIVATE-THINKING-SECRET" in file.read_bytes()
                for file in root.rglob("*.json")
            )
            return
        assert observation.status == "completed", observation.error
        assert not issues, issues
        assert load_capture(path)[-1] == []
        assert (
            observation.reply_committed
            and len(observation.source_messages)
            == len(load_suite()["cases"][case_id].history) * 2
        )
        assert len(fixture.calls) == (
            len(load_suite()["cases"][case_id].history) + 1 + int(tool_on_probe)
        )
        assert not list(path.glob("review-*.json"))
        original = (path / "readbacks.json").read_bytes()
        (path / "readbacks.json").write_bytes(original + b"\n")
        with pytest.raises(ValueError, match="hash_mismatch"):
            load_capture(path)
