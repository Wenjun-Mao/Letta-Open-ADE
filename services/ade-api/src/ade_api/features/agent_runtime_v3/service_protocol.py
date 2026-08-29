from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol

from .contracts import (
    AcceptTurnRequest,
    CreateAgentDefinitionRequest,
    CreateConversationRequest,
    CreateMemorySubjectRequest,
)


class AgentRuntimeV3Service(Protocol):
    async def create_agent_definition(
        self, request: CreateAgentDefinitionRequest
    ) -> dict[str, Any]: ...

    async def get_agent_definition(self, definition_id: str) -> dict[str, Any]: ...

    async def create_memory_subject(
        self, request: CreateMemorySubjectRequest
    ) -> dict[str, Any]: ...

    async def get_memory_subject(self, subject_id: str) -> dict[str, Any]: ...

    async def get_subject_memories(self, subject_id: str) -> dict[str, Any]: ...

    async def create_conversation(
        self, request: CreateConversationRequest
    ) -> dict[str, Any]: ...

    async def get_conversation_state(self, conversation_id: str) -> dict[str, Any]: ...

    async def accept_turn(
        self, conversation_id: str, request: AcceptTurnRequest
    ) -> dict[str, Any]: ...

    async def get_run(self, run_id: str) -> dict[str, Any]: ...

    async def cancel_run(self, run_id: str) -> dict[str, Any]: ...

    async def stream_events(
        self, run_id: str, after_sequence: int
    ) -> AsyncIterator[dict[str, Any]]: ...
