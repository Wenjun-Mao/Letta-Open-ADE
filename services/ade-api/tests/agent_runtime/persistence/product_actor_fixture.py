"""Controlled native/provider boundaries around the normal product path and real Router."""

import asyncio
import copy
from contextlib import asynccontextmanager
import json
from types import SimpleNamespace
import time
from uuid import uuid4, uuid5, NAMESPACE_URL

from fastapi import FastAPI
import httpx

from ade_api.features.agent_runtime.api import router as product_router
from ade_api.features.agent_runtime.application import AgentRuntimeApplication
from ade_api.features.agent_runtime.dependencies import get_agent_runtime_service
from ade_api.features.agent_runtime.router_transport import RouterTransport
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.platform.auth import AdePrincipal, AdeRole, authenticate_ade_request
from ade_api.platform.settings import AdeApiSettings
from content.prompts.system.chat.chat_v20261019 import PROMPT
import model_router.app as router_app
import model_router.forwarding as forwarding
import model_router.request_observations as observations
from model_router.catalog import RoutedModel
from model_router.settings import ModelRouterSettings, RouterSourceConfig
from workflows.evals.hindsight_integration.casebook import load_suite
from workflows.evals.hindsight_integration.operations import Lease, create_record
from workflows.evals.hindsight_integration.public_http import PublicRecordingTransport

from .hindsight_native_fake import NativeDeliveryFake
from .hindsight_runtime_support import CATALOG, CharacterTransport, ReadyWorker


class PublishedRegistry:
    def __init__(self, *, wrong_persona=False):
        self.wrong_persona = wrong_persona

    def get_template(self, kind, key, **kwargs):
        return {
            "key": key,
            "content": PROMPT
            if kind == "prompt"
            else load_suite()["persona"]["content"]
            + ("controlled mismatch" if self.wrong_persona else ""),
        }


class MirroringNative:
    """Echoes actual saved source bodies; it performs no semantic extraction/scoring."""

    def __init__(self, db):
        self.delivery = NativeDeliveryFake(db)
        self.operation_banks = {}

    def __getattr__(self, name):
        return getattr(self.delivery, name)

    async def aclose(self):
        pass

    def rows(self, bank):
        return [
            {
                "id": str(uuid5(NAMESPACE_URL, document["id"])),
                "text": json.loads(document["original_text"])["content"],
                "document_id": document["id"],
                "fact_type": "world",
            }
            for document in self.delivery.documents.values()
            if document["bank_id"] == bank
        ]

    async def memories(self, bank, *, limit, offset):
        await self.delivery.outside_transaction(bank)
        rows = self.rows(bank)
        return {"items": rows[offset : offset + limit], "total": len(rows)}

    async def recall(self, bank, payload):
        await self.delivery.outside_transaction(bank)
        rows = self.rows(bank)
        return {
            "results": rows,
            "trace": {
                "rrf_merged": [{"node_id": row["id"]} for row in rows],
                "reranked": [
                    {
                        "node_id": row["id"],
                        "score_components": {
                            "cross_encoder_score": 1.0,
                            "cross_encoder_score_normalized": 0.5,
                        },
                    }
                    for row in rows
                ],
                "summary": {
                    "results_returned": len(rows),
                    "phase_metrics": [
                        {
                            "phase_name": "reranking",
                            "details": {
                                "reranker_type": "cross-encoder",
                                "candidates_reranked": len(rows),
                            },
                        }
                    ],
                },
            },
        }

    async def submit(self, bank, **kwargs):
        await self.delivery.submit(bank, **kwargs)
        self.operation_banks[kwargs["operation_id"]] = bank

    async def operation(self, bank, operation, **kwargs):
        if self.operation_banks.get(operation) != bank:
            await self.delivery.outside_transaction(bank)
            return {"operation_id": operation, "status": "not_found"}
        return await self.delivery.operation(bank, operation)

    async def operations(self, bank, *, limit, offset):
        await self.delivery.outside_transaction(bank)
        rows = [
            {
                "operation_id": operation,
                "status": self.delivery.operations[operation],
                "operation_type": "batch_retain",
            }
            for operation, owner in self.operation_banks.items()
            if owner == bank
        ]
        if rows:
            rows.append(
                {
                    "operation_id": str(
                        uuid5(NAMESPACE_URL, "controlled-consolidation:" + bank)
                    ),
                    "status": "completed",
                    "operation_type": "consolidation",
                }
            )
        return {
            "bank_id": bank,
            "operations": rows[offset : offset + limit],
            "total": len(rows),
        }


@asynccontextmanager
async def actor_fixture(
    monkeypatch,
    root,
    db,
    *,
    tool_on_probe=False,
    private_tool_reasoning=False,
    wrong_persona=False,
):
    original_client = httpx.AsyncClient
    lease_root = root / "activation"
    now = int(time.time())
    lease = Lease(
        "ade-hindsight-integration-actor-test",
        str(uuid4()),
        "f" * 40,
        now - 1,
        now + 3600,
        now + 7200,
        "/mnt/projects",
        (),
    )
    lease.save(lease_root)
    create_record(
        lease_root / "checks/001.json",
        {
            "time": time.time(),
            "issues": [],
            "activation_id": lease.activation_id,
            "source_revision": lease.source_revision,
        },
    )
    source = RouterSourceConfig(
        id="fake",
        label="Controlled",
        base_url="https://provider.invalid",
        enabled_for=["agent_studio"],
    )
    model = RoutedModel(
        router_model_id="fake::character",
        source_id="fake",
        source_label="Controlled",
        source_kind="openai-compatible",
        source_adapter="openai_compatible",
        source_base_url=source.base_url,
        module_visibility=("agent_studio",),
        provider_model_id="character",
        model_type="llm",
        agent_studio_available=True,
        comment_lab_available=False,
        label_lab_available=False,
        structured_output_mode="json_schema",
    )
    router_settings = ModelRouterSettings(
        _env_file=None,
        sources=[source],
        api_key="controlled-router",
        api_key_secret="",
        observation_root=str(root / "router-observations"),
        activation_root=str(lease_root),
    )
    monkeypatch.setattr(router_app, "get_settings", lambda: router_settings)
    monkeypatch.setattr(forwarding, "get_settings", lambda: router_settings)
    monkeypatch.setattr(observations, "get_settings", lambda: router_settings)
    monkeypatch.setattr(
        router_app,
        "catalog_service",
        SimpleNamespace(
            find_routed_model=lambda value: model, source_config=lambda value: source
        ),
    )
    monkeypatch.setattr(
        router_app, "_catalog_payload", lambda **kw: copy.deepcopy(CATALOG)
    )

    async def local_router(request):
        async with original_client(
            transport=httpx.ASGITransport(app=router_app.app)
        ) as client:
            return await client.send(request)

    class LocalClient(original_client):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("transport", httpx.MockTransport(local_router))
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", LocalClient)
    calls = []

    def provider(request):
        body = json.loads(request.content)
        calls.append(body)
        is_probe = body["messages"][1].get("content") in {
            case.prompt for case in load_suite()["cases"].values()
        }
        has_tool = any(message["role"] == "tool" for message in body["messages"])
        message = {
            "role": "assistant",
            "content": "Controlled recording-provider response",
        }
        if tool_on_probe and is_probe and not has_tool:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-controlled",
                        "type": "function",
                        "function": {
                            "name": "search_memory",
                            "arguments": '{"query":"controlled query"}',
                        },
                    }
                ],
            }
            if private_tool_reasoning:
                message["reasoning_content"] = "PRIVATE-THINKING-SECRET"
        return httpx.Response(
            200,
            json={
                "id": "controlled-" + str(len(calls)),
                "choices": [
                    {
                        "index": 0,
                        "message": message,
                        "finish_reason": "tool_calls"
                        if message.get("tool_calls")
                        else "stop",
                    }
                ],
            },
        )

    native = MirroringNative(db)
    app_settings = AdeApiSettings(
        _env_file=None,
        auth_enabled=True,
        operator_key="controlled-api",
        agent_runtime_mode="development",
        agent_runtime_workspace_key="actor-sql-" + uuid4().hex,
        agent_runtime_observation_root=str(root / "product-observations"),
        agent_runtime_worker_poll_seconds=0.02,
    )
    (root / "product-observations").mkdir(mode=0o700)
    application = AgentRuntimeApplication(
        engine=db,
        settings=app_settings,
        prompt_registry=PublishedRegistry(wrong_persona=wrong_persona),
        router_transport=CharacterTransport(db),
        hindsight_client=native,
    )
    application.runs.worker_health = ReadyWorker()
    api = FastAPI()
    api.include_router(product_router)
    api.dependency_overrides[get_agent_runtime_service] = lambda: application
    api.dependency_overrides[authenticate_ade_request] = lambda: AdePrincipal(
        AdeRole.OPERATOR, "controlled"
    )
    worker = AgentRuntimeWorker(
        engine=db,
        settings=app_settings,
        transport=RouterTransport("http://router/v1", "controlled-router"),
        hindsight_client=native,
    )
    worker.delivery_worker.poll_seconds = 0.02
    stop = asyncio.Event()
    async with LocalClient(transport=httpx.MockTransport(provider)) as upstream:
        monkeypatch.setattr(
            router_app.app.state, "upstream_client", upstream, raising=False
        )
        task = asyncio.create_task(worker.run_forever(stop))

        def transport_factory(path):
            app = api if path.name == "api-http" else router_app.app
            return PublicRecordingTransport(path, inner=httpx.ASGITransport(app=app))

        try:
            yield SimpleNamespace(
                application=application,
                worker=worker,
                native=native,
                source={
                    "source_revision": lease.source_revision,
                    "source_fingerprint": "e" * 64,
                    "source_dirty": "false",
                    "activation_id": lease.activation_id,
                },
                transport_factory=transport_factory,
                calls=calls,
            )
        finally:
            stop.set()
            await asyncio.wait_for(task, timeout=10)
            await worker.aclose()
            await application.aclose()
