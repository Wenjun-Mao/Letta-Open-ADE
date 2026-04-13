from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load_json(path: Path) -> dict[str, Any]:
    _require(path.exists(), f"Missing JSON file: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(payload, dict), f"Expected JSON object: {path}")
    return payload


def _resolve_openapi_paths(api_config: dict[str, Any]) -> list[str]:
    openapi_value = api_config.get("openapi")
    if isinstance(openapi_value, str):
        return [openapi_value]
    if isinstance(openapi_value, list):
        return [str(item) for item in openapi_value]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate docs.json and referenced OpenAPI artifact(s).")
    parser.add_argument("--docs", default="docs/docs.json", help="Path to Mintlify docs.json")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    docs_path = (project_root / args.docs).resolve()
    docs_root = docs_path.parent

    config = _load_json(docs_path)

    _require(bool(config.get("$schema")), "docs.json missing '$schema'")
    _require(bool(config.get("name")), "docs.json missing 'name'")
    _require(isinstance(config.get("navigation"), list), "docs.json 'navigation' must be a list")

    api_config = config.get("api")
    _require(isinstance(api_config, dict), "docs.json missing 'api' object")

    openapi_paths = _resolve_openapi_paths(api_config)
    _require(len(openapi_paths) > 0, "docs.json api.openapi must define at least one OpenAPI source")

    for openapi_path in openapi_paths:
        # Skip remote URL checks; those should be handled by remote availability checks.
        if openapi_path.startswith("http://") or openapi_path.startswith("https://"):
            continue

        resolved = (docs_root / openapi_path).resolve()
        schema = _load_json(resolved)
        _require(bool(schema.get("openapi")), f"OpenAPI file missing 'openapi' field: {resolved}")
        _require(isinstance(schema.get("paths"), dict), f"OpenAPI file missing 'paths' object: {resolved}")

    print(f"[OK] docs config valid: {docs_path}")
    print(f"[OK] openapi references checked: {len(openapi_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
