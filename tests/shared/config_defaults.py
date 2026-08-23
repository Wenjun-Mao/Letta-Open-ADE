from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)

# Test/runtime defaults used by suites and validation scripts.
DEFAULT_LETTA_BASE_URL = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
DEFAULT_AGENT_PLATFORM_API_BASE_URL = os.getenv("AGENT_PLATFORM_API_BASE_URL", "http://127.0.0.1:8284")
DEFAULT_AGENT_PLATFORM_API_KEY = os.getenv("AGENT_PLATFORM_API_KEY", "").strip()
DEFAULT_PROMPT_KEY = "chat_v20260516"
DEFAULT_TEST_MODEL_HANDLE = "openai-proxy/local_llama_server::gemma4"
DEFAULT_EMBEDDING_HANDLE = "letta/letta-free"


def agent_platform_headers() -> dict[str, str]:
    if not DEFAULT_AGENT_PLATFORM_API_KEY:
        return {}
    return {"Authorization": f"Bearer {DEFAULT_AGENT_PLATFORM_API_KEY}"}
