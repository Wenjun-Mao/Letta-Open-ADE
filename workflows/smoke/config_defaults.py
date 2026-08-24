from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)

# Test/runtime defaults used by suites and validation scripts.
DEFAULT_ADE_API_BASE_URL = os.getenv("ADE_API_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_ADE_API_ADMIN_KEY = os.getenv("ADE_API_ADMIN_KEY", "").strip()
DEFAULT_PROMPT_KEY = "chat_v20260516"
DEFAULT_TEST_MODEL_HANDLE = "openai-proxy/local_llama_server::gemma4"
DEFAULT_EMBEDDING_HANDLE = "letta/letta-free"


def ade_api_headers() -> dict[str, str]:
    if not DEFAULT_ADE_API_ADMIN_KEY:
        return {}
    return {"Authorization": f"Bearer {DEFAULT_ADE_API_ADMIN_KEY}"}
