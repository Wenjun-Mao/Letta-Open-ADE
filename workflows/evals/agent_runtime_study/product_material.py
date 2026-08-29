from __future__ import annotations

import json
from pathlib import Path

from content.prompts.system.chat.chat_v20260516 import (
    PROMPT as SOURCE_CHAT_SYSTEM_PROMPT,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHAT_PERSONA_KEY = "chat_linxiaotang"


def compile_ade_native_chat_prompt(source: str) -> str:
    """Remove prompt blocks whose behavior was implemented by Letta itself."""

    compiled = str(source or "")
    for tag in ("basic_functions", "memory"):
        opening = f"<{tag}>"
        closing = f"</{tag}>"
        if compiled.count(opening) != 1 or compiled.count(closing) != 1:
            raise RuntimeError(f"Expected exactly one <{tag}> prompt block")
        before, remainder = compiled.split(opening, 1)
        _, after = remainder.split(closing, 1)
        compiled = f"{before}{after}"
    if "PURE DIALOGUE ONLY" not in compiled or "<style>" not in compiled:
        raise RuntimeError("ADE-native prompt compilation lost product output rules")
    return "\n".join(line.rstrip() for line in compiled.strip().splitlines())


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
CHAT_SYSTEM_PROMPT = compile_ade_native_chat_prompt(SOURCE_CHAT_SYSTEM_PROMPT)

__all__ = [
    "CHAT_PERSONA",
    "CHAT_PERSONA_KEY",
    "CHAT_SYSTEM_PROMPT",
    "SOURCE_CHAT_SYSTEM_PROMPT",
    "compile_ade_native_chat_prompt",
]
