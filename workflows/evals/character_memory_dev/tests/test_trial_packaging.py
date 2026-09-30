"""Private trial storage is mounted at runtime, never baked into images."""

from pathlib import Path


def test_private_trial_storage_is_excluded_from_docker_context() -> None:
    root = Path(__file__).resolve().parents[4]
    patterns = {
        line.strip()
        for line in (root / ".dockerignore").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert "workflows/evals/*/.trial/" in patterns
    assert "workflows/evals/*/outputs/" in patterns
    assert not any(
        pattern.startswith("!") and (".trial" in pattern or "outputs" in pattern)
        for pattern in patterns
    )
