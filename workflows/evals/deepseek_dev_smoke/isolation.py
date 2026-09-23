"""Official-provider and disposable-database guards for synthetic probes."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

from model_router.settings import ModelRouterSettings, RouterSourceConfig


ROOT = Path(__file__).resolve().parents[3]


def isolated_database_url(database_url: str) -> tuple[str, str]:
    url = make_url(database_url)
    if (
        url.drivername != "postgresql+psycopg"
        or url.host not in {"localhost", "127.0.0.1", "::1"}
        or url.username != "ade_owner"
        or url.password is not None
        or not re.fullmatch(r"ade_m2_memory_test_[0-9a-f]{8,}", url.database or "")
    ):
        raise ValueError(
            "Binding requires the disposable passwordless loopback test DB"
        )
    return database_url, str(url.database)


def router_settings(env_file: Path, *, include_spark: bool) -> ModelRouterSettings:
    values = dotenv_values(env_file)
    key = str(values.get("DEEPSEEK_API_KEY") or "").strip()
    base = str(values.get("DEEPSEEK_API_BASE") or "https://api.deepseek.com").strip()
    parsed = urlsplit(base)
    if not key or parsed.scheme != "https" or parsed.hostname != "api.deepseek.com":
        raise ValueError("Official DeepSeek key/base URL is not configured")
    os.environ["DEEPSEEK_API_KEY"] = key
    os.environ["DEEPSEEK_API_BASE"] = base
    sources = json.loads((ROOT / "config/model-router/sources.json").read_text())
    selected = [next(item for item in sources if item["id"] == "deepseek")]
    if include_spark:
        host = str(values.get("DGX_SPARK_HOST") or "").strip()
        if not host or "/" in host or "@" in host:
            raise ValueError("Spark host is not configured for isolated binding")
        embedding_key = str(values.get("DGX_EMBEDDING_API_KEY") or "").strip()
        if embedding_key:
            os.environ["DGX_EMBEDDING_API_KEY"] = embedding_key
        spark = next(item for item in sources if item["id"] == "dgx_embedding_sidecar")
        selected.append({**spark, "base_url": f"http://{host}:8001/v1"})
    return ModelRouterSettings(
        sources=[RouterSourceConfig.model_validate(item) for item in selected],
        api_key="",
        api_key_secret="",
        request_timeout_seconds=180,
    )
