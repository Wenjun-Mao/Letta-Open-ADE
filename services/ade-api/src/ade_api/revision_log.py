from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ade_api.dependencies import REVISION_LOG_DIR, REVISION_LOG_FILE
from ade_api.registries.prompt_persona_store.codec import first_non_empty_line

_REVISION_LOG_LOCK = threading.Lock()


def _trim_preview(value: str, max_len: int = 180) -> str:
    line = first_non_empty_line(value)
    if len(line) <= max_len:
        return line
    return f"{line[:max_len]}..."


def append_prompt_persona_revision(
    *,
    agent_id: str,
    field: str,
    before: str,
    after: str,
    source: str,
) -> None:
    if before == after:
        return

    record = {
        "revision_id": str(uuid4()),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "field": field,
        "source": source,
        "before": before,
        "after": after,
        "before_preview": _trim_preview(before),
        "after_preview": _trim_preview(after),
        "before_length": len(before),
        "after_length": len(after),
        "delta_length": len(after) - len(before),
    }

    try:
        with _REVISION_LOG_LOCK:
            REVISION_LOG_DIR.mkdir(parents=True, exist_ok=True)
            with REVISION_LOG_FILE.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        return


def read_prompt_persona_revisions(
    *,
    agent_id: str | None,
    field: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    if not REVISION_LOG_FILE.exists():
        return []

    items: list[dict[str, Any]] = []
    try:
        with _REVISION_LOG_LOCK:
            lines = REVISION_LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue

            if agent_id and str(payload.get("agent_id", "") or "") != agent_id:
                continue
            if field and str(payload.get("field", "") or "") != field:
                continue
            items.append(payload)
    except OSError:
        return []

    if len(items) > limit:
        items = items[-limit:]
    items.reverse()
    return items
