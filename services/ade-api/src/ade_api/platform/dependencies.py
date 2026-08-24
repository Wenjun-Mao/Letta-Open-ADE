from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from letta_client import Letta

from ade_api.features.agent_studio.lifecycle_registry import AgentLifecycleRegistry
from ade_api.features.schema_center.registry import LabelSchemaRegistry
from ade_api.features.tool_center.registry import CustomToolRegistry
from ade_api.integrations.letta.agent_service import LettaAgentService
from ade_api.integrations.letta.tool_service import LettaToolService
from ade_api.integrations.model_router.client import ModelRouterClient
from ade_api.features.prompt_center.registry import PromptPersonaRegistry
from ade_api.features.comment_lab.service import CommentingService
from ade_api.features.label_lab.service import LabelingService
from ade_api.platform.settings import AdeApiSettings, get_settings
from ade_api.features.test_center.orchestrator import TestRunOrchestrator

APP_VERSION = os.getenv("ADE_API_VERSION", "0.3.0")
PROJECT_ROOT = Path(os.getenv("ADE_REPOSITORY_ROOT", Path.cwd())).resolve()


def _resolve_project_path(value: str) -> Path:
    path = Path(str(value or "").strip())
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


_initial_settings = get_settings()
RUNTIME_DATA_DIR = _resolve_project_path(_initial_settings.runtime_data_dir).resolve()
REVISION_LOG_DIR = RUNTIME_DATA_DIR / "audit"
REVISION_LOG_FILE = REVISION_LOG_DIR / "prompt_persona_revisions.jsonl"


@dataclass(frozen=True)
class ApplicationServices:
    client: Letta
    letta_agent_service: LettaAgentService
    letta_tool_service: LettaToolService
    test_orchestrator: TestRunOrchestrator
    prompt_persona_registry: PromptPersonaRegistry
    label_schema_registry: LabelSchemaRegistry
    custom_tool_registry: CustomToolRegistry
    agent_lifecycle_registry: AgentLifecycleRegistry
    model_router_client: ModelRouterClient
    commenting_service: CommentingService
    labeling_service: LabelingService


def build_application_services(
    *,
    settings: AdeApiSettings | None = None,
    project_root: Path = PROJECT_ROOT,
) -> ApplicationServices:
    resolved_settings = settings or get_settings()
    resolved_project_root = Path(project_root).resolve()

    def resolve_path(value: str) -> Path:
        path = Path(str(value or "").strip())
        return path if path.is_absolute() else resolved_project_root / path

    runtime_data_dir = resolve_path(resolved_settings.runtime_data_dir).resolve()
    letta_client = Letta(
        base_url=os.getenv("LETTA_BASE_URL", "http://localhost:8283"),
        max_retries=0,
    )
    return ApplicationServices(
        client=letta_client,
        letta_agent_service=LettaAgentService(letta_client),
        letta_tool_service=LettaToolService(letta_client),
        test_orchestrator=TestRunOrchestrator(
            project_root=resolved_project_root,
            state_root=runtime_data_dir / "test-runs",
        ),
        prompt_persona_registry=PromptPersonaRegistry(
            resolved_project_root,
            persona_db_path=resolve_path(resolved_settings.persona_db_path),
            persona_seed_jsonl_path=resolve_path(
                resolved_settings.persona_seed_jsonl_path
            ),
        ),
        label_schema_registry=LabelSchemaRegistry(resolved_project_root),
        custom_tool_registry=CustomToolRegistry(resolved_project_root),
        agent_lifecycle_registry=AgentLifecycleRegistry(
            resolved_project_root,
            base_dir=runtime_data_dir / "agent-lifecycle",
        ),
        model_router_client=ModelRouterClient(),
        commenting_service=CommentingService(),
        labeling_service=LabelingService(),
    )


@lru_cache(maxsize=1)
def get_application_services() -> ApplicationServices:
    return build_application_services()


def initialize_dependencies() -> ApplicationServices:
    """Create runtime services during application startup, not module import."""
    return get_application_services()


def shutdown_dependencies() -> None:
    if get_application_services.cache_info().currsize == 0:
        return
    services = get_application_services()
    services.test_orchestrator.shutdown()
    close = getattr(services.client, "close", None)
    if callable(close):
        close()
    get_application_services.cache_clear()


def get_letta_client() -> Letta:
    return get_application_services().client


def get_letta_agent_service() -> LettaAgentService:
    return get_application_services().letta_agent_service


def get_letta_tool_service() -> LettaToolService:
    return get_application_services().letta_tool_service


def get_test_orchestrator() -> TestRunOrchestrator:
    return get_application_services().test_orchestrator


def get_prompt_persona_registry() -> PromptPersonaRegistry:
    return get_application_services().prompt_persona_registry


def get_label_schema_registry() -> LabelSchemaRegistry:
    return get_application_services().label_schema_registry


def get_custom_tool_registry() -> CustomToolRegistry:
    return get_application_services().custom_tool_registry


def get_agent_lifecycle_registry() -> AgentLifecycleRegistry:
    return get_application_services().agent_lifecycle_registry


def get_model_router_client() -> ModelRouterClient:
    return get_application_services().model_router_client


def get_commenting_service() -> CommentingService:
    return get_application_services().commenting_service


def get_labeling_service() -> LabelingService:
    return get_application_services().labeling_service


LettaClientDependency = Annotated[Letta, Depends(get_letta_client)]
LettaAgentServiceDependency = Annotated[
    LettaAgentService,
    Depends(get_letta_agent_service),
]
LettaToolServiceDependency = Annotated[
    LettaToolService,
    Depends(get_letta_tool_service),
]
TestOrchestratorDependency = Annotated[
    TestRunOrchestrator,
    Depends(get_test_orchestrator),
]
PromptPersonaRegistryDependency = Annotated[
    PromptPersonaRegistry,
    Depends(get_prompt_persona_registry),
]
LabelSchemaRegistryDependency = Annotated[
    LabelSchemaRegistry,
    Depends(get_label_schema_registry),
]
CustomToolRegistryDependency = Annotated[
    CustomToolRegistry,
    Depends(get_custom_tool_registry),
]
AgentLifecycleRegistryDependency = Annotated[
    AgentLifecycleRegistry,
    Depends(get_agent_lifecycle_registry),
]
ModelRouterClientDependency = Annotated[
    ModelRouterClient,
    Depends(get_model_router_client),
]
CommentingServiceDependency = Annotated[
    CommentingService,
    Depends(get_commenting_service),
]
LabelingServiceDependency = Annotated[
    LabelingService,
    Depends(get_labeling_service),
]
