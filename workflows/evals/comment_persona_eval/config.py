"""Local evaluation configuration; loading never changes the caller's environment."""

from __future__ import annotations

import argparse
import os
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_ROOT = Path(__file__).resolve().parent
TASK_SHAPES = {"classic", "all_in_system", "structured_output"}


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class EvalConfig:
    api_base_url: str = "http://127.0.0.1:8000"
    api_key: str = field(default="", repr=False)
    output_dir: Path = Path("workflows/evals/comment_persona_eval/outputs")
    news_path: Path = Path(
        "workflows/evals/comment_persona_eval/inputs/sports_news_demo.txt"
    )
    rounds: int = 3
    concurrency: int = 1
    stop_on_error: bool = False
    persona_keys: tuple[str, ...] = ()
    persona_search: str = ""
    limit: int = 0
    model_key: str = "local_llama_server::qwen3527b"
    prompt_key: str = "comment_v20260418"
    max_tokens: int = 0
    timeout_seconds: float = 180.0
    retry_count: int = 0
    task_shape: str = "all_in_system"
    cache_prompt: bool = False
    enable_thinking: bool = False
    temperature: float = 0.6
    top_p: float = 1.0
    top_k: int | None = 64
    api_retry_count: int = 2


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_config(path: Path) -> EvalConfig:
    environment = {**dotenv_values(PROJECT_ROOT / ".env"), **os.environ}
    payload: dict[str, Any] = {}
    if path.exists():
        with path.open("rb") as handle:
            payload = tomllib.load(handle)
    elif path != WORKFLOW_ROOT / "config.toml":
        raise ConfigError(f"Config file not found: {path}")
    config = EvalConfig(
        api_base_url=str(payload.get("api_base_url", EvalConfig.api_base_url)).rstrip(
            "/"
        ),
        api_key=str(environment.get("ADE_API_ADMIN_KEY") or "").strip(),
        output_dir=project_path(payload.get("output_dir", EvalConfig.output_dir)),
        news_path=project_path(payload.get("news_path", EvalConfig.news_path)),
        rounds=int(payload.get("rounds", EvalConfig.rounds)),
        concurrency=int(payload.get("concurrency", EvalConfig.concurrency)),
        stop_on_error=bool(payload.get("stop_on_error", EvalConfig.stop_on_error)),
        persona_keys=tuple(_clean_string_list(payload.get("persona_keys", []))),
        persona_search=str(payload.get("persona_search", "") or "").strip(),
        limit=int(payload.get("limit", EvalConfig.limit)),
        model_key=str(payload.get("model_key", EvalConfig.model_key) or "").strip(),
        prompt_key=str(payload.get("prompt_key", EvalConfig.prompt_key) or "").strip(),
        max_tokens=int(payload.get("max_tokens", EvalConfig.max_tokens)),
        timeout_seconds=float(
            payload.get("timeout_seconds", EvalConfig.timeout_seconds)
        ),
        retry_count=int(payload.get("retry_count", EvalConfig.retry_count)),
        task_shape=str(payload.get("task_shape", EvalConfig.task_shape) or "")
        .strip()
        .lower(),
        cache_prompt=bool(payload.get("cache_prompt", EvalConfig.cache_prompt)),
        enable_thinking=bool(
            payload.get("enable_thinking", EvalConfig.enable_thinking)
        ),
        temperature=float(payload.get("temperature", EvalConfig.temperature)),
        top_p=float(payload.get("top_p", EvalConfig.top_p)),
        top_k=_optional_int(payload.get("top_k", EvalConfig.top_k)),
        api_retry_count=int(payload.get("api_retry_count", EvalConfig.api_retry_count)),
    )
    validate_config(config)
    return config


def validate_config(config: EvalConfig) -> None:
    if not config.api_base_url:
        raise ConfigError("api_base_url is required")
    if not config.news_path.is_file():
        raise ConfigError(f"news_path does not exist: {config.news_path}")
    if config.rounds < 1:
        raise ConfigError("rounds must be >= 1")
    if config.concurrency != 1:
        raise ConfigError("Only concurrency=1 is supported for now")
    if config.limit < 0:
        raise ConfigError("limit must be >= 0")
    if config.max_tokens < 0:
        raise ConfigError("max_tokens must be >= 0")
    if config.timeout_seconds <= 0:
        raise ConfigError("timeout_seconds must be > 0")
    if not 0 <= config.retry_count <= 5:
        raise ConfigError("retry_count must be between 0 and 5")
    if config.api_retry_count < 0:
        raise ConfigError("api_retry_count must be >= 0")
    if config.task_shape not in TASK_SHAPES:
        raise ConfigError(
            f"task_shape must be one of: {', '.join(sorted(TASK_SHAPES))}"
        )
    if not 0 <= config.temperature <= 2:
        raise ConfigError("temperature must be between 0 and 2")
    if not 0 < config.top_p <= 1:
        raise ConfigError("top_p must be > 0 and <= 1")
    if config.top_k is not None and config.top_k <= 0:
        raise ConfigError("top_k must be > 0 when set")
    if not config.model_key:
        raise ConfigError("model_key is required")
    if not config.prompt_key:
        raise ConfigError("prompt_key is required")


def apply_cli_overrides(config: EvalConfig, args: argparse.Namespace) -> EvalConfig:
    persona_keys = list(config.persona_keys)
    persona_keys.extend(_clean_string_list(args.persona_key or []))
    updates: dict[str, Any] = {"persona_keys": tuple(dict.fromkeys(persona_keys))}
    if args.api_base_url:
        updates["api_base_url"] = str(args.api_base_url).rstrip("/")
    if args.output_dir:
        updates["output_dir"] = project_path(args.output_dir)
    if args.limit is not None:
        updates["limit"] = int(args.limit)
    next_config = replace(config, **updates)
    validate_config(next_config)
    return next_config


def _clean_string_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        raise ConfigError("Expected a list of strings")
    return [str(item).strip() for item in raw if str(item).strip()]


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, str) and not value.strip():
        return None
    return int(value)
