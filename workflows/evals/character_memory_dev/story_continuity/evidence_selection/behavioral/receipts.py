"""Exclusive, durable private capture and committed source identity."""

import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

from .contracts import DIRECTORY, ROOT, digest, load_prepared

OUTPUTS = DIRECTORY / "outputs"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_once(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def read(path: Path):
    return json.loads(path.read_bytes())


def require_private(directory: Path) -> Path:
    directory = directory.absolute()
    if (
        directory.name != "d04-comparison"
        or directory.parent != OUTPUTS
        or directory.is_symlink()
        or OUTPUTS.is_symlink()
        or directory.resolve().parent != OUTPUTS.resolve()
    ):
        raise ValueError("Use a direct nonsymlink child of behavioral/outputs")
    return directory


def source_receipt() -> dict:
    prepared = load_prepared()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT):
        raise ValueError("Clean committed reviewed protocol/request freeze required")
    return {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT)
        .decode()
        .strip(),
        "preparation_sha256": digest(prepared),
        "requests_sha256": prepared["requests_sha256"],
    }
