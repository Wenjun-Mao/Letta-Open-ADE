from __future__ import annotations

import hashlib
from typing import Any
from uuid import uuid4

from ade_api.features.prompt_center import PromptTemplateReader
from ade_api.platform.settings import AdeApiSettings

from .contracts import CreateAgentDefinitionRequest, QualificationState
from .database_boundary import (
    DEFAULT_WORKSPACE_ID,
    RuntimeDatabase,
    require_default_workspace,
)
from .deployments import ResolvedDeployment, resolve_deployment
from .errors import RuntimeValidationError
from .persistence.definitions import DefinitionVersionRepository
from .presenters import definition_response
from .router_transport import RouterTransport


MEMORY_POLICY_VERSION = "typed-user-facts-v1"


class DefinitionService:
    def __init__(
        self,
        *,
        database: RuntimeDatabase,
        settings: AdeApiSettings,
        prompt_registry: PromptTemplateReader,
        router_transport: RouterTransport,
    ) -> None:
        self.database = database
        self.settings = settings
        self.prompt_registry = prompt_registry
        self.router_transport = router_transport

    async def create(self, request: CreateAgentDefinitionRequest) -> dict[str, Any]:
        await self.database.ensure_ready()
        if (
            "get_weather" in request.tool_names
            and self.settings.agent_runtime_v3_mode != "development"
        ):
            raise RuntimeValidationError(
                "get_weather is available only in development and qualification runs"
            )
        prompt = self.prompt_registry.get_template(
            "prompt", request.prompt_key, scenario="chat"
        )
        persona = self.prompt_registry.get_template(
            "persona", request.persona_key, scenario="chat"
        )
        if prompt is None:
            raise RuntimeValidationError(
                f"Active chat prompt does not exist: {request.prompt_key}"
            )
        if persona is None:
            raise RuntimeValidationError(
                f"Active chat persona does not exist: {request.persona_key}"
            )
        catalog = await self.router_transport.catalog(
            timeout_seconds=self.settings.model_discovery_timeout_seconds
        )
        deployments = self._resolve_deployments(request, catalog)
        qualification = (
            QualificationState.QUALIFIED
            if all(
                item.qualification_state is QualificationState.QUALIFIED
                for item in deployments
            )
            else QualificationState.UNQUALIFIED
        )
        prompt_content = str(prompt.get("content", ""))
        persona_content = str(persona.get("content", ""))
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                await self.database.ensure_workspace(connection)
                row = await DefinitionVersionRepository(connection).create_next(
                    DEFAULT_WORKSPACE_ID,
                    {
                        "id": str(uuid4()),
                        "definition_key": request.definition_key,
                        "name": request.name,
                        "model_key": deployments[0].route_alias,
                        "reviewer_model_key": deployments[1].route_alias,
                        "embedding_model_key": deployments[2].route_alias,
                        "prompt_key": request.prompt_key,
                        "prompt_sha256": _sha256(prompt_content),
                        "prompt_content": prompt_content,
                        "persona_key": request.persona_key,
                        "persona_sha256": _sha256(persona_content),
                        "persona_content": persona_content,
                        "tool_names": list(request.tool_names),
                        "memory_policy_version": MEMORY_POLICY_VERSION,
                        "qualification_state": qualification.value,
                        "deployment_snapshot": [
                            item.as_snapshot() for item in deployments
                        ],
                    },
                )
        return definition_response(row)

    async def get(self, definition_id: str) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                row = await DefinitionVersionRepository(connection).get(definition_id)
                require_default_workspace(row)
        return definition_response(row)

    def _resolve_deployments(
        self,
        request: CreateAgentDefinitionRequest,
        catalog: dict[str, Any],
    ) -> tuple[ResolvedDeployment, ResolvedDeployment, ResolvedDeployment]:
        mode = self.settings.agent_runtime_v3_mode
        return (
            resolve_deployment(
                catalog,
                route_alias=_route_alias(request.model_key),
                role="conversation",
                mode=mode,
            ),
            resolve_deployment(
                catalog,
                route_alias=_route_alias(request.reviewer_model_key),
                role="reviewer",
                mode=mode,
            ),
            resolve_deployment(
                catalog,
                route_alias=_route_alias(request.embedding_model_key),
                role="retriever",
                mode=mode,
            ),
        )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _route_alias(value: str) -> str:
    normalized = str(value or "").strip()
    lowered = normalized.casefold()
    for prefix in ("openai-proxy/", "lmstudio_openai/", "openai/"):
        if lowered.startswith(prefix):
            return normalized[len(prefix) :].strip()
    return normalized
