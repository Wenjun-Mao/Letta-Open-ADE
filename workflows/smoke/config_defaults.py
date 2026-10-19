from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _api_defaults() -> tuple[str, str]:
    # Imports must not install a private dotenv into unrelated callers' environment.
    values = dotenv_values(PROJECT_ROOT / ".env")

    def read(name: str, default: str) -> str:
        value = os.environ.get(name, values.get(name))
        return default if value is None else value

    return read("ADE_API_BASE_URL", "http://127.0.0.1:8000"), read(
        "ADE_API_ADMIN_KEY", ""
    ).strip()


# Test/runtime defaults used by suites and validation scripts.
DEFAULT_ADE_API_BASE_URL, DEFAULT_ADE_API_ADMIN_KEY = _api_defaults()
DEFAULT_PROMPT_KEY = "chat_v20260516"
DEFAULT_TEST_MODEL_KEY = "dgx_vllm::qwen3.6-35b-a3b-fp8"
DEFAULT_EMBEDDING_MODEL_KEY = "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B"


def ade_api_headers() -> dict[str, str]:
    if not DEFAULT_ADE_API_ADMIN_KEY:
        return {}
    return {"Authorization": f"Bearer {DEFAULT_ADE_API_ADMIN_KEY}"}
