from __future__ import annotations

import json
from pathlib import Path

from content.prompts.system.chat.chat_v20260516 import PROMPT as CHAT_SYSTEM_PROMPT


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHAT_PERSONA_KEY = "chat_linxiaotang"


def load_chat_persona() -> str:
    path = PROJECT_ROOT / "content" / "personas" / "personas.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if item.get("key") == CHAT_PERSONA_KEY and not item.get("archived", False):
            return str(item.get("content") or "").strip()
    raise RuntimeError(f"Active persona not found: {CHAT_PERSONA_KEY}")


CHAT_PERSONA = load_chat_persona()

__all__ = ["CHAT_PERSONA", "CHAT_PERSONA_KEY", "CHAT_SYSTEM_PROMPT"]
