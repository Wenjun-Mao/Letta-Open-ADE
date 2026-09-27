"""Explicit development trial over evaluation-owned native resources."""

from __future__ import annotations

from typing import Any

from .agent_studio_sessions import EVALUATION_PURPOSE, PurposeSessionService
from .contracts import CreateAgentDefinitionRequest, CreateAgentStudioSessionRequest
from .database_boundary import RuntimeDatabase
from .definition_service import DefinitionService
from .errors import RuntimeValidationError
from .history_capacity import bind_history_probe_capacity, checked_history_probe_capacity
from .history_native_rank import HISTORY_EMBEDDING_ROUTE
from .natural_context import HISTORY_PROBE_POLICY
from .natural_evaluation_capacity import DEEPSEEK_ROUTE
from .resource_service import ResourceService

TRIAL_PROMPT = "chat_v20260926"
TRIAL_PERSONA = "chat_linxiaotang"
TRIAL_DEEPSEEK_FINGERPRINT = "870ff4fb8a25a9c2016f67dcda05e26e82a6c5dea6ad55781a80be2201161cfe"
TRIAL_QWEN_FINGERPRINT = "c549d7dc288d2112f10e8b1032b502eda74557d093bc1390fe0fc4f44de63086"


def trial_definition_request() -> CreateAgentDefinitionRequest:
    return CreateAgentDefinitionRequest(
        definition_key="lin_xiaotang_history_trial",
        name="Lin Xiaotang · historical recall trial",
        model_key=DEEPSEEK_ROUTE,
        reviewer_model_key=DEEPSEEK_ROUTE,
        embedding_model_key=HISTORY_EMBEDDING_ROUTE,
        prompt_key=TRIAL_PROMPT,
        persona_key=TRIAL_PERSONA,
        tool_names=["search_memory"],
    )


def require_trial_definition(definition: dict[str, Any]) -> None:
    if (
        definition.get("memory_policy_version") != HISTORY_PROBE_POLICY
        or
        definition.get("prompt_key") != TRIAL_PROMPT
        or definition.get("persona_key") != TRIAL_PERSONA
        or definition.get("model_key") != DEEPSEEK_ROUTE
        or definition.get("reviewer_model_key") != DEEPSEEK_ROUTE
        or definition.get("embedding_model_key") != HISTORY_EMBEDDING_ROUTE
        or definition.get("tool_names") != ["search_memory"]
    ):
        raise RuntimeValidationError("History trial requires its pinned definition")
    if checked_history_probe_capacity(definition, purpose=EVALUATION_PURPOSE) is None:
        raise RuntimeValidationError("History trial capacity binding is missing")
    roles = {item["role"]: item for item in definition["deployment_snapshot"]}
    if (
        roles["conversation"]["fingerprint"] != TRIAL_DEEPSEEK_FINGERPRINT
        or roles["reviewer"]["fingerprint"] != TRIAL_DEEPSEEK_FINGERPRINT
        or roles["retriever"]["fingerprint"] != TRIAL_QWEN_FINGERPRINT
    ):
        raise RuntimeValidationError("History trial provider fingerprints differ")


class HistoryTrialDefinitions:
    def __init__(self, base: DefinitionService) -> None:
        self.base = base
        self.settings = base.settings

    def configured_agent_studio_bundle(self) -> dict[str, Any]:
        bundle = self.base.configured_agent_studio_bundle(trial_definition_request())
        bundle["key"] = "lin_xiaotang_history_trial"
        bundle["name"] = "Lin Xiaotang · historical recall trial"
        bundle["memory_policy_version"] = HISTORY_PROBE_POLICY
        bundle = bind_history_probe_capacity(
            {**bundle, "deployment_snapshot": bundle.pop("deployments")}
        )
        bundle["deployments"] = bundle.pop("deployment_snapshot")
        return bundle

    async def prepare(
        self, request: CreateAgentDefinitionRequest, *, purpose: str
    ) -> dict[str, Any]:
        if purpose != EVALUATION_PURPOSE:
            raise RuntimeValidationError("History trial requires evaluation purpose")
        expected = trial_definition_request()
        for key in (
            "model_key", "reviewer_model_key", "embedding_model_key",
            "prompt_key", "persona_key", "tool_names",
        ):
            if getattr(request, key) != getattr(expected, key):
                raise RuntimeValidationError("History trial definition differs")
        prepared = await self.base.prepare(request, purpose=purpose)
        prepared["memory_policy_version"] = HISTORY_PROBE_POLICY
        bound = bind_history_probe_capacity(prepared)
        require_trial_definition(bound)
        return bound


class HistoryTrialSessionService(PurposeSessionService):
    async def _resolve_definition(self, connection, request, identity, prepared):
        definition = await super()._resolve_definition(
            connection, request, identity, prepared
        )
        require_trial_definition(definition)
        return definition


class HistoryTrialService:
    def __init__(
        self, *, database: RuntimeDatabase, definitions: DefinitionService,
        resources: ResourceService,
    ) -> None:
        self.sessions = HistoryTrialSessionService(
            database=database,
            definitions=HistoryTrialDefinitions(definitions),
            purpose=EVALUATION_PURPOSE,
            session_namespace="history-trial",
        )
        self.resources = resources

    async def options(self) -> dict[str, Any]:
        options = await self.sessions.options()
        options["max_retry_count"] = 0
        return options

    async def create(self, request: CreateAgentStudioSessionRequest) -> dict[str, Any]:
        return await self.sessions.create(request)

    async def get(self, conversation_id: str) -> dict[str, Any]:
        return await self.sessions.get(conversation_id)

    async def list(self, *, include_archived: bool, limit: int, offset: int) -> dict[str, Any]:
        return await self.sessions.list(
            include_archived=include_archived, limit=limit, offset=offset
        )

    async def set_archived(self, conversation_id: str, *, archived: bool) -> dict[str, Any]:
        return await self.sessions.set_archived(conversation_id, archived=archived)

    async def list_definitions(self, *, include_archived: bool, limit: int, offset: int) -> dict[str, Any]:
        return await self.sessions.list_definitions(
            include_archived=include_archived, limit=limit, offset=offset
        )

    async def list_subjects(self, *, include_archived: bool, limit: int, offset: int) -> dict[str, Any]:
        return await self.sessions.list_subjects(
            include_archived=include_archived, limit=limit, offset=offset
        )

    async def conversation_state(
        self, conversation_id: str, *, message_limit: int,
        before_sequence: int | None,
    ) -> dict[str, Any]:
        await self.sessions.get(conversation_id)
        return await self.resources.get_conversation_state(
            conversation_id,
            required_purpose=EVALUATION_PURPOSE,
            message_limit=message_limit,
            before_sequence=before_sequence,
        )

    async def subject_memories(self, subject_id: str) -> dict[str, Any]:
        return await self.resources.get_subject_memories(
            subject_id, required_purpose=EVALUATION_PURPOSE
        )
