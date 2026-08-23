from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from letta_client import Letta

from ade_api.clients.model_router import ModelRouterClient
from ade_api.registries.agent_lifecycle import AgentLifecycleRegistry
from ade_api.registries.custom_tool import CustomToolRegistry
from ade_api.registries.label_schema import LabelSchemaRegistry
from ade_api.registries.prompt_persona_store.registry import PromptPersonaRegistry
from ade_api.services.agent_platform import AgentPlatformService
from ade_api.services.commenting import CommentingService
from ade_api.services.labeling import LabelingService
from ade_api.settings import AdeApiSettings, get_settings
from ade_api.testing.orchestrator import PlatformTestOrchestrator

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
    agent_platform: AgentPlatformService
    test_orchestrator: PlatformTestOrchestrator
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
        agent_platform=AgentPlatformService(letta_client),
        test_orchestrator=PlatformTestOrchestrator(
            project_root=resolved_project_root,
            state_root=runtime_data_dir / "test-runs",
        ),
        prompt_persona_registry=PromptPersonaRegistry(
            resolved_project_root,
            persona_db_path=resolve_path(resolved_settings.persona_db_path),
            persona_seed_jsonl_path=resolve_path(resolved_settings.persona_seed_jsonl_path),
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


class _LazyDependency:
    def __init__(self, resolver: Callable[[], Any]) -> None:
        object.__setattr__(self, "_resolver", resolver)

    def _resolve(self) -> Any:
        return object.__getattribute__(self, "_resolver")()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._resolve(), name)

    def __repr__(self) -> str:
        return "<lazy application dependency>"


def _service(name: str) -> _LazyDependency:
    return _LazyDependency(lambda: getattr(get_application_services(), name))


client = _service("client")
agent_platform = _service("agent_platform")
test_orchestrator = _service("test_orchestrator")
prompt_persona_registry = _service("prompt_persona_registry")
label_schema_registry = _service("label_schema_registry")
custom_tool_registry = _service("custom_tool_registry")
agent_lifecycle_registry = _service("agent_lifecycle_registry")
model_router_client = _service("model_router_client")
commenting_service = _service("commenting_service")
labeling_service = _service("labeling_service")
