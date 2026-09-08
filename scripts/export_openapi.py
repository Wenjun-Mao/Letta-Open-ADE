from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _build_openapi_schema(project_root: Path) -> dict:
    sys.path.insert(0, str(project_root))
    from ade_api.main import app

    schema = app.openapi()

    if not schema.get("servers"):
        schema["servers"] = [
            {
                "url": "http://127.0.0.1:8000",
                "description": "Local ADE API",
            }
        ]

    return schema


def _check_artifact(path: Path, rendered: str) -> bool:
    if not path.exists():
        print(f"[FAIL] Missing OpenAPI artifact: {path}")
        return False

    existing = path.read_text(encoding="utf-8")
    if existing != rendered:
        print(f"[FAIL] OpenAPI artifact is out of date: {path}")
        return False

    print(f"[OK] OpenAPI artifact is current: {path}")
    return True


def _write_artifact(path: Path, rendered: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    print(f"[OK] OpenAPI artifact written: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export the canonical ADE API OpenAPI artifact."
    )
    parser.add_argument(
        "--output",
        default="docs/openapi/ade-api-openapi.json",
        help="Output OpenAPI JSON file path.",
    )
    parser.add_argument(
        "--frontend-output",
        default="apps/ade-web/public/openapi/ade-api-openapi.json",
        help="Secondary OpenAPI JSON path used by the ADE frontend.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: fail if committed artifact differs from generated schema.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    output_path = (project_root / args.output).resolve()
    frontend_output_path = (project_root / args.frontend_output).resolve()
    schema = _build_openapi_schema(project_root)
    paths = (output_path, frontend_output_path)

    if args.check:
        results = [_check_artifact(path, _canonical_json(schema)) for path in paths]
        if not all(results):
            print("Run: uv run python scripts/export_openapi.py")
            return 1

        return 0

    rendered = _canonical_json(schema)
    for path in paths:
        _write_artifact(path, rendered)
    print(
        f"[INFO] title={schema.get('info', {}).get('title')} "
        f"paths={len(schema.get('paths', {}))} "
        f"schemas={len(schema.get('components', {}).get('schemas', {}))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
