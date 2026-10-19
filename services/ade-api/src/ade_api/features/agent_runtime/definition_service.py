from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from ade_api.features.prompt_center import PromptTemplateReader
from ade_api.platform.project_paths import PROJECT_ROOT
from ade_api.platform.settings import AdeApiSettings
from model_catalog_contracts.deployment_manifest import load_deployment_manifest

from .contracts import CreateAgentDefinitionRequest, QualificationState
from .database_boundary import RuntimeDatabase
from .deployments import ResolvedDeployment, resolve_deployment
from .errors import (
    RuntimeConflict,
    RuntimeNotFound,
    RuntimeValidationError,
    UnqualifiedDeployment,
)
from .turn_sources import HINDSIGHT_MEMORY_POLICY
from .persistence.definitions import (
    AgentDefinitionRepository,
    DefinitionVersionRepository,
)
from .presenters import definition_response
from .router_transport import RouterTransport


MEMORY_POLICY_VERSION = HINDSIGHT_MEMORY_POLICY
_ROUTER_SOURCE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


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

    def default_agent_studio_request(self) -> CreateAgentDefinitionRequest:
        """Build the configured Agent Studio definition for the active mode."""

        if self.settings.agent_runtime_mode == "release":
            raise UnqualifiedDeployment(
                "Hindsight conversation path is not release-qualified"
            )
        else:
            manifest = load_deployment_manifest(
                PROJECT_ROOT / self.settings.agent_runtime_deployment_manifest,
                project_root=PROJECT_ROOT,
            )
            route_aliases = {
                role: next(
                    (
                        deployment.route_aliases[0]
                        for deployment in manifest.deployments
                        if role in deployment.roles
                        and deployment.lifecycle != "deprecated"
                    ),
                    "",
                )
                for role in ("conversation", "compaction")
            }
            missing_roles = [role for role, alias in route_aliases.items() if not alias]
            if missing_roles:
                raise RuntimeValidationError(
                    "Deployment manifest has no active Agent Studio route for: "
                    + ", ".join(missing_roles)
                )
            prompt_key = "chat_v20261019"
            persona_key = "chat_linxiaotang"
            tool_names = ["search_memory"]

        return CreateAgentDefinitionRequest(
            definition_key="ade_hindsight_default",
            name="ADE Hindsight Companion",
            model_key=route_aliases["conversation"],
            compaction_model_key=route_aliases["compaction"],
            prompt_key=prompt_key,
            persona_key=persona_key,
            tool_names=tool_names,
        )

    def configured_agent_studio_bundle(
        self, request: CreateAgentDefinitionRequest | None = None
    ) -> dict[str, Any]:
        """Describe the configured bundle without requiring a live provider."""

        request = request or self.default_agent_studio_request()
        manifest = load_deployment_manifest(
            PROJECT_ROOT / self.settings.agent_runtime_deployment_manifest,
            project_root=PROJECT_ROOT,
        )
        catalog = {
            "items": [
                {
                    "route_aliases": list(deployment.route_aliases),
                    "deployment": deployment.as_catalog_dict(),
                }
                for deployment in manifest.deployments
            ]
        }
        deployments = self._resolve_deployments(request, catalog)
        qualification = (
            QualificationState.QUALIFIED
            if all(
                deployment.qualification_state is QualificationState.QUALIFIED
                for deployment in deployments
            )
            else QualificationState.UNQUALIFIED
        )
        return {
            "key": "ade_hindsight_default",
            "name": "ADE Hindsight Default",
            "model_key": deployments[0].route_alias,
            "compaction_model_key": deployments[1].route_alias,
            "prompt_key": request.prompt_key,
            "persona_key": request.persona_key,
            "tool_names": list(request.tool_names),
            "memory_policy_version": MEMORY_POLICY_VERSION,
            "qualification_state": qualification.value,
            "deployments": [deployment.as_snapshot() for deployment in deployments],
        }

    async def create(
        self,
        request: CreateAgentDefinitionRequest,
        *,
        purpose: str = "development",
        version_id: str | None = None,
        root_id: str | None = None,
    ) -> dict[str, Any]:
        prepared = await self.prepare(request, purpose=purpose)
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                await self.database.ensure_workspace(connection)
                row = await DefinitionVersionRepository(connection).create_next(
                    self.database.workspace_id,
                    {
                        "id": version_id or str(uuid4()),
                        **({"agent_definition_id": root_id} if root_id else {}),
                        **prepared,
                    },
                    purpose=purpose,
                    expected_current_version=request.expected_current_version,
                )
        return definition_response(row)

    async def create_next_version(
        self,
        root_id: str,
        request: CreateAgentDefinitionRequest,
        prepared: dict[str, Any],
        *,
        purpose: str,
        validate_current: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        """Advance an existing scoped root using an already validated snapshot."""
        if not request.expected_current_version:
            raise RuntimeValidationError(
                "A positive expected_current_version is required"
            )
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                versions = DefinitionVersionRepository(connection)
                await versions.lock_workspace(self.database.workspace_id)
                root = await AgentDefinitionRepository(connection).get_for_update(
                    root_id
                )
                self.database.require_workspace(root)
                if root["purpose"] != purpose:
                    raise RuntimeNotFound(
                        "agent definition does not exist in this purpose"
                    )
                if root["definition_key"] != request.definition_key:
                    raise RuntimeValidationError(
                        "Definition key must match the existing root"
                    )
                current = await versions.get(str(root["current_version_id"]))
                if current["version"] != request.expected_current_version:
                    raise RuntimeConflict(
                        "agent definition current version does not match"
                    )
                validate_current(current)
                row = await versions.create_next(
                    self.database.workspace_id,
                    {**prepared, "id": str(uuid4()), "agent_definition_id": root_id},
                    purpose=purpose,
                    expected_current_version=request.expected_current_version,
                )
        return definition_response(row)

    async def prepare(
        self, request: CreateAgentDefinitionRequest, *, purpose: str = "development"
    ) -> dict[str, Any]:
        """Resolve external snapshots without writing a partial definition."""

        await self.database.ensure_ready()
        if self.settings.agent_runtime_mode == "release":
            raise UnqualifiedDeployment(
                "Hindsight conversation path is not release-qualified"
            )
        if "get_weather" in request.tool_names and purpose != "evaluation":
            raise RuntimeValidationError(
                "get_weather is available only to evaluation sessions"
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
        return {
            "definition_key": request.definition_key,
            "name": request.name,
            "model_key": deployments[0].route_alias,
            "compaction_model_key": deployments[1].route_alias,
            "prompt_key": request.prompt_key,
            "prompt_sha256": _sha256(prompt_content),
            "prompt_content": prompt_content,
            "persona_key": request.persona_key,
            "persona_sha256": _sha256(persona_content),
            "persona_content": persona_content,
            "tool_names": list(request.tool_names),
            "memory_policy_version": MEMORY_POLICY_VERSION,
            "qualification_state": qualification.value,
            "deployment_snapshot": [item.as_snapshot() for item in deployments],
        }

    async def get(self, definition_id: str) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                row = await DefinitionVersionRepository(connection).get(definition_id)
                self.database.require_workspace(row)
        return definition_response(row)

    def _resolve_deployments(
        self,
        request: CreateAgentDefinitionRequest,
        catalog: dict[str, Any],
    ) -> tuple[ResolvedDeployment, ResolvedDeployment]:
        mode = self.settings.agent_runtime_mode
        requested_routes = {
            "conversation": normalize_route_alias(request.model_key),
            "compaction": normalize_route_alias(request.compaction_model_key),
        }
        if mode == "release":
            raise UnqualifiedDeployment(
                "Hindsight conversation path is not release-qualified"
            )
        return (
            resolve_deployment(
                catalog,
                route_alias=requested_routes["conversation"],
                role="conversation",
                mode=mode,
            ),
            resolve_deployment(
                catalog,
                route_alias=requested_routes["compaction"],
                role="compaction",
                mode=mode,
            ),
        )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_route_alias(value: str) -> str:
    normalized = str(value or "").strip()
    source_id, separator, provider_model_id = normalized.partition("::")
    if (
        not separator
        or not _ROUTER_SOURCE_ID_RE.fullmatch(source_id)
        or not provider_model_id
        or "::" in provider_model_id
    ):
        raise RuntimeValidationError(
            "model keys must use canonical Model Router source::model identity"
        )
    return normalized
