from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol
from .memory_inspection import MemoryInspectionService
from .private_observation_service import PrivateObservationService

from .contracts import (
    AcceptTurnRequest,
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateEvaluationSessionRequest,
    CreateMemorySubjectRequest,
    RetryRunRequest,
    UpdateMemorySubjectRequest,
)


class AgentRuntimeService(Protocol):
    memory_inspection: MemoryInspectionService
    private_observations: PrivateObservationService

    async def get_agent_studio_options(self) -> dict[str, Any]: ...

    async def create_agent_studio_session(
        self, request: CreateAgentStudioSessionRequest
    ) -> dict[str, Any]: ...

    async def get_agent_studio_session(
        self, conversation_id: str
    ) -> dict[str, Any]: ...

    async def list_agent_studio_sessions(
        self, *, include_archived: bool, limit: int, offset: int
    ) -> dict[str, Any]: ...

    async def set_agent_studio_session_archived(
        self, conversation_id: str, *, archived: bool
    ) -> dict[str, Any]: ...

    async def list_agent_studio_definitions(
        self, *, include_archived: bool, limit: int, offset: int
    ) -> dict[str, Any]: ...

    async def create_agent_studio_definition(
        self, request: CreateAgentDefinitionRequest
    ) -> dict[str, Any]: ...

    async def set_agent_studio_definition_archived(
        self, definition_id: str, *, archived: bool
    ) -> dict[str, Any]: ...

    async def list_agent_studio_subjects(
        self, *, include_archived: bool, limit: int, offset: int
    ) -> dict[str, Any]: ...

    async def create_agent_studio_subject(
        self, request: CreateMemorySubjectRequest
    ) -> dict[str, Any]: ...

    async def update_agent_studio_subject(
        self, subject_id: str, request: UpdateMemorySubjectRequest
    ) -> dict[str, Any]: ...

    async def set_agent_studio_subject_archived(
        self, subject_id: str, *, archived: bool
    ) -> dict[str, Any]: ...

    async def get_agent_studio_conversation_state(
        self,
        conversation_id: str,
        *,
        message_limit: int,
        before_sequence: int | None,
    ) -> dict[str, Any]: ...

    async def create_evaluation_session(
        self, request: CreateEvaluationSessionRequest
    ) -> dict[str, Any]: ...

    async def get_evaluation_session_state(
        self,
        conversation_id: str,
        *,
        message_limit: int,
        before_sequence: int | None = None,
    ) -> dict[str, Any]: ...

    async def accept_turn(
        self, conversation_id: str, request: AcceptTurnRequest
    ) -> dict[str, Any]: ...

    async def get_run(self, run_id: str) -> dict[str, Any]: ...

    async def list_conversation_activity(
        self, conversation_id: str
    ) -> dict[str, Any]: ...

    async def list_runs(
        self, conversation_id: str, *, limit: int, offset: int
    ) -> dict[str, Any]: ...

    async def list_run_events(
        self, run_id: str, *, limit: int, after_sequence: int
    ) -> dict[str, Any]: ...

    async def cancel_run(self, run_id: str) -> dict[str, Any]: ...

    async def retry_run(
        self, run_id: str, request: RetryRunRequest
    ) -> dict[str, Any]: ...

    async def stream_events(
        self, run_id: str, after_sequence: int
    ) -> AsyncIterator[dict[str, Any]]: ...
