from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ArtifactError(RuntimeError):
    pass


@dataclass(frozen=True)
class Artifact:
    path: Path
    sha256: str


class ArtifactWriter:
    """Write one immutable, content-addressed evidence bundle per parity run."""

    def __init__(self, output_dir: Path, run_id: str) -> None:
        self.root = output_dir / run_id
        self.root.mkdir(parents=True, exist_ok=False)

    def write_json(self, name: str, payload: dict[str, Any]) -> Artifact:
        path = self._path(name, ".json")
        material = dict(payload)
        material.pop("artifact_sha256", None)
        digest = sha256_json(material)
        _atomic_write(
            path, canonical_json_bytes({**material, "artifact_sha256": digest})
        )
        return Artifact(path=path, sha256=digest)

    def write_jsonl(self, name: str, rows: list[dict[str, Any]]) -> Artifact:
        path = self._path(name, ".jsonl")
        payload = b"".join(
            canonical_json_bytes(row).rstrip(b"\n") + b"\n" for row in rows
        )
        _atomic_write(path, payload)
        return Artifact(path=path, sha256=hashlib.sha256(payload).hexdigest())

    def _path(self, name: str, suffix: str) -> Path:
        if Path(name).name != name or not name:
            raise ArtifactError("artifact names must be plain filenames")
        path = self.root / f"{name}{suffix}"
        if path.exists():
            raise ArtifactError(f"immutable artifact already exists: {path}")
        return path


def canonical_json_bytes(payload: object) -> bytes:
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


def sha256_json(payload: object) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def verify_json_artifact(path: Path) -> bool:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return False
    actual = str(payload.pop("artifact_sha256", ""))
    return bool(actual) and actual == sha256_json(payload)


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp-{os.getpid()}")
    temporary.write_bytes(payload)
    temporary.replace(path)
