"""Release-scoped P4 restart evidence paths for the stdlib host workflow."""

from __future__ import annotations

from pathlib import Path

FILES = {
    "selection": "restart-selection.json",
    "before": "restart-readback.before.json",
    "after": "restart-readback.after.json",
    "completed": "restart-readback.completed.json",
}


def _release_sha(value: str) -> str:
    if (not isinstance(value, str) or len(value) != 40
            or any(character not in "0123456789abcdef" for character in value)):
        raise RuntimeError("p4_evidence_release_identity_invalid")
    return value


def path_for(directory: Path, release_sha: str, artifact: str) -> Path:
    release_sha = _release_sha(release_sha)
    try:
        filename = FILES[artifact]
    except KeyError as exc:
        raise RuntimeError("p4_evidence_artifact_invalid") from exc
    return directory.parent / "p4" / release_sha / filename


def reference(directory: Path, release_sha: str, artifact: str) -> dict:
    path = path_for(directory, release_sha, artifact)
    return {"path": f"../p4/{release_sha}/{path.name}", "release_sha": release_sha}


def resolve_reference(directory: Path, reference_value: dict, release_sha: str,
                      artifact: str) -> Path:
    expected = reference(directory, release_sha, artifact)
    if (not isinstance(reference_value, dict)
            or reference_value.get("release_sha") != expected["release_sha"]
            or reference_value.get("path") != expected["path"]):
        raise RuntimeError("p4_evidence_reference_invalid")
    path = path_for(directory, release_sha, artifact)
    namespace = path.parent
    if any(parent.is_symlink() for parent in (directory.parent / "p4", namespace, path)):
        raise RuntimeError("p4_evidence_path_invalid")
    return path
