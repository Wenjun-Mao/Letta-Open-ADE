"""Loopback-only browser mechanics fixture, never a live Memory/Character probe.

Uses the disposable application-role database and the normal product orchestration.
Both network boundaries are controlled. No credentials/provider traffic is needed.
Run with PYTHONPATH=services/ade-api/tests uv run uvicorn
agent_runtime.browser_fixture:create_app --factory --host 127.0.0.1 --port 18431.
"""

import asyncio
import copy
from contextlib import asynccontextmanager, suppress
from uuid import uuid4

from fastapi import FastAPI

from ade_api.features.agent_runtime.api import router
from ade_api.features.agent_runtime.application import AgentRuntimeApplication
from ade_api.features.agent_runtime.dependencies import get_agent_runtime_service
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.integrations.hindsight import HindsightError
from ade_api.platform.auth import AdePrincipal, AdeRole, authenticate_ade_request
from ade_api.platform.settings import AdeApiSettings

from .persistence.hindsight_runtime_support import (
    CATALOG,
    CharacterTransport,
    NativeRecallFake,
    ReadyWorker,
)
from .persistence.hindsight_support import engine
from .persistence.test_hindsight_sessions_sql import PromptRegistry


class BrowserCharacter(CharacterTransport):
    route_alias = ""

    async def catalog(self, **kwargs):
        value = copy.deepcopy(CATALOG)
        value["items"][0]["model_key"] = self.route_alias
        return value

    async def chat_completion(self, payload, **kwargs):
        value = await super().chat_completion(payload, **kwargs)
        if "response_format" not in payload:
            value["choices"][0]["message"]["content"] = (
                "这是浏览器机械检查中的受控回复，不是实时模型结果。"
            )
        return value


class BrowserMemory:
    def __init__(self, db):
        self.native = NativeRecallFake(db)
        self.available = True
        self.banks = {}

    def __getattr__(self, key):
        return getattr(self.native, key)

    async def bank_config(self, bank):
        if not self.available:
            raise HindsightError("hindsight_unavailable")
        return await self.native.bank_config(bank)

    async def submit(self, bank, *, operation_id, payload):
        self.banks[operation_id] = bank
        return await self.native.submit(
            bank, operation_id=operation_id, payload=payload
        )

    async def operation(self, bank, operation, **kwargs):
        if self.banks.get(operation) != bank:
            return {"operation_id": operation, "status": "not_found"}
        return await self.native.operation(bank, operation)

    async def operations(self, bank, *, limit, offset):
        items = [
            {"operation_id": key, "status": value, "operation_type": "retain"}
            for key, value in self.native.operations.items()
            if self.banks.get(key) == bank
        ]
        return {
            "bank_id": bank,
            "operations": items[offset : offset + limit],
            "total": len(items),
        }

    async def memories(self, bank, *, limit, offset):
        values = [
            value
            for value in self.native.documents.values()
            if value["bank_id"] == bank
        ]
        items = [
            {
                "id": value["id"],
                "text": value["original_text"],
                "context": "受控原文投影，不代表语义抽取正确",
                "fact_type": "world",
                "document_id": value["id"],
            }
            for value in values
        ]
        return {"items": items[offset : offset + limit], "total": len(items)}


def create_app():
    db = engine()  # Refuses non-loopback, non-disposable or privileged databases.
    settings = AdeApiSettings(
        _env_file=None,
        agent_runtime_mode="development",
        agent_runtime_workspace_key="browser-sql-" + uuid4().hex,
    )
    transport, native = BrowserCharacter(db), BrowserMemory(db)
    application = AgentRuntimeApplication(
        engine=db,
        settings=settings,
        prompt_registry=PromptRegistry(),
        router_transport=transport,
        hindsight_client=native,
    )
    transport.route_alias = (
        application.definitions.default_agent_studio_request().model_key
    )
    application.runs.worker_health = ReadyWorker()
    worker = AgentRuntimeWorker(
        engine=db, settings=settings, transport=transport, hindsight_client=native
    )

    async def consume():
        while True:
            await worker.process_once()
            for _ in range(3):
                await worker.delivery_worker.process_once()
            await asyncio.sleep(0.1)

    @asynccontextmanager
    async def lifespan(app):
        await application.database.ensure_ready()
        task = asyncio.create_task(consume())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            await worker.aclose()

    api = FastAPI(lifespan=lifespan)
    api.include_router(router)
    api.dependency_overrides[get_agent_runtime_service] = lambda: application
    api.dependency_overrides[authenticate_ade_request] = lambda: AdePrincipal(
        role=AdeRole.ADMIN, key_name="loopback-synthetic-fixture"
    )

    @api.get("/api/v2/prompt-center/{kind}")
    async def templates(kind: str):
        if kind not in {"prompts", "personas"}:
            return {"items": [], "total": 0}
        key = "chat_v20261019" if kind == "prompts" else "chat_linxiaotang"
        return {
            "items": [
                {
                    "key": key,
                    "label": "Controlled browser fixture",
                    "content": "Controlled original prompt"
                    if kind == "prompts"
                    else "Controlled original persona",
                }
            ],
            "total": 1,
        }

    @api.post("/__test__/memory/{available}")
    async def availability(available: bool):
        native.available = available
        native.native.fail_recall = not available
        return {"controlled_native_available": available}

    return api
