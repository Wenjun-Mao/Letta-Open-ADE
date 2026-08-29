from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from ade_api.features.prompt_center import (
    PromptTemplateReader,
    build_prompt_template_reader,
)
from ade_api.platform.dependencies import PROJECT_ROOT
from ade_api.platform.settings import AdeApiSettings, get_settings

from .contracts import (
    AcceptTurnRequest,
    CreateAgentDefinitionRequest,
    CreateConversationRequest,
    CreateMemorySubjectRequest,
)
from .database_boundary import RuntimeDatabase
from .definition_service import DefinitionService
from .errors import RuntimeNotReady
from .persistence.database import create_persistence_engine
from .resource_service import ResourceService
from .router_transport import RouterTransport
from .run_service import RunService


class AgentRuntimeV3Application:
    """Small facade over the v3 definition, resource, and run use cases."""

    def __init__(
        self,
        *,
        engine: AsyncEngine,
        settings: AdeApiSettings,
        prompt_registry: PromptTemplateReader,
        router_transport: RouterTransport,
    ) -> None:
        self.engine = engine
        database = RuntimeDatabase(engine)
        self.definitions = DefinitionService(
            database=database,
            settings=settings,
            prompt_registry=prompt_registry,
            router_transport=router_transport,
        )
        self.resources = ResourceService(database)
        self.runs = RunService(database)

    async def aclose(self) -> None:
        await self.engine.dispose()

    async def create_agent_definition(
        self, request: CreateAgentDefinitionRequest
    ) -> dict[str, Any]:
        return await self.definitions.create(request)

    async def get_agent_definition(self, definition_id: str) -> dict[str, Any]:
        return await self.definitions.get(definition_id)

    async def create_memory_subject(
        self, request: CreateMemorySubjectRequest
    ) -> dict[str, Any]:
        return await self.resources.create_subject(request)

    async def get_memory_subject(self, subject_id: str) -> dict[str, Any]:
        return await self.resources.get_subject(subject_id)

    async def get_subject_memories(self, subject_id: str) -> dict[str, Any]:
        return await self.resources.get_subject_memories(subject_id)

    async def create_conversation(
        self, request: CreateConversationRequest
    ) -> dict[str, Any]:
        return await self.resources.create_conversation(request)

    async def get_conversation_state(self, conversation_id: str) -> dict[str, Any]:
        return await self.resources.get_conversation_state(conversation_id)

    async def accept_turn(
        self, conversation_id: str, request: AcceptTurnRequest
    ) -> dict[str, Any]:
        return await self.runs.accept_turn(conversation_id, request)

    async def get_run(self, run_id: str) -> dict[str, Any]:
        return await self.runs.get_run(run_id)

    async def cancel_run(self, run_id: str) -> dict[str, Any]:
        return await self.runs.cancel_run(run_id)

    async def stream_events(
        self, run_id: str, after_sequence: int
    ) -> AsyncIterator[dict[str, Any]]:
        async for event in self.runs.stream_events(run_id, after_sequence):
            yield event


def build_agent_runtime_v3_service() -> AgentRuntimeV3Application:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeNotReady("ADE_API_DATABASE_URL is required for runtime v3")
    router_base_url = settings.model_router_v1_base_url()
    if not router_base_url:
        raise RuntimeNotReady(
            "ADE_API_MODEL_ROUTER_BASE_URL is required for runtime v3"
        )
    project_root = PROJECT_ROOT
    registry = build_prompt_template_reader(
        project_root,
        persona_db_path=_project_path(project_root, settings.persona_db_path),
        persona_seed_jsonl_path=_project_path(
            project_root, settings.persona_seed_jsonl_path
        ),
    )
    return AgentRuntimeV3Application(
        engine=create_persistence_engine(settings.database_url),
        settings=settings,
        prompt_registry=registry,
        router_transport=RouterTransport(
            base_url=router_base_url,
            api_key=settings.resolve_model_router_api_key(),
        ),
    )


def _project_path(project_root: Path, value: str) -> Path:
    path = Path(str(value or "").strip())
    return path if path.is_absolute() else project_root / path
