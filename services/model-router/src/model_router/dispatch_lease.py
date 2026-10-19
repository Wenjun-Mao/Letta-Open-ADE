"""Admission against an immutable operator activation and its close marker."""

import hashlib
import json
from pathlib import Path
import time
import math


class DispatchClosed(RuntimeError):
    pass


def check_dispatch_lease(root: Path | None, *, now: float | None = None) -> dict | None:
    if root is None:
        return None
    try:
        value = json.loads((root / "lease.json").read_bytes())
        seal = json.loads((root / "lease.seal.json").read_bytes())
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        if hashlib.sha256(encoded).hexdigest() != seal["sha256"]:
            raise ValueError("lease_changed")
        if (root / "closed.json").exists():
            raise ValueError("activation_closed")
        deadline = value["dispatch_deadline"]
        if type(deadline) is not int or deadline >= value["expires_at"]:
            raise ValueError("lease_invalid")
        observed = time.time() if now is None else now
        if not value["started_at"] <= observed < deadline:
            raise ValueError("dispatch_window_closed")
        checks = sorted((root / "checks").glob("*.json"))
        if not checks:
            raise ValueError("supervision_missing")
        heartbeat = json.loads(checks[-1].read_bytes())
        stamp = heartbeat.get("time")
        if (
            not isinstance(stamp, int | float)
            or not math.isfinite(stamp)
            or not 0 <= observed - stamp <= 60
            or heartbeat.get("issues") != []
            or heartbeat.get("activation_id") != value["activation_id"]
            or heartbeat.get("source_revision") != value["source_revision"]
        ):
            raise ValueError("supervision_stale_or_failed")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DispatchClosed("activation_unavailable_or_closed") from exc
    return value
