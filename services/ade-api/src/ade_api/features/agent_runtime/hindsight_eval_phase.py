"""Optional fail-closed phase marker for isolated Hindsight evaluation runs."""

from __future__ import annotations

import json
import os
import stat
import time
import uuid
from pathlib import Path

from .hindsight_eval_contracts import EvaluationError


def annotate(phase: str, correlation_id: str) -> dict | None:
    """Atomically publish a unique phase intent when the runner opts in."""
    target_value = os.environ.get("ADE_EVAL_PHASE_FILE")
    if not target_value:
        return None
    if phase not in {"recall", "character"}:
        raise EvaluationError("phase_invalid")
    if not correlation_id or len(correlation_id) > 256:
        raise EvaluationError("phase_invalid")
    target = Path(target_value)
    value = {
        "phase": phase,
        "operation_id": f"eval-{uuid.uuid4().hex}",
        "correlation_id": correlation_id,
        "time_ns": time.time_ns(),
    }
    try:
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if stat.S_IMODE(target.parent.stat().st_mode) != 0o700:
            raise OSError("phase_directory_mode")
        intent = target.parent / f"phase-{uuid.uuid4().hex}.intent.json"
        _exclusive_json(intent, value)
        temporary = target.parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
        _exclusive_json(temporary, value)
        os.replace(temporary, target)
        _fsync_directory(target.parent)
        return value
    except OSError as exc:
        raise EvaluationError("phase_capture_failed") from exc


def _exclusive_json(path: Path, value: dict) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
