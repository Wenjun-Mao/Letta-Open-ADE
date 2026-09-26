"""Real definition snapshots retain explicit old and candidate prompt bindings."""

from __future__ import annotations

import asyncio
import hashlib
import os
from uuid import uuid4

import pytest
from sqlalchemy import select

from ade_api.features.agent_runtime.agent_studio_sessions import PurposeSessionService
from ade_api.features.agent_runtime.contracts import (
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
)
from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.definition_service import DefinitionService
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    agent_definition_versions,
    conversations,
)
from ade_api.features.prompt_center import build_prompt_template_reader
from ade_api.platform.settings import AdeApiSettings
from workflows.evals.deepseek_dev_smoke.isolation import ROOT


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="disposable PostgreSQL required"
)


def test_old_and_candidate_definitions_keep_independent_prompt_snapshots(
    tmp_path, natural_worker_support
) -> None:
    asyncio.run(_exercise(tmp_path, natural_worker_support))


async def _exercise(tmp_path, support) -> None:
    assert DATABASE_URL is not None
    engine = create_persistence_engine(DATABASE_URL)
    registry = build_prompt_template_reader(
        ROOT, persona_db_path=tmp_path / "personas.sqlite3"
    )
    catalog = support.catalog()
    definitions = DefinitionService(
        database=RuntimeDatabase(engine),
        settings=AdeApiSettings(
            _env_file=None,
            agent_runtime_enabled=True,
            agent_runtime_mode="development",
            database_url=DATABASE_URL,
        ),
        prompt_registry=registry,
        router_transport=support.transport(catalog),
    )
    sessions = PurposeSessionService(
        database=RuntimeDatabase(engine),
        definitions=definitions,
        purpose="evaluation",
        session_namespace="generation-candidate-test",
    )
    token = uuid4().hex[:12]
    records = {}
    try:
        assert definitions.default_agent_studio_request().prompt_key == "chat_v20260516"
        for key in ("chat_v20260516", "chat_v20260926"):
            session = await sessions.create(
                CreateAgentStudioSessionRequest(
                    idempotency_key=f"candidate-{key}-{token}",
                    title=key,
                    new_definition=CreateAgentDefinitionRequest(
                        definition_key=f"candidate_{key}_{token}",
                        name=key,
                        model_key="fake::conversation",
                        reviewer_model_key="fake::reviewer",
                        embedding_model_key="fake::retriever",
                        prompt_key=key,
                        tool_names=["search_memory"],
                    ),
                    new_subject=CreateMemorySubjectRequest(
                        external_key=f"candidate-{key}-{token}",
                        display_name="Synthetic subject",
                    ),
                )
            )
            records[key] = session
            expected = registry.get_template("prompt", key, scenario="chat")
            assert expected is not None
            assert (
                session["agent_definition"]["prompt_sha256"]
                == hashlib.sha256(expected["content"].encode()).hexdigest()
            )

        async with engine.connect() as connection:
            for key, session in records.items():
                row = (
                    await connection.execute(
                        select(
                            agent_definition_versions.c.prompt_key,
                            agent_definition_versions.c.prompt_sha256,
                            agent_definition_versions.c.prompt_content,
                            conversations.c.agent_definition_version_id,
                        )
                        .join(
                            conversations,
                            conversations.c.agent_definition_version_id
                            == agent_definition_versions.c.id,
                        )
                        .where(conversations.c.id == session["conversation"]["id"])
                    )
                ).one()
                expected = registry.get_template("prompt", key, scenario="chat")
                assert row.prompt_key == key
                assert row.prompt_content == expected["content"]
                assert row.prompt_sha256 == session["agent_definition"]["prompt_sha256"]
                assert (
                    str(row.agent_definition_version_id)
                    == session["agent_definition"]["id"]
                )
        assert (
            records["chat_v20260516"]["agent_definition"]["prompt_sha256"]
            != (records["chat_v20260926"]["agent_definition"]["prompt_sha256"])
        )
    finally:
        await engine.dispose()
