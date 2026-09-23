from __future__ import annotations

import argparse
import hashlib
import os
import stat
import subprocess
from collections.abc import Iterable
from pathlib import Path


GOVERNED_SOURCE_ROOTS = (
    "content/personas/",
    "content/prompts/system/chat/",
    "packages/agent-runtime-eval-contracts/src/",
    "packages/model-catalog-contracts/src/",
    "services/ade-api/migrations/versions/",
    "services/ade-api/src/ade_api/features/agent_runtime/",
    "services/ade-api/src/ade_api/features/model_catalog/",
    "services/ade-api/src/ade_api/features/prompt_center/",
    "services/ade-api/src/ade_api/integrations/model_router/",
    "services/ade-api/src/ade_api/platform/",
    "services/model-router/src/model_router/",
)
GOVERNED_SOURCE_FILES = frozenset(
    {
        "compose.yaml",
        "config/model-router/model-profiles.json",
        "config/model-router/sources.json",
        "pyproject.toml",
        "uv.lock",
        "services/ade-api/Dockerfile",
        "services/ade-api/alembic.ini",
        "services/ade-api/migrations/env.py",
        "services/ade-api/pyproject.toml",
        "services/model-router/Dockerfile",
        "services/model-router/pyproject.toml",
        "scripts/check_agent_studio_release_gate.py",
        "scripts/embedding_space_compatibility.py",
        "scripts/promote_agent_studio_release.py",
        "scripts/rebind_agent_runtime_policy.py",
        "scripts/record_agent_studio_conformance.py",
        "scripts/source_fingerprint.py",
    }
)


def git_visible_paths(project_root: Path) -> tuple[bytes, ...]:
    """Return governed tracked and unignored paths as Git represents them."""

    output = subprocess.check_output(
        [
            "git",
            "-C",
            os.fspath(project_root),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ]
    )
    return tuple(
        sorted(
            path
            for path in output.split(b"\0")
            if path and is_governed_source_path(os.fsdecode(path))
        )
    )


def is_governed_source_path(path: str) -> bool:
    normalized = Path(path).as_posix().lstrip("./")
    return normalized in GOVERNED_SOURCE_FILES or normalized.startswith(
        GOVERNED_SOURCE_ROOTS
    )


def source_fingerprint(project_root: Path, paths: Iterable[bytes] | None = None) -> str:
    """Hash exact governed path state without relying on Git index blobs."""

    root = project_root.resolve()
    visible_paths = tuple(
        sorted(paths if paths is not None else git_visible_paths(root))
    )
    digest = hashlib.sha256()
    digest.update(b"ade-governed-source-fingerprint-v2\0")
    for raw_path in visible_paths:
        relative = os.fsdecode(raw_path)
        path = root / relative
        digest.update(len(raw_path).to_bytes(8, "big"))
        digest.update(raw_path)
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            _update_record(digest, b"missing", b"")
            continue
        if stat.S_ISLNK(metadata.st_mode):
            _update_record(digest, b"symlink", os.fsencode(os.readlink(path)))
            continue
        if stat.S_ISREG(metadata.st_mode):
            kind = b"executable" if metadata.st_mode & stat.S_IXUSR else b"file"
            _update_record(digest, kind, path.read_bytes())
            continue
        _update_record(digest, b"unsupported", b"")
    return digest.hexdigest()


def _update_record(digest: hashlib._Hash, kind: bytes, content: bytes) -> None:
    digest.update(len(kind).to_bytes(2, "big"))
    digest.update(kind)
    digest.update(len(content).to_bytes(8, "big"))
    digest.update(content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print the governed ADE runtime source fingerprint."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    print(source_fingerprint(args.root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
