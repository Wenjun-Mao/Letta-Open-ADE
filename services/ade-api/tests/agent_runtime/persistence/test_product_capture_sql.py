"""Normal ADE worker -> real Router -> recording provider -> public collector.

SQL/HTTP/capture mechanics only; native Memory and provider outputs are controlled.
"""

import asyncio
import copy
import json
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
import httpx
import pytest

from ade_api.features.agent_runtime.api import router as product_router
from ade_api.features.agent_runtime.application import AgentRuntimeApplication
from ade_api.features.agent_runtime.dependencies import get_agent_runtime_service
from ade_api.features.agent_runtime.router_transport import RouterTransport
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.platform.auth import AdePrincipal, AdeRole, authenticate_ade_request
from ade_api.platform.settings import AdeApiSettings
import model_router.app as router_app
import model_router.forwarding as forwarding
import model_router.request_observations as observations
from model_router.catalog import RoutedModel
from model_router.settings import ModelRouterSettings, RouterSourceConfig
from workflows.evals.hindsight_integration.product_capture import collect_saved_run
from workflows.evals.hindsight_integration.capture_validation import qualify_run_capture

from .hindsight_runtime_support import (
    CATALOG,
    CharacterTransport,
    NativeRecallFake,
    ReadyWorker,
)
from .hindsight_support import DATABASE_URL, engine
from .test_hindsight_sessions_sql import PromptRegistry


pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Disposable SQL not configured"
)


def test_actual_product_capture_public_joins_and_tool_continuation_reject_corruption(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("ADE_SOURCE_REVISION", "f" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "e" * 64)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "false")
    asyncio.run(_capture(monkeypatch, tmp_path))


async def _capture(monkeypatch, root):
    original_client = httpx.AsyncClient
    source = RouterSourceConfig(
        id="fake",
        label="Controlled provider",
        base_url="https://provider.invalid",
        enabled_for=["agent_studio"],
    )
    model = RoutedModel(
        router_model_id="fake::character",
        source_id="fake",
        source_label="Controlled provider",
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
    settings = ModelRouterSettings(
        _env_file=None,
        sources=[source],
        api_key="controlled-key",
        api_key_secret="",
        observation_root=str(root / "router"),
    )
    monkeypatch.setattr(router_app, "get_settings", lambda: settings)
    monkeypatch.setattr(forwarding, "get_settings", lambda: settings)
    monkeypatch.setattr(observations, "get_settings", lambda: settings)
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
        def __init__(self, *args, **kw):
            kw.setdefault("transport", httpx.MockTransport(local_router))
            super().__init__(*args, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", LocalClient)
    sent = []

    def provider(request):
        sent.append(request.content)
        tool = {
            "id": "call-a",
            "type": "function",
            "function": {"name": "search_memory", "arguments": '{"query":"先前"}'},
        }
        message = {
            "role": "assistant",
            "content": "受控回复",
            "reasoning_content": "PRIVATE-REASONING-EXCLUDED",
        }
        if len(sent) == 1:
            message = {"role": "assistant", "content": None, "tool_calls": [tool]}
        return httpx.Response(
            200,
            json={
                "id": f"controlled-{len(sent)}",
                "choices": [
                    {
                        "index": 0,
                        "message": message,
                        "finish_reason": "tool_calls" if len(sent) == 1 else "stop",
                    }
                ],
            },
        )

    db = engine()
    async with LocalClient(transport=httpx.MockTransport(provider)) as upstream:
        monkeypatch.setattr(
            router_app.app.state, "upstream_client", upstream, raising=False
        )
        app_settings = AdeApiSettings(
            _env_file=None,
            auth_enabled=True,
            agent_runtime_mode="development",
            agent_runtime_workspace_key="capture-sql-" + uuid4().hex,
            agent_runtime_observation_root=str(root / "ade"),
            operator_key="controlled",
        )
        native = NativeRecallFake(db)
        application = AgentRuntimeApplication(
            engine=db,
            settings=app_settings,
            prompt_registry=PromptRegistry(),
            router_transport=CharacterTransport(db),
            hindsight_client=native,
        )
        application.runs.worker_health = ReadyWorker()
        app = FastAPI()
        app.include_router(product_router)
        app.dependency_overrides[get_agent_runtime_service] = lambda: application
        app.dependency_overrides[authenticate_ade_request] = lambda: AdePrincipal(
            AdeRole.OPERATOR, "controlled"
        )
        transport = RouterTransport("http://router/v1", "controlled-key")
        worker = AgentRuntimeWorker(
            engine=db,
            settings=app_settings,
            transport=transport,
            hindsight_client=native,
        )
        try:
            async with (
                original_client(
                    transport=httpx.ASGITransport(app=app), base_url="http://ade"
                ) as api,
                original_client(
                    transport=httpx.ASGITransport(app=router_app.app),
                    base_url="http://router",
                    headers={"Authorization": "Bearer controlled-key"},
                ) as wire_api,
            ):
                response = await api.post(
                    "/api/v3/evaluation-sessions",
                    json={
                        "idempotency_key": uuid4().hex,
                        "model_key": "fake::character",
                        "compaction_model_key": "fake::character",
                    },
                )
                assert response.status_code == 201, response.text
                session = response.json()
                conversation_id = session["conversation"]["id"]
                response = await api.post(
                    f"/api/v3/conversations/{conversation_id}/turns",
                    json={
                        "idempotency_key": uuid4().hex,
                        "content": "真实已保存的受控输入",
                    },
                )
                assert response.status_code == 202, response.text
                run_id = response.json()["run_id"]
                assert await worker.process_once()
                scope = {
                    "workspace_id": application.database.workspace_id,
                    "subject_id": session["memory_subject"]["id"],
                    "character_root_id": session["agent_definition"][
                        "agent_definition_id"
                    ],
                }
                source_binding = {
                    "source_revision": "f" * 40,
                    "source_fingerprint": "e" * 64,
                    "source_dirty": "false",
                }
                bundle, result = await collect_saved_run(
                    api=api,
                    router=wire_api,
                    run_id=run_id,
                    phase="probe",
                    state_path=f"/api/v3/evaluation-sessions/{conversation_id}/state",
                    scope=scope,
                    source=source_binding,
                    expected_input="真实已保存的受控输入",
                    fresh_probe=True,
                    out=root / "collected",
                )
                assert len(result["requests"]) == len(sent) == 2
                assert result["reply"] == "受控回复"
                assert [
                    item["request"]["raw_body_utf8"].encode()
                    for item in bundle["wires"]
                ] == sent
                assert any(
                    part["kind"] == "tool_recall"
                    for part in result["requests"][-1]["components"]
                )
                assert "PRIVATE-REASONING-EXCLUDED" not in json.dumps(bundle)
                for mutation in (
                    "missing_continuation",
                    "wrong_run",
                    "wrong_body",
                    "wrong_reply",
                    "extra_local_history",
                    "missing_attempt",
                    "changed_component",
                ):
                    altered = copy.deepcopy(bundle)
                    match mutation:
                        case "missing_continuation":
                            altered["wires"].pop()
                        case "wrong_run":
                            altered["wires"][0]["request"]["metadata"]["run_id"] = str(
                                uuid4()
                            )
                        case "wrong_body":
                            altered["wires"][0]["request"]["body"]["messages"] = []
                        case "wrong_reply":
                            altered["state"]["conversation"]["messages"][-1][
                                "content"
                            ] = "Not the actual provider reply"
                        case "extra_local_history":
                            for row in altered["export"]["observations"][0]["records"]:
                                if row["type"] == "context.sources":
                                    row["value"]["summary"] = {
                                        "content": "copied source"
                                    }
                        case "missing_attempt":
                            altered["export"]["observations"] = []
                        case "changed_component":
                            for row in altered["export"]["observations"][0]["records"]:
                                if row["type"] == "context.composed":
                                    row["value"]["components"][0]["sha256"] = "0" * 64
                    with pytest.raises(ValueError):
                        qualify_run_capture(
                            run=altered["run"],
                            export=altered["export"],
                            state=altered["state"]["conversation"],
                            wires=altered["wires"],
                            events=altered["events"],
                            scope=scope,
                            source=source_binding,
                            expected_input="真实已保存的受控输入",
                            fresh_probe=True,
                        )
        finally:
            await application.aclose()
