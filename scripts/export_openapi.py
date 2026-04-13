from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _build_openapi_schema(project_root: Path) -> dict:
    sys.path.insert(0, str(project_root))
    from dev_ui.main import app  # Imported lazily so script can run from any cwd.

    schema = app.openapi()

    if not schema.get("servers"):
        schema["servers"] = [
            {
                "url": "http://127.0.0.1:8284",
                "description": "Dev UI local",
            }
        ]

    return schema


def main() -> int:
    parser = argparse.ArgumentParser(description="Export canonical OpenAPI artifact for Agent Platform API.")
    parser.add_argument(
        "--output",
        default="docs/openapi/agent-platform-openapi.json",
        help="Output OpenAPI JSON file path.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: fail if committed artifact differs from generated schema.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    output_path = (project_root / args.output).resolve()

    schema = _build_openapi_schema(project_root)
    rendered = _canonical_json(schema)

    if args.check:
        if not output_path.exists():
            print(f"[FAIL] Missing OpenAPI artifact: {output_path}")
            print("Run: uv run python scripts/export_openapi.py")
            return 1

        existing = output_path.read_text(encoding="utf-8")
        if existing != rendered:
            print(f"[FAIL] OpenAPI artifact is out of date: {output_path}")
            print("Run: uv run python scripts/export_openapi.py")
            return 1

        print(f"[OK] OpenAPI artifact is current: {output_path}")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")

    print(f"[OK] OpenAPI artifact written: {output_path}")
    print(f"[INFO] paths={len(schema.get('paths', {}))} schemas={len(schema.get('components', {}).get('schemas', {}))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
