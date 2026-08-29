from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RoundArtifact:
    round_path: Path
    events_path: Path
    sha256: str


class RoundArtifactWriter:
    def __init__(self, output_dir: Path, run_id: str) -> None:
        self.root = output_dir / run_id
        self.root.mkdir(parents=True, exist_ok=True)

    def write_round(
        self, index: int, payload: dict[str, Any], events: list[dict[str, Any]]
    ) -> RoundArtifact:
        kind = str(payload.get("kind") or "primary")
        directory_name = (
            f"round-{index:03d}" if kind == "primary" else f"{kind}-round-{index:03d}"
        )
        directory = self.root / directory_name
        directory.mkdir(parents=True, exist_ok=False)
        events_path = directory / "events.jsonl"
        self._write_json_lines(events_path, events)
        event_sha256 = _sha256(events_path.read_bytes())
        round_payload = {
            **payload,
            "created_at": datetime.now(UTC).isoformat(),
            "events_sha256": event_sha256,
        }
        digest = _sha256(_canonical_bytes(round_payload))
        materialized = {**round_payload, "artifact_sha256": digest}
        round_path = directory / "round.json"
        _atomic_write(round_path, _canonical_bytes(materialized))
        return RoundArtifact(
            round_path=round_path, events_path=events_path, sha256=digest
        )

    def write_provenance(self, payload: dict[str, Any]) -> tuple[Path, str]:
        digest = _sha256(_canonical_bytes(payload))
        path = self.root / "provenance.json"
        _atomic_write(path, _canonical_bytes({**payload, "provenance_sha256": digest}))
        return path, digest

    @staticmethod
    def _write_json_lines(path: Path, values: list[dict[str, Any]]) -> None:
        payload = b"".join(
            _canonical_bytes(value).rstrip(b"\n") + b"\n" for value in values
        )
        _atomic_write(path, payload)


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp-{os.getpid()}")
    temporary.write_bytes(payload)
    temporary.replace(path)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
