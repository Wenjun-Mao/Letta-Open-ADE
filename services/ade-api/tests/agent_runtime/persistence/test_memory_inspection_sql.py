"""Public inspection with real least-privilege SQL and recording native HTTP."""

import asyncio
import json
from uuid import uuid4

from fastapi import FastAPI
import httpx
import pytest
from sqlalchemy import select, update

from ade_api.features.agent_runtime.api import router
from ade_api.features.agent_runtime.application import AgentRuntimeApplication
from ade_api.features.agent_runtime.dependencies import get_agent_runtime_service
from ade_api.features.agent_runtime.persistence.metadata import memory_deliveries
from ade_api.integrations.hindsight import HindsightError
from ade_api.platform.auth import AdePrincipal, AdeRole, authenticate_ade_request
from ade_api.platform.settings import AdeApiSettings

from .hindsight_native_fake import NativeDeliveryFake
from .hindsight_runtime_support import CharacterTransport, ReadyWorker
from .hindsight_support import DATABASE_URL, engine
from .test_hindsight_sessions_sql import PromptRegistry


pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Disposable SQL not configured"
)


class NativeInspectionFake(NativeDeliveryFake):
    def __init__(self, db):
        super().__init__(db)
        del self.operations
        self.available = True
        self.reads = []
        self.rows = {}
        self.operation_rows = {}

    async def bank_config(self, bank):
        self.reads.append(bank)
        if not self.available:
            raise HindsightError("hindsight_unavailable")
        return await super().bank_config(bank)

    async def memories(self, bank, *, limit, offset):
        await self.outside_transaction(bank)
        return {
            "items": self.rows.get(bank, [])[offset : offset + limit],
            "total": len(self.rows.get(bank, [])),
        }

    async def operations(self, bank, *, limit, offset):
        await self.outside_transaction(bank)
        items = list(self.operation_rows.get(bank, {}).values())
        return {
            "bank_id": bank,
            "operations": items[offset : offset + limit],
            "total": len(items),
        }

    async def operation(self, bank, operation, *, include_payload=True):
        assert include_payload is False
        await self.outside_transaction(bank)
        return self.operation_rows.get(bank, {}).get(
            operation, {"operation_id": operation, "status": "not_found"}
        )


def test_relationship_inspection_scope_outage_source_progress_and_retry():
    asyncio.run(_inspection())


async def _inspection():
    db = engine()
    native = NativeInspectionFake(db)
    application = AgentRuntimeApplication(
        engine=db,
        settings=AdeApiSettings(
            _env_file=None,
            agent_runtime_mode="development",
            agent_runtime_workspace_key="inspection-" + uuid4().hex,
        ),
        prompt_registry=PromptRegistry(),
        router_transport=CharacterTransport(db),
        hindsight_client=native,
    )
    application.runs.worker_health = ReadyWorker()
    api = FastAPI()
    api.include_router(router)
    api.dependency_overrides[get_agent_runtime_service] = lambda: application
    api.dependency_overrides[authenticate_ade_request] = lambda: AdePrincipal(
        role=AdeRole.ADMIN, key_name="synthetic"
    )
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api), base_url="http://controlled"
        ) as client:
            saved = (
                await client.post(
                    "/api/v3/evaluation-sessions",
                    json={
                        "idempotency_key": uuid4().hex,
                        "model_key": "fake::character",
                        "compaction_model_key": "fake::character",
                    },
                )
            ).json()
            subject = saved["memory_subject"]["id"]
            root = saved["agent_definition"]["agent_definition_id"]
            base = f"/api/v3/memory/subjects/{subject}/characters/{root}"
            assert (await client.get(base + "/memories")).json()["items"] == []
            assert len(native.creations) == 1
            accepted = await client.post(
                f"/api/v3/conversations/{saved['conversation']['id']}/turns",
                json={"content": "我每周三练习书法。", "idempotency_key": uuid4().hex},
            )
            assert accepted.status_code == 202, accepted.text
            async with db.connect() as connection:
                delivery = dict(
                    (
                        await connection.execute(
                            select(memory_deliveries).where(
                                memory_deliveries.c.workspace_id
                                == application.database.workspace_id
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
            bank = delivery["bank_id"]
            operation = str(delivery["operation_id"])
            document = delivery["document_id"]
            item = json.loads(bytes(delivery["payload"]))["items"][0]
            native.documents[document] = {
                "id": document,
                "bank_id": bank,
                "original_text": item["content"],
                "retain_params": {"context": item["context"]},
            }
            native.rows[bank] = [
                {
                    "id": str(uuid4()),
                    "text": "用户每周三练习书法。",
                    "context": "用户陈述",
                    "fact_type": "world",
                    "document_id": document,
                    "provider_secret": "never-public",
                }
            ]
            native.operation_rows[bank] = {
                operation: {
                    "operation_id": operation,
                    "status": "failed",
                    "error_message": "never-public",
                    "task_payload": {"secret": "never-public"},
                    "progress": {
                        "processed": 1,
                        "total": 15,
                        "detail": {"secret": "never-public"},
                    },
                }
            }
            memories = await client.get(base + "/memories")
            assert memories.status_code == 200, memories.text
            assert "never-public" not in memories.text
            source = await client.get(base + f"/sources/{document}")
            assert source.status_code == 200, source.text
            assert source.json()["content"] == "我每周三练习书法。"
            assert (
                source.json()["definition_version_id"]
                == saved["agent_definition"]["id"]
            )
            operations = await client.get(base + "/operations")
            assert operations.status_code == 200, operations.text
            assert "never-public" not in operations.text
            assert (
                await client.get(base + "/operations", params={"limit": 200})
            ).status_code == 422
            assert (
                await client.get(base + f"/operations/{uuid4()}")
            ).status_code == 404
            assert (
                await client.get(base + f"/operations/{operation}")
            ).status_code == 200
            async with db.begin() as connection:
                await connection.execute(
                    update(memory_deliveries)
                    .where(memory_deliveries.c.operation_id == operation)
                    .values(
                        status="uncertain",
                        check_count=5,
                        consecutive_errors=5,
                        native_progress=native.operation_rows[bank][operation],
                    )
                )
            native.available = False
            assert (await client.get(base + "/memories")).status_code == 503
            assert (
                await client.get(
                    f"/api/v3/evaluation-sessions/{saved['conversation']['id']}/state"
                )
            ).status_code == 200
            queue = await client.get(base + "/deliveries")
            assert queue.status_code == 200, queue.text
            assert queue.json()["counts"] == {"uncertain": 1}
            assert queue.json()["blocked_operation_id"] == operation
            assert "never-public" not in queue.text
            assert queue.json()["items"][0]["accepted_at"] is None
            assert queue.json()["items"][0]["retained_at"] is None
            retry = await client.post(
                base + f"/deliveries/{operation}/retry",
                json={"expected_check_count": 4},
            )
            assert retry.status_code == 409
            retry = await client.post(
                base + f"/deliveries/{operation}/retry",
                json={"expected_check_count": 5},
            )
            assert retry.status_code == 200, retry.text
            assert retry.json()["status"] == "queued"
            assert retry.json()["retry_requested"] is True
            assert (
                await client.post(
                    base + f"/deliveries/{uuid4()}/retry",
                    json={"expected_check_count": 0},
                )
            ).status_code == 404
            native.available = True
            native.corrupt_document = True
            assert (await client.get(base + f"/sources/{document}")).status_code == 503
            # Both a foreign workspace pair and mixed legitimate relationship IDs
            # must fail before a native request, not merely hide the result later.
            other = (
                await client.post(
                    "/api/v3/evaluation-sessions",
                    json={
                        "idempotency_key": uuid4().hex,
                        "model_key": "fake::character",
                        "compaction_model_key": "fake::character",
                    },
                )
            ).json()
            mixed = f"/api/v3/memory/subjects/{subject}/characters/{other['agent_definition']['agent_definition_id']}"
            calls = len(native.reads)
            assert (await client.get(mixed + "/memories")).status_code == 404
            assert len(native.reads) == calls
            foreign = f"/api/v3/memory/subjects/{other['memory_subject']['id']}/characters/{other['agent_definition']['agent_definition_id']}"
            assert (
                await client.get(foreign + f"/sources/{document}")
            ).status_code == 404
            assert (
                await client.get(foreign + f"/operations/{operation}")
            ).status_code == 404
            foreign_application = AgentRuntimeApplication(
                engine=db,
                settings=AdeApiSettings(
                    _env_file=None,
                    agent_runtime_mode="development",
                    agent_runtime_workspace_key="foreign-inspection-" + uuid4().hex,
                ),
                prompt_registry=PromptRegistry(),
                router_transport=CharacterTransport(db),
                hindsight_client=native,
            )
            api.dependency_overrides[get_agent_runtime_service] = lambda: (
                foreign_application
            )
            calls = len(native.reads)
            for suffix in (
                "/deliveries",
                "/memories",
                f"/sources/{document}",
                f"/operations/{operation}",
            ):
                assert (await client.get(base + suffix)).status_code == 404
            assert len(native.reads) == calls
            api.dependency_overrides[get_agent_runtime_service] = lambda: application
            api.dependency_overrides[authenticate_ade_request] = lambda: AdePrincipal(
                role=AdeRole.READER, key_name="reader"
            )
            assert (
                await client.post(
                    base + f"/deliveries/{operation}/retry",
                    json={"expected_check_count": 5},
                )
            ).status_code == 403
            assert native.network_checks > 0
    finally:
        await db.dispose()
