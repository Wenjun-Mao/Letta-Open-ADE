from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


WORKFLOW_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = WORKFLOW_ROOT.parents[2]
DEFAULT_DGX_MODEL = "dgx_vllm::qwen3.6-35b-a3b-fp8"
DEFAULT_DGX_EMBEDDING = "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B"
DEFAULT_LEGACY_MODEL = f"openai-proxy/{DEFAULT_DGX_MODEL}"
DEFAULT_FIXTURE_PATH = Path(
    "workflows/evals/chat_memory_eval/fixtures/recent_user_chat_turns.json"
)
RUN_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,48}$")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ParityConfig:
    legacy_api_base_url: str = "http://127.0.0.1:8000"
    native_api_base_url: str = "http://127.0.0.1:8002"
    legacy_api_key: str = ""
    native_api_key: str = ""
    database_url: str = ""
    output_dir: Path = Path("workflows/evals/agent_runtime_parity/outputs")
    fixture_path: Path = DEFAULT_FIXTURE_PATH
    rounds: int = 3
    timeout_seconds: float = 180.0
    retry_count: int = 0
    prompt_key: str = "chat_v20260516"
    persona_key: str = "chat_linxiaotang"
    legacy_model: str = DEFAULT_LEGACY_MODEL
    legacy_embedding: str = "letta/letta-free"
    native_conversation_model: str = DEFAULT_DGX_MODEL
    native_reviewer_model: str = DEFAULT_DGX_MODEL
    native_embedding_model: str = DEFAULT_DGX_EMBEDDING


def load_config(path: Path | None = None) -> ParityConfig:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    payload = _load_toml(path)
    config = ParityConfig(
        legacy_api_base_url=_value(
            payload,
            "legacy_api_base_url",
            "http://127.0.0.1:8000",
            "AGENT_RUNTIME_PARITY_LEGACY_API_BASE_URL",
        ).rstrip("/"),
        native_api_base_url=_value(
            payload,
            "native_api_base_url",
            "http://127.0.0.1:8002",
            "AGENT_RUNTIME_PARITY_NATIVE_API_BASE_URL",
        ).rstrip("/"),
        legacy_api_key=_value(
            payload,
            "legacy_api_key",
            os.getenv("ADE_API_ADMIN_KEY", ""),
            "AGENT_RUNTIME_PARITY_LEGACY_API_KEY",
        ),
        native_api_key=_value(
            payload,
            "native_api_key",
            os.getenv("ADE_API_OPERATOR_KEY") or os.getenv("ADE_API_ADMIN_KEY", ""),
            "AGENT_RUNTIME_PARITY_NATIVE_API_KEY",
        ),
        database_url=_value(
            payload,
            "database_url",
            os.getenv("ADE_API_DATABASE_URL", ""),
            "AGENT_RUNTIME_PARITY_DATABASE_URL",
        ),
        output_dir=_project_path(
            _value(
                payload,
                "output_dir",
                "workflows/evals/agent_runtime_parity/outputs",
                "AGENT_RUNTIME_PARITY_OUTPUT_DIR",
            )
        ),
        fixture_path=_project_path(
            _value(
                payload,
                "fixture_path",
                str(DEFAULT_FIXTURE_PATH),
                "AGENT_RUNTIME_PARITY_FIXTURE_PATH",
            )
        ),
        rounds=_integer(payload, "rounds", 3),
        timeout_seconds=_number(payload, "timeout_seconds", 180.0),
        retry_count=_integer(payload, "retry_count", 0),
        prompt_key=_value(
            payload,
            "prompt_key",
            "chat_v20260516",
            "AGENT_RUNTIME_PARITY_PROMPT_KEY",
        ),
        persona_key=_value(
            payload,
            "persona_key",
            "chat_linxiaotang",
            "AGENT_RUNTIME_PARITY_PERSONA_KEY",
        ),
        legacy_model=_value(
            payload,
            "legacy_model",
            DEFAULT_LEGACY_MODEL,
            "AGENT_RUNTIME_PARITY_LEGACY_MODEL",
        ),
        legacy_embedding=_value(
            payload,
            "legacy_embedding",
            "letta/letta-free",
            "AGENT_RUNTIME_PARITY_LEGACY_EMBEDDING",
        ),
        native_conversation_model=_value(
            payload,
            "native_conversation_model",
            DEFAULT_DGX_MODEL,
            "AGENT_RUNTIME_PARITY_NATIVE_CONVERSATION_MODEL",
        ),
        native_reviewer_model=_value(
            payload,
            "native_reviewer_model",
            DEFAULT_DGX_MODEL,
            "AGENT_RUNTIME_PARITY_NATIVE_REVIEWER_MODEL",
        ),
        native_embedding_model=_value(
            payload,
            "native_embedding_model",
            DEFAULT_DGX_EMBEDDING,
            "AGENT_RUNTIME_PARITY_NATIVE_EMBEDDING_MODEL",
        ),
    )
    validate_config(config)
    return config


def with_overrides(config: ParityConfig, **values: object) -> ParityConfig:
    updates = {key: value for key, value in values.items() if value is not None}
    if "output_dir" in updates:
        updates["output_dir"] = _project_path(str(updates["output_dir"]))
    if "fixture_path" in updates:
        updates["fixture_path"] = _project_path(str(updates["fixture_path"]))
    result = replace(config, **updates)
    validate_config(result)
    return result


def validate_config(config: ParityConfig) -> None:
    for field in ("legacy_api_base_url", "native_api_base_url"):
        if not str(getattr(config, field)).strip():
            raise ConfigError(f"{field} is required")
    if not config.legacy_api_key.strip():
        raise ConfigError("legacy_api_key is required")
    if not config.native_api_key.strip():
        raise ConfigError("native_api_key is required")
    if not config.database_url.startswith(
        ("postgres://", "postgresql://", "postgresql+psycopg://")
    ):
        raise ConfigError(
            "database_url must be a PostgreSQL URL for fail-closed cleanup"
        )
    if not config.fixture_path.is_file():
        raise ConfigError(f"fixture_path does not exist: {config.fixture_path}")
    if not 1 <= config.rounds <= 3:
        raise ConfigError("rounds must be between 1 and 3")
    if not 5 <= config.timeout_seconds <= 600:
        raise ConfigError("timeout_seconds must be between 5 and 600")
    if config.retry_count != 0:
        raise ConfigError("retry_count must be 0; parity runs forbid hidden retries")
    if not config.prompt_key.startswith("chat_"):
        raise ConfigError("prompt_key must start with chat_")
    if not config.persona_key.startswith("chat_"):
        raise ConfigError("persona_key must start with chat_")
    for field in (
        "legacy_model",
        "legacy_embedding",
        "native_conversation_model",
        "native_reviewer_model",
        "native_embedding_model",
    ):
        if not str(getattr(config, field)).strip():
            raise ConfigError(f"{field} is required")


def validate_run_id(run_id: str) -> str:
    value = run_id.strip().lower()
    if not RUN_ID_PATTERN.fullmatch(value):
        raise ConfigError(
            "run_id must match ^[a-z][a-z0-9_-]{1,48}$ so cleanup keys remain scoped"
        )
    return value


def public_config(config: ParityConfig) -> dict[str, object]:
    return {
        "legacy_api_base_url": config.legacy_api_base_url,
        "native_api_base_url": config.native_api_base_url,
        "database_url_configured": bool(config.database_url),
        "output_dir": str(config.output_dir),
        "fixture_path": str(config.fixture_path),
        "rounds": config.rounds,
        "timeout_seconds": config.timeout_seconds,
        "retry_count": config.retry_count,
        "prompt_key": config.prompt_key,
        "persona_key": config.persona_key,
        "legacy_model": config.legacy_model,
        "legacy_embedding": config.legacy_embedding,
        "native_conversation_model": config.native_conversation_model,
        "native_reviewer_model": config.native_reviewer_model,
        "native_embedding_model": config.native_embedding_model,
    }


def router_model_key(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("openai-proxy/"):
        return normalized.split("/", 1)[1]
    return normalized


def _load_toml(path: Path | None) -> dict[str, Any]:
    selected = path or WORKFLOW_ROOT / "config.toml"
    if not selected.is_file():
        if path is None:
            return {}
        raise ConfigError(f"Config file not found: {selected}")
    with selected.open("rb") as handle:
        payload = tomllib.load(handle)
    if not isinstance(payload, dict):
        raise ConfigError("config must be a TOML table")
    return payload


def _value(payload: dict[str, Any], key: str, default: str, env_key: str) -> str:
    return str(os.getenv(env_key) or payload.get(key) or default).strip()


def _integer(payload: dict[str, Any], key: str, default: int) -> int:
    value = os.getenv(f"AGENT_RUNTIME_PARITY_{key.upper()}")
    return int(value if value is not None else payload.get(key, default))


def _number(payload: dict[str, Any], key: str, default: float) -> float:
    value = os.getenv(f"AGENT_RUNTIME_PARITY_{key.upper()}")
    return float(value if value is not None else payload.get(key, default))


def _project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path
