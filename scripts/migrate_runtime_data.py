from __future__ import annotations

import argparse
import shutil
from pathlib import Path


MIGRATIONS = (
    (
        Path("data/personas/personas.sqlite3"),
        Path("data/runtime/personas/personas.sqlite3"),
    ),
    (
        Path("data/agent_lifecycle/registry.json"),
        Path("data/runtime/agent-lifecycle/registry.json"),
    ),
)


def migrate_file(
    project_root: Path,
    source_relative: Path,
    destination_relative: Path,
    *,
    remove_source: bool = False,
    dry_run: bool = False,
) -> str:
    source = project_root / source_relative
    destination = project_root / destination_relative
    if not source.is_file():
        return f"skip {source_relative} (not found)"

    if destination.exists():
        if not destination.is_file() or source.read_bytes() != destination.read_bytes():
            raise RuntimeError(
                f"Refusing to replace conflicting runtime data: {destination_relative}"
            )
        action = "verified"
    else:
        action = "copy"
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    if remove_source:
        action += " and remove source"
        if not dry_run:
            source.unlink()
            try:
                source.parent.rmdir()
            except OSError:
                pass

    prefix = "would " if dry_run else ""
    return f"{prefix}{action} {source_relative} -> {destination_relative}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate pre-data/runtime ADE state without overwriting conflicts."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to the parent of scripts/.",
    )
    parser.add_argument(
        "--remove-source",
        action="store_true",
        help="Delete a legacy source only after its destination is copied or verified identical.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report actions without changing files."
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    try:
        for source, destination in MIGRATIONS:
            print(
                migrate_file(
                    project_root,
                    source,
                    destination,
                    remove_source=args.remove_source,
                    dry_run=args.dry_run,
                )
            )
    except RuntimeError as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
