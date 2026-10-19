"""Opt-in synthetic-workspace snapshots; never ordinary activity or product state."""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from uuid import UUID


PRIVATE_FIELDS = frozenset(
    {
        "authorization",
        "api_key",
        "access_token",
        "refresh_token",
        "password",
        "reasoning_content",
        "encrypted_content",
        "client_secret",
    }
)


def contains_private_fields(value: object) -> bool:
    if isinstance(value, dict):
        return any(str(key).lower() in PRIVATE_FIELDS for key in value) or any(
            contains_private_fields(item) for item in value.values()
        )
    return isinstance(value, (list, tuple)) and any(
        contains_private_fields(item) for item in value
    )


def encoded(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    ).encode()


def capture_root(settings) -> Path | None:
    root = getattr(settings, "agent_runtime_observation_root", "")
    if not root:
        return None
    if (
        settings.agent_runtime_mode != "development"
        or not settings.agent_runtime_workspace_key
        or settings.agent_runtime_workspace_key == "default"
        or not Path(root).is_absolute()
        or not settings.auth_enabled
        or not (settings.operator_key or settings.admin_key)
    ):
        raise ValueError(
            "Private capture requires an authenticated explicit development workspace and absolute root"
        )
    return Path(root)


class AttemptObservation:
    def __init__(self, root: Path, identity: dict):
        self.identity = identity
        self.path = (
            root / str(UUID(identity["run_id"])) / str(UUID(identity["attempt_id"]))
        )
        self.sequence = 0
        self.failed = False
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        _require_private_directory(root)
        self.path.parent.mkdir(exist_ok=True, mode=0o700)
        _require_private_directory(self.path.parent)

    def record(self, event_type: str, value: dict) -> bool:
        self.sequence += 1
        private = contains_private_fields(value)
        record = {
            "schema_version": 1,
            "identity": self.identity,
            "sequence": self.sequence,
            "recorded_at": time.time(),
            "type": event_type,
            "input_complete": not private,
            "value": {"limitation": "private_fields_excluded"} if private else value,
        }
        envelope = {
            "record": record,
            "sha256": hashlib.sha256(encoded(record)).hexdigest(),
        }
        temporary = None
        try:
            self.path.mkdir(parents=True, exist_ok=True, mode=0o700)
            _require_private_directory(self.path)
            descriptor, temporary = tempfile.mkstemp(prefix=".capture-", dir=self.path)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded(envelope) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, self.path / f"{self.sequence:06d}.json")
        except (OSError, ValueError, TypeError):
            self.failed = True
            return False
        finally:
            if temporary:
                os.unlink(temporary)
        self.failed |= private
        return not private


def read_attempts(root: Path, run_id: str, workspace_id: str) -> list[dict]:
    _require_private_directory(root)
    run_path = root / str(UUID(run_id))
    attempts = []
    for attempt_path in sorted(run_path.iterdir()) if run_path.exists() else ():
        _require_private_directory(attempt_path)
        attempt_id = str(UUID(attempt_path.name))
        records = []
        for path in sorted(attempt_path.glob("*.json")):
            if path.is_symlink():
                raise ValueError("Invalid private observation path")
            envelope = json.loads(path.read_bytes())
            record = envelope["record"]
            identity = record["identity"]
            if (
                envelope["sha256"] != hashlib.sha256(encoded(record)).hexdigest()
                or identity["run_id"] != run_id
                or identity["workspace_id"] != workspace_id
                or identity["attempt_id"] != attempt_id
                or record["sequence"] != len(records) + 1
                or type(record["sequence"]) is not int
                or contains_private_fields(record)
            ):
                raise ValueError("Invalid private observation")
            records.append(record)
        attempts.append({"attempt_id": attempt_id, "records": records})
    return attempts


def _require_private_directory(path: Path) -> None:
    if (
        path.is_symlink()
        or path.stat().st_uid != os.geteuid()
        or path.stat().st_mode & 0o077
    ):
        raise ValueError(
            "Observation directory must already be private and operator-owned"
        )
