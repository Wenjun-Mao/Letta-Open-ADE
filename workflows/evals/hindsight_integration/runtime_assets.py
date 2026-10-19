"""Fresh private authoring assets seeded from the staged source, never incumbent state."""

import hashlib
import json
from pathlib import Path
import shutil

from .operations import create_record, encoded


def manifest(root: Path) -> dict:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Candidate content seed must be a real directory")
    files = {}
    for path in sorted(root.rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError("Candidate content seed cannot contain symlinks")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    if not files:
        raise ValueError("Candidate content seed is empty")
    return {"files": files, "sha256": hashlib.sha256(encoded(files)).hexdigest()}


def seed_runtime_assets(activation_root: Path, source: Path) -> dict:
    original = manifest(source)
    target = activation_root / "runtime-data/content"
    shutil.copytree(
        source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    if manifest(target) != original:
        raise ValueError("Candidate content copy differs from its source")
    receipt = {"schema_version": 1, "source_path": str(source), **original}
    create_record(activation_root / "runtime-assets.json", receipt)
    return receipt


def require_runtime_assets(activation_root: Path) -> None:
    receipt = json.loads((activation_root / "runtime-assets.json").read_bytes())
    observed = manifest(activation_root / "runtime-data/content")
    if (
        receipt.get("schema_version") != 1
        or observed["files"] != receipt["files"]
        or observed["sha256"] != receipt["sha256"]
    ):
        raise ValueError("Candidate initial authoring assets changed")
