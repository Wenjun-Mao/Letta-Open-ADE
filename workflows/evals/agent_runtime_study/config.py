from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .contracts import ContextBudget, RuntimePolicy


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_ROOT = Path(__file__).resolve().parent
DEFAULT_MODELS = (
    "dgx_vllm::qwen3.6-35b-a3b-fp8",
    "local_llama_server::gemma4",
)
DEFAULT_ADAPTERS = ("custom_loop", "pydantic_ai")


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
    max_output_tokens: int | None = None,
) -> StudyConfig:
    policy = replace(
        config.policy,
        timeout_seconds=(
            config.policy.timeout_seconds
            if timeout_seconds is None
            else timeout_seconds
        ),
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
        "policy": asdict(config.policy),
        "run_live": config.run_live,
    }
