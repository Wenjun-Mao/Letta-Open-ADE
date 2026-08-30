from __future__ import annotations

import argparse
import hashlib
import os
import stat
import subprocess
from collections.abc import Iterable
from pathlib import Path


def git_visible_paths(project_root: Path) -> tuple[bytes, ...]:
    """Return tracked and unignored untracked paths as Git represents them."""

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
    return tuple(sorted(path for path in output.split(b"\0") if path))


def source_fingerprint(project_root: Path, paths: Iterable[bytes] | None = None) -> str:
    """Hash exact Git-visible path state without relying on the Git index blob."""

    root = project_root.resolve()
    visible_paths = tuple(
        sorted(paths if paths is not None else git_visible_paths(root))
    )
    digest = hashlib.sha256()
    digest.update(b"ade-source-fingerprint-v1\0")
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
        description="Print the exact Git-visible ADE source-tree fingerprint."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    print(source_fingerprint(args.root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
