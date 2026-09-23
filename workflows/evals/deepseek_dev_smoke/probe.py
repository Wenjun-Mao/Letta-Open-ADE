"""Bounded, synthetic DeepSeek development probes through the real Model Router."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import socket
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import uvicorn
from dotenv import dotenv_values
from sqlalchemy import text as sql_text
from sqlalchemy.engine import make_url

import model_router.app as router_app
import model_router.forwarding as forwarding
from model_router.catalog import RouterCatalogService
from model_router.settings import ModelRouterSettings, RouterSourceConfig

from ade_api.features.agent_runtime.executor import ConversationExecutor, curated_tools
from ade_api.features.agent_runtime.agent_studio_sessions import (
    AgentStudioSessionService,
)
from ade_api.features.agent_runtime.contracts import (
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
)
from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.definition_service import DefinitionService
from ade_api.features.agent_runtime.memory_policy import prepare_memory_review
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.reviewer import MemoryReviewer
from ade_api.features.agent_runtime.router_transport import RouterTransport
from ade_api.features.agent_runtime.tool_policy import ToolRequirement
from ade_api.features.comment_lab.service import CommentingService
from ade_api.features.label_lab.helpers import football_label_output_schema
from ade_api.features.label_lab.service import LabelingService
from ade_api.features.prompt_center import build_prompt_template_reader
from ade_api.platform.settings import AdeApiSettings

from native_turn import run_native_turn


ROOT = Path(__file__).resolve().parents[3]
MODEL = "deepseek::deepseek-flash"
SUBJECT_ID = "00000000-0000-0000-0000-000000000001"


class CountedRouter:
    def __init__(self, inner: RouterTransport, *, limit: int) -> None:
        self.inner = inner
        self.limit = limit
        self.count = 0
        self.reasoning_replayed = False
        self.reasoning_received = False

    async def chat_completion(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        if self.count >= self.limit:
            raise RuntimeError("Synthetic probe request reservation exhausted")
        self.count += 1  # Reserve before the network call, including failure.
        self.reasoning_replayed |= any(
            isinstance(message, dict) and bool(message.get("reasoning_content"))
            for message in payload.get("messages", [])
        )
        response = await self.inner.chat_completion(
            payload, timeout_seconds=min(timeout_seconds, 180.0)
        )
        self.reasoning_received |= any(
            isinstance(choice, dict)
            and isinstance(choice.get("message"), dict)
            and bool(choice["message"].get("reasoning_content"))
            for choice in response.get("choices", [])
        )
        return response


def _settings(env_file: Path, *, include_spark: bool) -> ModelRouterSettings:
    values = dotenv_values(env_file)
    key = str(values.get("DEEPSEEK_API_KEY") or "").strip()
    base = str(values.get("DEEPSEEK_API_BASE") or "https://api.deepseek.com").strip()
    parsed = urlsplit(base)
    if not key or parsed.scheme != "https" or parsed.hostname != "api.deepseek.com":
        raise ValueError("Official DeepSeek key/base URL is not configured")
    os.environ["DEEPSEEK_API_KEY"] = key
    os.environ["DEEPSEEK_API_BASE"] = base
    sources = json.loads((ROOT / "config/model-router/sources.json").read_text())
    selected = [next(item for item in sources if item["id"] == "deepseek")]
    if include_spark:
        host = str(values.get("DGX_SPARK_HOST") or "").strip()
        if not host or "/" in host or "@" in host:
            raise ValueError("Spark host is not configured for isolated binding")
        embedding_key = str(values.get("DGX_EMBEDDING_API_KEY") or "").strip()
        if embedding_key:
            os.environ["DGX_EMBEDDING_API_KEY"] = embedding_key
        spark = next(item for item in sources if item["id"] == "dgx_embedding_sidecar")
        selected.append({**spark, "base_url": f"http://{host}:8001/v1"})
    return ModelRouterSettings(
        sources=[RouterSourceConfig.model_validate(item) for item in selected],
        api_key="",
        api_key_secret="",
        request_timeout_seconds=180,
    )


async def _run_tool(transport: RouterTransport) -> None:
    counted = CountedRouter(transport, limit=2)

    async def synthetic_search(query: str, limit: int) -> list[dict[str, Any]]:
        return [{"fact_type": "person.preference", "value": "oolong tea"}]

    try:
        result = await ConversationExecutor(
            counted, provider_adapter="deepseek_openai"
        ).execute(
            model_key=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "This is a synthetic ADE memory test. For an explicit older-memory "
                        "search request, call the supplied search_memory tool before answering."
                    ),
                },
                {
                    "role": "user",
                    "content": "Search my older memory for my favorite tea. What did you find?",
                },
            ],
            tools=curated_tools(("search_memory",), search_memory=synthetic_search),
            tool_requirement=ToolRequirement(
                tool_name="search_memory", capability="memory.deep_search"
            ),
            timeout_seconds=180,
            max_output_tokens=2048,
            max_model_requests=2,
        )
        print(
            json.dumps(
                {
                    "requests": counted.count,
                    "required_tool_satisfied": result.tool_requirement_satisfied,
                    "tool_events": len(result.tool_events),
                    "reasoning_received": counted.reasoning_received,
                    "reasoning_replayed": counted.reasoning_replayed,
                    "answer": result.assistant_text,
                    "usage": result.usage,
                },
                ensure_ascii=False,
            )
        )
    except Exception as exc:
        print(
            json.dumps({"requests": counted.count, "failure_type": type(exc).__name__})
        )
        raise


async def _run_reviewer(transport: RouterTransport) -> None:
    counted = CountedRouter(transport, limit=1)
    fact_id = "00000000-0000-0000-0000-000000000003"
    message = {"id": "message-1", "content": "Please forget that I like blue."}
    facts = [
        {
            "id": fact_id,
            "subject_id": SUBJECT_ID,
            "entity_id": SUBJECT_ID,
            "normalized_key": f"person.preference|{SUBJECT_ID}|color",
            "fact_type": "person.preference",
            "qualifier": "color",
            "value": "blue",
            "status": "active",
            "version": 2,
        }
    ]
    entities = [
        {"id": SUBJECT_ID, "subject_id": SUBJECT_ID, "kind": "subject", "label": ""}
    ]
    try:
        result = await MemoryReviewer(
            counted, provider_adapter="deepseek_openai"
        ).review(
            model_key=MODEL,
            current_user_message=message,
            recent_user_messages=[],
            active_facts=facts,
            entities=entities,
            timeout_seconds=180,
            max_model_requests=1,
            validate_decision=lambda decision: prepare_memory_review(
                decision=decision,
                subject_id=SUBJECT_ID,
                current_user_message=message,
                active_facts=facts,
                entities=entities,
            ),
        )
        proposal = result.decision.proposals[0] if result.decision.proposals else None
        print(
            json.dumps(
                {
                    "requests": counted.count,
                    "proposal_count": len(result.decision.proposals),
                    "operation": getattr(proposal, "operation", None),
                    "fact_id_matches": getattr(proposal, "fact_id", None) == fact_id,
                    "expected_version": getattr(proposal, "expected_version", None),
                    "value_is_null": getattr(proposal, "value", "missing") is None,
                    "reasoning_received": counted.reasoning_received,
                    "usage": result.usage,
                }
            )
        )
    except Exception as exc:
        print(
            json.dumps({"requests": counted.count, "failure_type": type(exc).__name__})
        )
        raise


def _lab_settings() -> SimpleNamespace:
    return SimpleNamespace(
        comment_lab_max_tokens=2048,
        comment_lab_timeout_seconds=180,
        comment_lab_task_shape="structured_output",
        comment_lab_cache_prompt=False,
        comment_lab_temperature=0.6,
        comment_lab_top_p=1.0,
        comment_lab_top_k=None,
        label_lab_max_tokens=2048,
        label_lab_timeout_seconds=180,
        label_lab_repair_retry_count=0,
        label_lab_temperature=0.0,
        label_lab_top_p=1.0,
        label_lab_top_k=None,
    )


async def _run_lab(mode: str, base_url: str) -> None:
    if mode == "comment":
        result = await asyncio.to_thread(
            CommentingService(settings_factory=_lab_settings).generate_comment,
            base_url=base_url,
            model=MODEL,
            source_adapter="deepseek_openai",
            system_prompt="Write one friendly Chinese community comment. Return JSON only.",
            persona_prompt="You are a friendly neighbor.",
            news_input="合成消息：社区图书馆周六开放。",
            max_tokens=2048,
            timeout_seconds=180,
            retry_count=0,
            task_shape="structured_output",
            enable_thinking=True,
        )
        print(
            json.dumps(
                {
                    "requests": 1,
                    "content": result["content"],
                    "source": result["content_source"],
                    "reasoning_exposed": "reasoning_content"
                    in json.dumps(result["raw_reply"]),
                    "usage": result["usage"],
                },
                ensure_ascii=False,
            )
        )
    else:
        result = await asyncio.to_thread(
            LabelingService(settings_factory=_lab_settings).generate_labels,
            base_url=base_url,
            model=MODEL,
            source_adapter="deepseek_openai",
            system_prompt="Extract exact player and team names. Return JSON only.",
            article_input="Messi scored for Inter Miami against Orlando City.",
            output_mode="json_object",
            output_schema_raw=json.dumps(football_label_output_schema()),
            max_tokens=2048,
            timeout_seconds=180,
            repair_retry_count=0,
        )
        print(
            json.dumps(
                {
                    "requests": 1,
                    "result": result["result"],
                    "selected_attempt": result["selected_attempt"],
                    "reasoning_exposed": "reasoning_content"
                    in json.dumps(result["raw_reply"]),
                    "usage": result["usage"],
                },
                ensure_ascii=False,
            )
        )


def _isolated_database_url(database_url: str) -> tuple[str, str]:
    url = make_url(database_url)
    if (
        url.drivername != "postgresql+psycopg"
        or url.host not in {"localhost", "127.0.0.1", "::1"}
        or url.username != "ade_owner"
        or url.password is not None
        or not re.fullmatch(r"ade_m2_memory_test_[0-9a-f]{8,}", url.database or "")
    ):
        raise ValueError(
            "Binding requires the disposable passwordless loopback test DB"
        )
    return database_url, str(url.database)


async def _run_bind(transport: RouterTransport, database_url: str) -> None:
    checked_url, expected_name = _isolated_database_url(database_url)
    engine = create_persistence_engine(checked_url)
    try:
        async with engine.connect() as connection:
            actual_name = await connection.scalar(sql_text("SELECT current_database()"))
            actual_role = await connection.scalar(sql_text("SELECT current_user"))
        if actual_name != expected_name or actual_role != "ade_owner":
            raise ValueError(
                "Connected database identity did not match isolation guard"
            )
        database = RuntimeDatabase(engine)
        await database.ensure_ready()
        with tempfile.TemporaryDirectory(prefix="ade-deepseek-probe-") as temp_dir:
            prompt_registry = build_prompt_template_reader(
                ROOT,
                persona_db_path=Path(temp_dir) / "personas.sqlite3",
            )
            definitions = DefinitionService(
                database=database,
                settings=AdeApiSettings(
                    agent_runtime_enabled=True,
                    agent_runtime_mode="development",
                    model_discovery_timeout_seconds=30,
                    database_url=checked_url,
                ),
                prompt_registry=prompt_registry,
                router_transport=transport,
            )
            default_request = definitions.default_agent_studio_request()
            token = uuid4().hex[:12]
            request = CreateAgentStudioSessionRequest(
                idempotency_key=f"deepseek-synthetic-{token}",
                title="Synthetic DeepSeek development binding",
                new_definition=default_request.model_copy(
                    update={"definition_key": f"deepseek_synthetic_{token}"}
                ),
                new_subject=CreateMemorySubjectRequest(
                    external_key=f"deepseek-synthetic-{token}",
                    display_name="Synthetic test user",
                ),
            )
            session = await AgentStudioSessionService(
                database=database, definitions=definitions
            ).create(request)
            binding = session["agent_definition"]
            print(
                json.dumps(
                    {
                        "database": expected_name,
                        "conversation_id": session["conversation"]["id"],
                        "subject_id": session["memory_subject"]["id"],
                        "purpose": session["conversation"]["purpose"],
                        "qualification_state": binding["qualification_state"],
                        "deployments": [
                            {
                                "role": item["role"],
                                "route_alias": item["route_alias"],
                                "qualification_state": item["qualification_state"],
                            }
                            for item in binding["deployments"]
                        ],
                    }
                )
            )
    finally:
        await engine.dispose()


async def main(mode: str, env_file: Path, database_url: str | None) -> None:
    settings = _settings(env_file, include_spark=mode in {"bind", "native"})
    router_app.get_settings = lambda: settings
    router_app.catalog_service = RouterCatalogService(settings_factory=lambda: settings)
    forwarding.get_settings = lambda: settings
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(router_app.app, log_level="critical", access_log=False)
    )
    server_task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        for _ in range(200):
            if server.started:
                break
            if server_task.done():
                raise RuntimeError("Synthetic Model Router did not start")
            await asyncio.sleep(0.05)
        else:
            raise RuntimeError("Synthetic Model Router startup timed out")
        base_url = f"http://127.0.0.1:{port}/v1"
        transport = RouterTransport(base_url=base_url)
        if mode == "tool":
            await _run_tool(transport)
        elif mode == "reviewer":
            await _run_reviewer(transport)
        elif mode == "bind":
            if not database_url:
                raise ValueError("Binding requires --database-url")
            await _run_bind(transport, database_url)
        elif mode == "native":
            if not database_url:
                raise ValueError("Native turn requires --database-url")
            checked_url, expected_name = _isolated_database_url(database_url)
            await run_native_turn(
                transport,
                database_url=checked_url,
                database_name=expected_name,
                root=ROOT,
            )
        else:
            await _run_lab(mode, base_url)
    finally:
        server.should_exit = True
        await server_task


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("tool", "reviewer", "comment", "label", "bind", "native")
    )
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--database-url")
    args = parser.parse_args()
    asyncio.run(main(args.mode, args.env_file, args.database_url))
