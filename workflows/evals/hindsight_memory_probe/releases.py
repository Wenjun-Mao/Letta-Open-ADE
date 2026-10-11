"""Clean SHA release verification and explicit owned release admission."""

import hashlib
import json
import re
from pathlib import Path

PARENT = Path("/mnt/projects/apps/ade-hindsight-probe/releases")


def validate_path(release):
    release = Path(release).resolve()
    if release.parent != PARENT or not re.fullmatch("[a-f0-9]{40}", release.name):
        raise RuntimeError("clean_sha_release_path_required")
    return release


def verify(release):
    release = validate_path(release)
    manifest = json.loads((release / ".probe-release.json").read_text())
    if manifest["source_sha"] != release.name or manifest["source_dirty"] is not False:
        raise RuntimeError("clean_release_manifest_required")
    for name, expected in manifest["file_sha256"].items():
        path = release / name
        if release not in path.resolve().parents or path.is_symlink():
            raise RuntimeError("release_file_escaped")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError("release_file_hash_changed")
    return manifest
