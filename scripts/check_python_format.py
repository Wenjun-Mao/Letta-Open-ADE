from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path, PurePosixPath


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORMATTED_ROOTS = {
    "ade_core",
    "agent_platform_api",
    "evals",
    "model_router",
    "scripts",
    "tests",
}


def _git_lines(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def changed_python_files(base: str) -> list[str]:
    subprocess.run(
        ["git", "rev-parse", "--verify", f"{base}^{{commit}}"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    candidates = set(
        _git_lines("diff", "--name-only", "--diff-filter=ACMR", base, "--")
    )
    candidates.update(_git_lines("ls-files", "--others", "--exclude-standard"))
    return sorted(
        path
        for path in candidates
        if path.endswith(".py")
        and PurePosixPath(path).parts
        and PurePosixPath(path).parts[0] in FORMATTED_ROOTS
        and (PROJECT_ROOT / path).is_file()
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check Ruff formatting for Python files changed from a Git base."
    )
    parser.add_argument("--base", required=True, help="Git revision to compare against")
    args = parser.parse_args()

    files = changed_python_files(args.base)
    if not files:
        print("No changed Python files require formatting checks.")
        return 0

    ruff = shutil.which("ruff")
    if not ruff:
        raise RuntimeError("ruff is not available on PATH")
    print(f"Checking Ruff formatting for {len(files)} changed Python files.")
    return subprocess.call(
        [ruff, "format", "--check", *files],
        cwd=PROJECT_ROOT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
