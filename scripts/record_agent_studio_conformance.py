from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ade_api.features.agent_runtime_v3.release_evidence import (
    REQUIRED_CONFORMANCE_TESTS as CONFORMANCE_TESTS,
    canonical_sha256,
)
from scripts.source_fingerprint import source_fingerprint


def record_conformance(
    *,
    project_root: Path,
    output_path: Path,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    revision = _git(project_root, "rev-parse", "HEAD")
    dirty = bool(_git(project_root, "status", "--porcelain"))
    command = [sys.executable, "-m", "pytest", *CONFORMANCE_TESTS, "-q"]
    completed = run(
        command,
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    output = f"{completed.stdout}\n{completed.stderr}".strip()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "kind": "ade-agent-studio-conformance-receipt",
        "source_revision": revision,
        "source_dirty": dirty,
        "source_fingerprint": source_fingerprint(project_root),
        "completed_at": now().astimezone(UTC).isoformat(),
        "passed": completed.returncode == 0 and not dirty,
        "exit_code": completed.returncode,
        "test_paths": list(CONFORMANCE_TESTS),
        "command": command,
        "output_sha256": canonical_sha256(output),
    }
    payload["artifact_sha256"] = canonical_sha256(payload)
    _atomic_write(output_path, payload)
    return payload


def _git(project_root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=project_root,
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the deterministic Agent Studio retry, cancellation, idempotency, "
            "and trace contracts and write a content-addressed receipt."
        )
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = record_conformance(
        project_root=PROJECT_ROOT,
        output_path=args.output,
    )
    print(
        f"Agent Studio conformance passed={receipt['passed']} "
        f"artifact={receipt['artifact_sha256']}"
    )
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
