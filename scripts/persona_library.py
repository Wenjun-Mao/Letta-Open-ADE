from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_platform_api.registries.persona_sqlite import PersonaSqliteRegistry


def _project_root() -> Path:
    return PROJECT_ROOT


def _registry(args: argparse.Namespace) -> PersonaSqliteRegistry:
    project_root = _project_root()
    db_path = Path(args.db_path)
    if not db_path.is_absolute():
        db_path = project_root / db_path
    seed_path = Path(args.seed_jsonl)
    if not seed_path.is_absolute():
        seed_path = project_root / seed_path
    return PersonaSqliteRegistry(project_root, db_path=db_path, seed_jsonl_path=seed_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import/export ADE SQLite persona library data.")
    parser.add_argument("--db-path", default="data/personas/personas.sqlite3")
    parser.add_argument("--seed-jsonl", default="agent_platform_api/seed_data/personas.jsonl")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import-jsonl", help="Import personas from JSONL.")
    import_parser.add_argument("--input", required=True)
    import_parser.add_argument("--on-conflict", choices=["error", "skip", "upsert"], default="error")

    export_parser = subparsers.add_parser("export-jsonl", help="Export personas to JSONL.")
    export_parser.add_argument("--output", required=True)
    export_parser.add_argument("--scenario", choices=["chat", "comment"], default=None)
    export_parser.add_argument("--include-archived", action="store_true")

    markdown_parser = subparsers.add_parser("export-markdown", help="Export personas to Markdown.")
    markdown_parser.add_argument("--output", required=True)
    markdown_parser.add_argument("--scenario", choices=["chat", "comment"], default=None)
    markdown_parser.add_argument("--include-archived", action="store_true")

    args = parser.parse_args()
    registry = _registry(args)

    if args.command == "import-jsonl":
        result = registry.import_jsonl(Path(args.input), on_conflict=args.on_conflict)
        print(result)
        return
    if args.command == "export-jsonl":
        count = registry.export_jsonl(
            Path(args.output),
            include_archived=args.include_archived,
            scenario=args.scenario,
        )
        print(f"exported {count} personas")
        return
    if args.command == "export-markdown":
        count = registry.export_markdown(
            Path(args.output),
            include_archived=args.include_archived,
            scenario=args.scenario,
        )
        print(f"exported {count} personas")
        return

    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
