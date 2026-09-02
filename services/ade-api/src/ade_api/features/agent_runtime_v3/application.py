from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from ade_api.features.prompt_center import (
    PromptTemplateReader,
    build_prompt_template_reader,
)
from ade_api.platform.project_paths import PROJECT_ROOT
from ade_api.platform.settings import AdeApiSettings, get_settings

from .contracts import (
    AcceptTurnRequest,
    AgentStudioResetRequest,
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateConversationRequest,
    CreateMemorySubjectRequest,
    UpdateMemorySubjectRequest,
)
from .agent_studio_reset import AgentStudioResetService
from .agent_studio_sessions import AgentStudioSessionService, AGENT_STUDIO_PURPOSE
from .database_boundary import RuntimeDatabase
from .definition_service import DefinitionService
from .errors import RuntimeNotReady
from .persistence.database import create_persistence_engine
from .resource_service import ResourceService
from .router_transport import RouterTransport
from .run_service import RunService
from .release_policy import ensure_agent_studio_release_ready


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
        self.database = RuntimeDatabase(engine)
        self.definitions = DefinitionService(
            database=self.database,
            settings=settings,
            prompt_registry=prompt_registry,
            router_transport=router_transport,
        )
        self.resources = ResourceService(self.database)
        self.agent_studio = AgentStudioSessionService(
            database=self.database,
            definitions=self.definitions,
        )
        self.agent_studio_reset = AgentStudioResetService(self.database)
        self.runs = RunService(
            database=self.database,
            settings=settings,
            router_transport=router_transport,
        )

    async def aclose(self) -> None:
        await self.engine.dispose()

    async def create_agent_definition(
        self, request: CreateAgentDefinitionRequest
    ) -> dict[str, Any]:
        return await self.definitions.create(request)

    async def get_agent_definition(self, definition_id: str) -> dict[str, Any]:
        return await self.definitions.get(definition_id)

    async def get_agent_studio_options(self) -> dict[str, Any]:
        self._ensure_agent_studio_release_ready()
        return await self.agent_studio.options()

    async def create_agent_studio_session(
        self, request: CreateAgentStudioSessionRequest
    ) -> dict[str, Any]:
        self._ensure_agent_studio_release_ready()
        return await self.agent_studio.create(request)

    async def get_agent_studio_session(self, conversation_id: str) -> dict[str, Any]:
        self._ensure_agent_studio_release_ready()
        return await self.agent_studio.get(conversation_id)

    async def list_agent_studio_sessions(
        self, *, include_archived: bool, limit: int, offset: int
    ) -> dict[str, Any]:
        self._ensure_agent_studio_release_ready()
        return await self.agent_studio.list(
            include_archived=include_archived, limit=limit, offset=offset
        )

    async def set_agent_studio_session_archived(
        self, conversation_id: str, *, archived: bool
    ) -> dict[str, Any]:
        self._ensure_agent_studio_release_ready()
        return await self.agent_studio.set_archived(conversation_id, archived=archived)

    async def list_agent_studio_definitions(
        self, *, include_archived: bool, limit: int, offset: int
    ) -> dict[str, Any]:
        self._ensure_agent_studio_release_ready()
        return await self.agent_studio.list_definitions(
            include_archived=include_archived, limit=limit, offset=offset
        )

    async def create_agent_studio_definition(
        self, request: CreateAgentDefinitionRequest
    ) -> dict[str, Any]:
        self._ensure_agent_studio_release_ready()
        return await self.agent_studio.create_definition(request)

    async def set_agent_studio_definition_archived(
        self, definition_id: str, *, archived: bool
    ) -> dict[str, Any]:
        self._ensure_agent_studio_release_ready()
        return await self.agent_studio.set_definition_archived(
            definition_id, archived=archived
        )

    async def list_agent_studio_subjects(
        self, *, include_archived: bool, limit: int, offset: int
    ) -> dict[str, Any]:
        self._ensure_agent_studio_release_ready()
        return await self.agent_studio.list_subjects(
            include_archived=include_archived, limit=limit, offset=offset
        )

    async def create_agent_studio_subject(
        self, request: CreateMemorySubjectRequest
    ) -> dict[str, Any]:
        self._ensure_agent_studio_release_ready()
        return await self.agent_studio.create_subject(request)

    async def update_agent_studio_subject(
        self, subject_id: str, request: UpdateMemorySubjectRequest
    ) -> dict[str, Any]:
        self._ensure_agent_studio_release_ready()
        return await self.agent_studio.update_subject(subject_id, request)

    async def set_agent_studio_subject_archived(
        self, subject_id: str, *, archived: bool
    ) -> dict[str, Any]:
        self._ensure_agent_studio_release_ready()
        return await self.agent_studio.set_subject_archived(
            subject_id, archived=archived
        )

    async def get_agent_studio_subject_memories(
        self, subject_id: str
    ) -> dict[str, Any]:
        self._ensure_agent_studio_release_ready()
        return await self.resources.get_subject_memories(
            subject_id, required_purpose=AGENT_STUDIO_PURPOSE
        )

    async def get_agent_studio_conversation_state(
        self,
        conversation_id: str,
        *,
        message_limit: int,
        before_sequence: int | None,
    ) -> dict[str, Any]:
        self._ensure_agent_studio_release_ready()
        return await self.resources.get_conversation_state(
            conversation_id,
            required_purpose=AGENT_STUDIO_PURPOSE,
            message_limit=message_limit,
            before_sequence=before_sequence,
        )

    async def reset_agent_studio(
        self, request: AgentStudioResetRequest
    ) -> dict[str, Any]:
        return await self.agent_studio_reset.reset(request)

    def _ensure_agent_studio_release_ready(self) -> None:
        ensure_agent_studio_release_ready(
            self.definitions.settings.agent_runtime_v3_mode
        )

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

    async def get_conversation_state(
        self,
        conversation_id: str,
        *,
        message_limit: int = 200,
        before_sequence: int | None = None,
    ) -> dict[str, Any]:
        return await self.resources.get_conversation_state(
            conversation_id,
            message_limit=message_limit,
            before_sequence=before_sequence,
        )

    async def accept_turn(
        self, conversation_id: str, request: AcceptTurnRequest
    ) -> dict[str, Any]:
        return await self.runs.accept_turn(conversation_id, request)

    async def get_run(self, run_id: str) -> dict[str, Any]:
        return await self.runs.get_run(run_id)

    async def list_runs(
        self, conversation_id: str, *, limit: int, offset: int
    ) -> dict[str, Any]:
        return await self.runs.list_runs(conversation_id, limit=limit, offset=offset)

    async def list_run_events(
        self, run_id: str, *, limit: int, after_sequence: int
    ) -> dict[str, Any]:
        return await self.runs.list_events(
            run_id, limit=limit, after_sequence=after_sequence
        )

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
