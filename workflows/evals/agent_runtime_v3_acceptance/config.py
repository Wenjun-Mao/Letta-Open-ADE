from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


WORKFLOW_ROOT = Path(__file__).resolve().parent
CLEANUP_OWNER = "019db09f-a9e0-7d93-a8b8-7697d67ad5bc"
DEFAULT_DGX_CHAT_MODEL = "dgx_vllm::qwen3.6-35b-a3b-fp8"
DEFAULT_DGX_EMBEDDING_MODEL = "dgx_embedding_sidecar::qwen3-embedding-0.6b"
DEFAULT_LLAMA_COMPATIBILITY_MODEL = "local_llama_server::gemma4"


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class AcceptanceConfig:
    api_base_url: str
    api_key: str
    output_dir: Path
    database_url: str | None = None
    conversation_model_key: str = DEFAULT_DGX_CHAT_MODEL
    reviewer_model_key: str = DEFAULT_DGX_CHAT_MODEL
    embedding_model_key: str = DEFAULT_DGX_EMBEDDING_MODEL
    llama_compatibility_model_key: str = DEFAULT_LLAMA_COMPATIBILITY_MODEL
    rounds: int = 3
    timeout_seconds: float = 180.0
    retry_count: int = 0
    include_llama_compatibility: bool = True
    cleanup_owner: str = CLEANUP_OWNER

    def validate(self) -> None:
        if not self.api_base_url.strip():
            raise ConfigError("api_base_url is required")
        if not self.api_key.strip():
            raise ConfigError("api_key is required")
        if not self.conversation_model_key.strip():
            raise ConfigError("conversation_model_key is required")
        if not self.reviewer_model_key.strip():
            raise ConfigError("reviewer_model_key is required")
        if not self.embedding_model_key.strip():
            raise ConfigError("embedding_model_key is required")
        if not 1 <= self.rounds <= 3:
            raise ConfigError("rounds must be between 1 and 3")
        if not 5 <= self.timeout_seconds <= 600:
            raise ConfigError("timeout_seconds must be between 5 and 600")
        if not 0 <= self.retry_count <= 5:
            raise ConfigError("retry_count must be between 0 and 5")
        if self.cleanup_owner != CLEANUP_OWNER:
            raise ConfigError("cleanup_owner is fixed by the task packet")


def load_config(path: Path | None = None) -> AcceptanceConfig:
    payload = _load_toml(path)
    config = AcceptanceConfig(
        api_base_url=_value(
            "API_BASE_URL", payload, "api_base_url", "http://127.0.0.1:8000"
        ).rstrip("/"),
        api_key=_value(
            "API_KEY",
            payload,
            "api_key",
            os.getenv("ADE_API_OPERATOR_KEY") or os.getenv("ADE_API_ADMIN_KEY") or "",
        ),
        output_dir=_project_path(
            _value(
                "OUTPUT_DIR",
                payload,
                "output_dir",
                "workflows/evals/agent_runtime_v3_acceptance/outputs",
            )
        ),
        database_url=(
            _nullable_value("DATABASE_URL", payload, "database_url")
            or str(os.getenv("ADE_API_DATABASE_URL") or "").strip()
            or None
        ),
        conversation_model_key=_value(
            "CONVERSATION_MODEL_KEY",
            payload,
            "conversation_model_key",
            DEFAULT_DGX_CHAT_MODEL,
        ),
        reviewer_model_key=_value(
            "REVIEWER_MODEL_KEY", payload, "reviewer_model_key", DEFAULT_DGX_CHAT_MODEL
        ),
        embedding_model_key=_value(
            "EMBEDDING_MODEL_KEY",
            payload,
            "embedding_model_key",
            DEFAULT_DGX_EMBEDDING_MODEL,
        ),
        llama_compatibility_model_key=_value(
            "LLAMA_COMPATIBILITY_MODEL_KEY",
            payload,
            "llama_compatibility_model_key",
            DEFAULT_LLAMA_COMPATIBILITY_MODEL,
        ),
        rounds=_int_value("ROUNDS", payload, "rounds", 3),
        timeout_seconds=_float_value(
            "TIMEOUT_SECONDS", payload, "timeout_seconds", 180
        ),
        retry_count=_int_value("RETRY_COUNT", payload, "retry_count", 0),
        include_llama_compatibility=_bool_value(
            "INCLUDE_LLAMA_COMPATIBILITY", payload, "include_llama_compatibility", True
        ),
        cleanup_owner=_value("CLEANUP_OWNER", payload, "cleanup_owner", CLEANUP_OWNER),
    )
    config.validate()
    return config


def with_overrides(config: AcceptanceConfig, **values: object) -> AcceptanceConfig:
    allowed = {key: value for key, value in values.items() if value is not None}
    result = replace(config, **allowed)
    result.validate()
    return result


def public_config(config: AcceptanceConfig) -> dict[str, object]:
    return {
        "api_base_url": config.api_base_url,
        "output_dir": str(config.output_dir),
        "database_url_configured": bool(config.database_url),
        "conversation_model_key": config.conversation_model_key,
        "reviewer_model_key": config.reviewer_model_key,
        "embedding_model_key": config.embedding_model_key,
        "llama_compatibility_model_key": config.llama_compatibility_model_key,
        "rounds": config.rounds,
        "timeout_seconds": config.timeout_seconds,
        "retry_count": config.retry_count,
        "include_llama_compatibility": config.include_llama_compatibility,
        "cleanup_owner": config.cleanup_owner,
    }


def _load_toml(path: Path | None) -> dict[str, Any]:
    selected = path or WORKFLOW_ROOT / "config.toml"
    if not selected.is_file():
        return {}
    with selected.open("rb") as handle:
        loaded = tomllib.load(handle)
    if not isinstance(loaded, dict):
        raise ConfigError("config must be a TOML table")
    return loaded


def _project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else WORKFLOW_ROOT.parents[2] / path


def _value(env_key: str, payload: dict[str, Any], key: str, default: str) -> str:
    return str(
        os.getenv(f"AGENT_RUNTIME_V3_ACCEPTANCE_{env_key}")
        or payload.get(key)
        or default
    ).strip()


def _nullable_value(env_key: str, payload: dict[str, Any], key: str) -> str | None:
    value = _value(env_key, payload, key, "")
    return value or None


def _int_value(env_key: str, payload: dict[str, Any], key: str, default: int) -> int:
    value = os.getenv(f"AGENT_RUNTIME_V3_ACCEPTANCE_{env_key}")
    return int(value if value is not None else payload.get(key, default))


def _float_value(
    env_key: str, payload: dict[str, Any], key: str, default: float
) -> float:
    value = os.getenv(f"AGENT_RUNTIME_V3_ACCEPTANCE_{env_key}")
    return float(value if value is not None else payload.get(key, default))


def _bool_value(env_key: str, payload: dict[str, Any], key: str, default: bool) -> bool:
    value = os.getenv(f"AGENT_RUNTIME_V3_ACCEPTANCE_{env_key}")
    raw = value if value is not None else payload.get(key, default)
    if isinstance(raw, bool):
        return raw
    normalized = str(raw).strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{key} must be a boolean")
