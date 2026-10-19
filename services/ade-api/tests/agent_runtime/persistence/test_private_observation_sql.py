"""Real product persistence with controlled boundaries, not semantic qualification."""

import asyncio
from uuid import uuid4

from fastapi import FastAPI
import httpx
import pytest

from ade_api.features.agent_runtime.api import router
from ade_api.features.agent_runtime.contracts import AcceptTurnRequest, RetryRunRequest
from ade_api.features.agent_runtime.dependencies import get_agent_runtime_service
from ade_api.features.agent_runtime.private_observation_service import (
    PrivateObservationService,
)
from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.errors import RuntimeNotFound
from ade_api.platform.auth import AdePrincipal, AdeRole, authenticate_ade_request

from .hindsight_runtime_support import runtime
from .hindsight_support import DATABASE_URL, engine


pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Disposable SQL not configured"
)


def test_normal_worker_private_capture_joins_saved_attempt_commit_and_paused_retry(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("ADE_SOURCE_REVISION", "f" * 40)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "true")
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "e" * 64)
    asyncio.run(_normal_capture(tmp_path))


async def _normal_capture(root):
    db = engine()
    try:
        owner, service, worker, native, transport = await runtime(db)
        worker.settings.agent_runtime_observation_root = str(root)
        worker.settings.auth_enabled = True
        worker.settings.operator_key = "controlled"
        observer = PrivateObservationService(
            database=service.database, settings=worker.settings
        )
        accepted = await service.accept_turn(
            str(owner.conversation["id"]),
            AcceptTurnRequest(
                content="实际已保存的输入",
                idempotency_key=uuid4().hex,
            ),
        )
        assert await worker.process_once()
        captured = await observer.read(accepted["run_id"])
        assert captured["run_status"] == "succeeded"
        assert len(captured["committed_assistant_message_ids"]) == 1
        assert len(captured["saved_attempts"]) == len(captured["observations"]) == 1
        records = captured["observations"][0]["records"]
        assert records[0]["type"] == "attempt_execution.started"
        assert records[-1]["value"] == {
            "status": "candidate_produced",
            "observation_incomplete": False,
        }
        assert (
            records[-1]["identity"]["attempt_id"] == captured["saved_attempts"][0]["id"]
        )
        lookup = next(
            row["value"] for row in records if row["type"] == "memory_lookup.completed"
        )
        assert lookup["response"] == {"results": []} and lookup["selected_ids"] == []
        assert native.lookups[0][1]["trace"] is True
        components = next(
            row["value"] for row in records if row["type"] == "context.composed"
        )
        assert components["messages"][-1]["content"] == "实际已保存的输入"
        assert {item["kind"] for item in components["components"]} == {
            "product_instructions",
            "persona",
            "memory_policy",
            "chat_metadata",
            "summary",
            "automatic_recall",
            "current_input",
        }

        # This is the same export route used by the collector, not a filesystem bypass.
        api = FastAPI()
        api.include_router(router)
        from types import SimpleNamespace

        api.dependency_overrides[get_agent_runtime_service] = lambda: SimpleNamespace(
            private_observations=observer
        )
        api.dependency_overrides[authenticate_ade_request] = lambda: AdePrincipal(
            AdeRole.OPERATOR, "controlled"
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api), base_url="http://fixture"
        ) as client:
            response = await client.get(
                f"/api/v3/private-observations/runs/{accepted['run_id']}"
            )
            assert response.status_code == 200 and response.json() == captured
            api.dependency_overrides[authenticate_ade_request] = lambda: AdePrincipal(
                AdeRole.READER, "controlled"
            )
            assert (
                await client.get(
                    f"/api/v3/private-observations/runs/{accepted['run_id']}"
                )
            ).status_code == 403

        foreign = PrivateObservationService(
            database=RuntimeDatabase(db, workspace_key="foreign-" + uuid4().hex),
            settings=worker.settings,
        )
        with pytest.raises(RuntimeNotFound):
            await foreign.read(accepted["run_id"])

        native.fail_recall = True
        paused = await service.accept_turn(
            str(owner.conversation["id"]),
            AcceptTurnRequest(
                content="保存后召回失败",
                idempotency_key=uuid4().hex,
            ),
        )
        assert await worker.process_once()
        failure = await observer.read(paused["run_id"])
        assert failure["run_status"] == "paused"
        assert failure["committed_assistant_message_ids"] == []
        failed_records = failure["observations"][0]["records"]
        assert any(row["type"] == "memory_lookup.failed" for row in failed_records)
        assert not any(row["type"] == "model_request.started" for row in failed_records)
        native.fail_recall = False
        await service.retry_run(
            paused["run_id"],
            RetryRunRequest(idempotency_key=uuid4().hex, expected_attempt_count=1),
        )
        assert await worker.process_once()
        retried = await observer.read(paused["run_id"])
        assert len(retried["observations"]) == len(retried["saved_attempts"]) == 2
        assert len(retried["committed_assistant_message_ids"]) == 1
        assert len(native.lookups) == 3
    finally:
        await db.dispose()
