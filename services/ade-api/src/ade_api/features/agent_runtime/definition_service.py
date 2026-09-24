from __future__ import annotations

import hashlib
import re
from typing import Any
from uuid import uuid4

from ade_api.features.prompt_center import PromptTemplateReader
from ade_api.platform.project_paths import PROJECT_ROOT
from ade_api.platform.settings import AdeApiSettings
from model_catalog_contracts.deployment_manifest import load_deployment_manifest

from .contracts import CreateAgentDefinitionRequest, QualificationState
from .database_boundary import (
    DEFAULT_WORKSPACE_ID,
    RuntimeDatabase,
    require_default_workspace,
)
from .deployments import ResolvedDeployment, resolve_deployment
from .errors import RuntimeValidationError
from .memory_policy_binding import TYPED_MEMORY_POLICY_VERSION
from .persistence.definitions import DefinitionVersionRepository
from .presenters import definition_response
from .release_policy import (
    AGENT_STUDIO_DEPLOYMENT_MANIFEST_PATH,
    current_production_policy_hashes,
    load_validated_agent_studio_release,
    source_tree_is_clean,
)
from .router_transport import RouterTransport


MEMORY_POLICY_VERSION = TYPED_MEMORY_POLICY_VERSION
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
            release = load_validated_agent_studio_release()
            route_aliases = release.route_aliases
            prompt_key = release.agent_bundle.prompt_key
            persona_key = release.agent_bundle.persona_key
            tool_names = list(release.agent_bundle.tool_names)
        else:
            manifest = load_deployment_manifest(
                PROJECT_ROOT / AGENT_STUDIO_DEPLOYMENT_MANIFEST_PATH,
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
                for role in ("conversation", "reviewer", "retriever")
            }
            missing_roles = [role for role, alias in route_aliases.items() if not alias]
            if missing_roles:
                raise RuntimeValidationError(
                    "Deployment manifest has no active Agent Studio route for: "
                    + ", ".join(missing_roles)
                )
            prompt_key = "chat_v20260516"
            persona_key = "chat_linxiaotang"
            tool_names = ["search_memory"]

        return CreateAgentDefinitionRequest(
            definition_key="ade_native_default",
            name="ADE Native Companion",
            model_key=route_aliases["conversation"],
            reviewer_model_key=route_aliases["reviewer"],
            embedding_model_key=route_aliases["retriever"],
            prompt_key=prompt_key,
            persona_key=persona_key,
            tool_names=tool_names,
        )

    def configured_agent_studio_bundle(self) -> dict[str, Any]:
        """Describe the configured bundle without requiring a live provider."""

        request = self.default_agent_studio_request()
        manifest = load_deployment_manifest(
            PROJECT_ROOT / AGENT_STUDIO_DEPLOYMENT_MANIFEST_PATH,
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
        deployments = self._resolve_deployments(request, catalog, release=None)
        qualification = (
            QualificationState.QUALIFIED
            if all(
                deployment.qualification_state is QualificationState.QUALIFIED
                for deployment in deployments
            )
            else QualificationState.UNQUALIFIED
        )
        return {
            "key": "ade_native_default",
            "name": "ADE Native Default",
            "model_key": deployments[0].route_alias,
            "reviewer_model_key": deployments[1].route_alias,
            "embedding_model_key": deployments[2].route_alias,
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
                    DEFAULT_WORKSPACE_ID,
                    {
                        "id": version_id or str(uuid4()),
                        **({"agent_definition_id": root_id} if root_id else {}),
                        **prepared,
                    },
                    purpose=purpose,
                    expected_current_version=request.expected_current_version,
                )
        return definition_response(row)

    async def prepare(
        self, request: CreateAgentDefinitionRequest, *, purpose: str = "development"
    ) -> dict[str, Any]:
        """Resolve external snapshots without writing a partial definition."""

        await self.database.ensure_ready()
        if "get_weather" in request.tool_names and purpose != "evaluation":
            raise RuntimeValidationError(
                "get_weather is available only to evaluation sessions"
            )
        release = (
            load_validated_agent_studio_release()
            if self.settings.agent_runtime_mode == "release"
            else None
        )
        if (
            purpose == "agent_studio"
            and release is not None
            and (
                request.prompt_key != release.agent_bundle.prompt_key
                or request.persona_key != release.agent_bundle.persona_key
                or tuple(request.tool_names) != release.agent_bundle.tool_names
            )
        ):
            raise RuntimeValidationError(
                "Release Agent Studio definitions must use the exact qualified prompt, "
                "persona, and tool contract"
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
        deployments = self._resolve_deployments(request, catalog, release=release)
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
            "deployment_snapshot": [item.as_snapshot() for item in deployments],
        }

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
        *,
        release: Any | None,
    ) -> tuple[ResolvedDeployment, ResolvedDeployment, ResolvedDeployment]:
        mode = self.settings.agent_runtime_mode
        requested_routes = {
            "conversation": normalize_route_alias(request.model_key),
            "reviewer": normalize_route_alias(request.reviewer_model_key),
            "retriever": normalize_route_alias(request.embedding_model_key),
        }
        if release is not None and requested_routes != release.route_aliases:
            raise RuntimeValidationError(
                "Release Agent Studio sessions must use the exact qualified deployment routes"
            )
        release_checks = (
            {
                "expected_policy_hashes": current_production_policy_hashes(),
                "source_clean": source_tree_is_clean(),
            }
            if mode == "release"
            else {}
        )
        return (
            resolve_deployment(
                catalog,
                route_alias=requested_routes["conversation"],
                role="conversation",
                mode=mode,
                **release_checks,
            ),
            resolve_deployment(
                catalog,
                route_alias=requested_routes["reviewer"],
                role="reviewer",
                mode=mode,
                **release_checks,
            ),
            resolve_deployment(
                catalog,
                route_alias=requested_routes["retriever"],
                role="retriever",
                mode=mode,
                **release_checks,
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
