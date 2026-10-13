"""Strict, content-bound, create-only local evidence files.

Seals detect accidental drift, not malicious provenance rewriting. No signing
or remote authenticity claim is made by this offline artifact format.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def json_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(json_bytes(value)).hexdigest()


def _unique_keys(pairs: list[tuple[str, object]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def _invalid_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON number: {value}")


def read_json(path: Path) -> dict:
    if path.is_symlink():
        raise ValueError(f"Evidence file must not be a symlink: {path}")
    raw = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_keys,
        parse_constant=_invalid_constant,
    )
    if not isinstance(raw, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return raw


def model_from_json(model: type[T], value: object) -> T:
    # JSON-mode accepts ISO timestamps while preserving strict scalar types.
    return model.model_validate_json(json_bytes(value))


def write_new(path: Path, value: object) -> None:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    raw = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    write_bytes_new(path, raw)


def write_bytes_new(path: Path, raw: bytes) -> None:
    """Publish complete bytes without replacing even a concurrent writer's file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".writing-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


def seal(kind: str, payload: BaseModel | dict) -> dict:
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    envelope = {"kind": kind, "format_version": 1, "payload": payload}
    return {**envelope, "sha256": digest(envelope)}


def load_sealed(path: Path, kind: str, model: type[T]) -> tuple[T, str]:
    raw = read_json(path)
    if set(raw) != {"kind", "format_version", "payload", "sha256"}:
        raise ValueError(f"Malformed sealed record: {path}")
    if (
        raw["kind"] != kind
        or type(raw["format_version"]) is not int
        or raw["format_version"] != 1
    ):
        raise ValueError(f"Unsupported {kind} record: {path}")
    expected = digest({key: raw[key] for key in ("kind", "format_version", "payload")})
    if raw["sha256"] != expected:
        raise ValueError(f"Changed/corrupt sealed record: {path}")
    return model_from_json(model, raw["payload"]), expected
