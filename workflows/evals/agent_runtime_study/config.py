from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .contracts import ContextBudget, RuntimePolicy
from .semantic_retrieval import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    DEFAULT_EMBEDDINGS_BASE_URL,
    DEFAULT_EMBEDDINGS_MODEL,
    DEFAULT_QUERY_INSTRUCTION,
    RetrievalStrategy,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_ROOT = Path(__file__).resolve().parent
DEFAULT_MODELS = (
    "dgx_vllm::qwen3.6-35b-a3b-fp8",
    "local_llama_server::gemma4",
)
DEFAULT_ADAPTERS = ("custom_loop", "pydantic_ai")
DEFAULT_REVIEWER_MODEL = "dgx_vllm::qwen3.6-35b-a3b-fp8"


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class StudyConfig:
    router_v1_base_url: str
    router_api_key: str
    ade_api_base_url: str
    ade_api_key: str
    output_dir: Path
    fixture_path: Path
    models: tuple[str, ...]
    adapters: tuple[str, ...]
    case_keys: tuple[str, ...]
    reviewer_model_key: str
    reviewer_max_output_tokens: int
    embeddings_base_url: str
    embeddings_api_key: str
    embeddings_model: str
    embedding_dimensions: int
    embedding_timeout_seconds: float
    retrieval_strategy: RetrievalStrategy
    retrieval_query_instruction: str | None
    retrieval_fixture_path: Path
    deployment_registry_path: Path
    allow_unqualified_study_models: bool
    policy: RuntimePolicy
    run_live: bool


def _project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _strings(value: object, default: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(value, list):
        return default
    parsed = tuple(str(item).strip() for item in value if str(item).strip())
    return parsed or default


def load_config(path: Path) -> StudyConfig:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    payload: dict[str, Any] = {}
    if path.is_file():
        with path.open("rb") as handle:
            payload = tomllib.load(handle)
    elif path != WORKFLOW_ROOT / "config.toml":
        raise ConfigError(f"Config file not found: {path}")

    context_payload = payload.get("context_budget") or {}
    if not isinstance(context_payload, dict):
        raise ConfigError("context_budget must be a table")
    budget = ContextBudget(
        total_tokens=int(context_payload.get("total_tokens", 16384)),
        response_reserve_tokens=int(
            context_payload.get("response_reserve_tokens", 4096)
        ),
        agent_tokens=int(context_payload.get("agent_tokens", 1800)),
        profile_tokens=int(context_payload.get("profile_tokens", 1200)),
        summary_tokens=int(context_payload.get("summary_tokens", 1200)),
        retrieved_tokens=int(context_payload.get("retrieved_tokens", 1200)),
        recent_message_tokens=int(context_payload.get("recent_message_tokens", 1700)),
    )
    policy = RuntimePolicy(
        timeout_seconds=float(payload.get("timeout_seconds", 180.0)),
        retry_count=int(payload.get("retry_count", 0)),
        max_model_requests=int(payload.get("max_model_requests", 6)),
        max_output_tokens=int(payload.get("max_output_tokens", 4096)),
        memory_search_limit=int(payload.get("memory_search_limit", 8)),
        include_episodes=bool(payload.get("include_episodes", False)),
        context_budget=budget,
    )
    router_base = str(
        os.getenv("AGENT_RUNTIME_STUDY_ROUTER_V1_BASE_URL")
        or payload.get("router_v1_base_url")
        or os.getenv("ADE_API_MODEL_ROUTER_BASE_URL")
        or "http://model-router:8010"
    ).rstrip("/")
    if not router_base.endswith("/v1"):
        router_base = f"{router_base}/v1"
    config = StudyConfig(
        router_v1_base_url=router_base,
        router_api_key=str(
            os.getenv("AGENT_RUNTIME_STUDY_ROUTER_API_KEY")
            or os.getenv("MODEL_ROUTER_API_KEY")
            or payload.get("router_api_key")
            or "local-router-dev-key"
        ).strip(),
        ade_api_base_url=str(
            os.getenv("AGENT_RUNTIME_STUDY_ADE_API_BASE_URL")
            or payload.get("ade_api_base_url")
            or f"http://127.0.0.1:{os.getenv('ADE_API_PORT', '8000')}"
        ).rstrip("/"),
        ade_api_key=str(
            payload.get("ade_api_key") or os.getenv("ADE_API_ADMIN_KEY") or ""
        ).strip(),
        output_dir=_project_path(
            payload.get("output_dir", "workflows/evals/agent_runtime_study/outputs")
        ),
        fixture_path=_project_path(
            payload.get(
                "fixture_path",
                "workflows/evals/agent_runtime_study/fixtures/study_cases.json",
            )
        ),
        models=_strings(payload.get("models"), DEFAULT_MODELS),
        adapters=_strings(payload.get("adapters"), DEFAULT_ADAPTERS),
        case_keys=_strings(payload.get("case_keys"), ()),
        reviewer_model_key=str(
            os.getenv("AGENT_RUNTIME_STUDY_REVIEWER_MODEL_KEY")
            or payload.get("reviewer_model_key")
            or DEFAULT_REVIEWER_MODEL
        ).strip(),
        reviewer_max_output_tokens=int(payload.get("reviewer_max_output_tokens", 2048)),
        embeddings_base_url=str(
            os.getenv("AGENT_RUNTIME_STUDY_EMBEDDINGS_BASE_URL")
            or payload.get("embeddings_base_url")
            or DEFAULT_EMBEDDINGS_BASE_URL
        ).rstrip("/"),
        embeddings_api_key=str(
            os.getenv("AGENT_RUNTIME_STUDY_EMBEDDINGS_API_KEY")
            or payload.get("embeddings_api_key")
            or ""
        ).strip(),
        embeddings_model=str(
            payload.get("embeddings_model") or DEFAULT_EMBEDDINGS_MODEL
        ).strip(),
        embedding_dimensions=int(
            payload.get("embedding_dimensions", DEFAULT_EMBEDDING_DIMENSIONS)
        ),
        embedding_timeout_seconds=float(payload.get("embedding_timeout_seconds", 15.0)),
        retrieval_strategy=RetrievalStrategy(
            str(payload.get("retrieval_strategy") or "hybrid")
        ),
        retrieval_query_instruction=(
            str(payload["retrieval_query_instruction"])
            if payload.get("retrieval_query_instruction") is not None
            else DEFAULT_QUERY_INSTRUCTION
        ),
        retrieval_fixture_path=_project_path(
            payload.get(
                "retrieval_fixture_path",
                "workflows/evals/agent_runtime_study/fixtures/semantic_retrieval_cases.json",
            )
        ),
        deployment_registry_path=_project_path(
            payload.get(
                "deployment_registry_path",
                "workflows/evals/agent_runtime_study/deployments.toml",
            )
        ),
        allow_unqualified_study_models=bool(
            payload.get("allow_unqualified_study_models", False)
        ),
        policy=policy,
        run_live=bool(payload.get("run_live", False)),
    )
    validate_config(config)
    return config


def validate_config(config: StudyConfig) -> None:
    if not config.router_v1_base_url:
        raise ConfigError("router_v1_base_url is required")
    if not config.fixture_path.is_file():
        raise ConfigError(f"fixture_path does not exist: {config.fixture_path}")
    unknown_adapters = sorted(set(config.adapters) - set(DEFAULT_ADAPTERS))
    if unknown_adapters:
        raise ConfigError(f"Unknown adapters: {unknown_adapters}")
    if not config.models:
        raise ConfigError("At least one model is required")
    if not config.reviewer_model_key:
        raise ConfigError("reviewer_model_key is required")
    if config.reviewer_max_output_tokens < 1:
        raise ConfigError("reviewer_max_output_tokens must be positive")
    if not config.embeddings_base_url or not config.embeddings_model:
        raise ConfigError("embeddings endpoint and model are required")
    if config.embedding_dimensions < 1:
        raise ConfigError("embedding_dimensions must be positive")
    if config.embedding_timeout_seconds <= 0:
        raise ConfigError("embedding_timeout_seconds must be positive")
    if not config.retrieval_fixture_path.is_file():
        raise ConfigError(
            f"retrieval_fixture_path does not exist: {config.retrieval_fixture_path}"
        )
    if not config.deployment_registry_path.is_file():
        raise ConfigError(
            f"deployment_registry_path does not exist: {config.deployment_registry_path}"
        )
    budget = config.policy.context_budget
    if budget.total_tokens <= budget.response_reserve_tokens:
        raise ConfigError("context token budget must exceed response reserve")


def with_overrides(
    config: StudyConfig,
    *,
    models: tuple[str, ...] | None = None,
    adapters: tuple[str, ...] | None = None,
    case_keys: tuple[str, ...] | None = None,
    run_live: bool | None = None,
    output_dir: Path | None = None,
    timeout_seconds: float | None = None,
    retry_count: int | None = None,
    max_output_tokens: int | None = None,
) -> StudyConfig:
    policy = replace(
        config.policy,
        timeout_seconds=(
            config.policy.timeout_seconds
            if timeout_seconds is None
            else timeout_seconds
        ),
        retry_count=(config.policy.retry_count if retry_count is None else retry_count),
        max_output_tokens=(
            config.policy.max_output_tokens
            if max_output_tokens is None
            else max_output_tokens
        ),
    )
    next_config = replace(
        config,
        models=models or config.models,
        adapters=adapters or config.adapters,
        case_keys=case_keys if case_keys is not None else config.case_keys,
        run_live=config.run_live if run_live is None else run_live,
        output_dir=output_dir or config.output_dir,
        policy=policy,
    )
    validate_config(next_config)
    return next_config


def public_config(config: StudyConfig) -> dict[str, Any]:
    return {
        "router_v1_base_url": config.router_v1_base_url,
        "ade_api_base_url": config.ade_api_base_url,
        "output_dir": str(config.output_dir),
        "fixture_path": str(config.fixture_path),
        "models": list(config.models),
        "adapters": list(config.adapters),
        "case_keys": list(config.case_keys),
        "reviewer_model_key": config.reviewer_model_key,
        "reviewer_max_output_tokens": config.reviewer_max_output_tokens,
        "embeddings_base_url": config.embeddings_base_url,
        "embeddings_model": config.embeddings_model,
        "embedding_dimensions": config.embedding_dimensions,
        "embedding_timeout_seconds": config.embedding_timeout_seconds,
        "retrieval_strategy": config.retrieval_strategy.value,
        "retrieval_query_instruction": config.retrieval_query_instruction,
        "retrieval_fixture_path": str(config.retrieval_fixture_path),
        "deployment_registry_path": str(config.deployment_registry_path),
        "allow_unqualified_study_models": config.allow_unqualified_study_models,
        "policy": asdict(config.policy),
        "run_live": config.run_live,
    }
