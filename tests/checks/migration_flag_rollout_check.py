from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from typing import Any

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dev_ui.main import app


@contextmanager
def _override_env(values: dict[str, str | None]):
    original: dict[str, str | None] = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def main() -> None:
    summary: dict[str, Any] = {
        "name": "migration_flag_rollout_check",
        "ok": False,
        "steps": {},
        "detail": "",
    }

    with TestClient(app) as http:
        with _override_env(
            {
                "AGENT_PLATFORM_API_ENABLED": "1",
                "AGENT_PLATFORM_LEGACY_API_ENABLED": "1",
                "AGENT_PLATFORM_MIGRATION_MODE": "dual",
                "AGENT_PLATFORM_STRICT_CAPABILITIES": "0",
            }
        ):
            response = http.get("/api/platform/migration-status")
            response.raise_for_status()
            payload = response.json()
            if payload.get("migration_mode") != "dual":
                raise RuntimeError("Expected dual mode under baseline env setup")
            summary["steps"]["baseline_dual_mode"] = {
                "ok": True,
                "payload": payload,
            }

        with _override_env(
            {
                "AGENT_PLATFORM_API_ENABLED": "0",
                "AGENT_PLATFORM_LEGACY_API_ENABLED": "1",
            }
        ):
            response = http.get("/api/platform/tools")
            if response.status_code != 503:
                raise RuntimeError("Expected /api/platform/tools to be blocked when platform API is disabled")
            detail = str(response.json().get("detail", "") or "")
            if "AGENT_PLATFORM_API_ENABLED" not in detail:
                raise RuntimeError("Platform disabled response did not include expected env flag detail")
            summary["steps"]["platform_disable_gate"] = {
                "ok": True,
                "status_code": response.status_code,
            }

        with _override_env(
            {
                "AGENT_PLATFORM_API_ENABLED": "1",
                "AGENT_PLATFORM_LEGACY_API_ENABLED": "0",
            }
        ):
            response = http.get("/api/options")
            if response.status_code != 503:
                raise RuntimeError("Expected /api/options to be blocked when legacy API is disabled")
            detail = str(response.json().get("detail", "") or "")
            if "AGENT_PLATFORM_LEGACY_API_ENABLED" not in detail:
                raise RuntimeError("Legacy disabled response did not include expected env flag detail")
            summary["steps"]["legacy_disable_gate"] = {
                "ok": True,
                "status_code": response.status_code,
            }

        with _override_env(
            {
                "AGENT_PLATFORM_API_ENABLED": "1",
                "AGENT_PLATFORM_LEGACY_API_ENABLED": "1",
                "AGENT_PLATFORM_MIGRATION_MODE": "unsupported-mode",
            }
        ):
            response = http.get("/api/platform/migration-status")
            response.raise_for_status()
            payload = response.json()
            if payload.get("migration_mode") != "dual":
                raise RuntimeError("Invalid migration mode should fall back to dual")
            summary["steps"]["invalid_mode_fallback"] = {
                "ok": True,
                "payload": payload,
            }

        with _override_env(
            {
                "AGENT_PLATFORM_API_ENABLED": "1",
                "AGENT_PLATFORM_LEGACY_API_ENABLED": "1",
                "AGENT_PLATFORM_MIGRATION_MODE": "legacy",
            }
        ):
            legacy_payload = http.get("/api/platform/migration-status")
            legacy_payload.raise_for_status()
            if legacy_payload.json().get("migration_mode") != "legacy":
                raise RuntimeError("Expected migration mode legacy")

        with _override_env(
            {
                "AGENT_PLATFORM_API_ENABLED": "1",
                "AGENT_PLATFORM_LEGACY_API_ENABLED": "1",
                "AGENT_PLATFORM_MIGRATION_MODE": "ade",
            }
        ):
            ade_payload = http.get("/api/platform/migration-status")
            ade_payload.raise_for_status()
            if ade_payload.json().get("migration_mode") != "ade":
                raise RuntimeError("Expected migration mode ade")

        summary["steps"]["mode_switch_rollout_and_rollback"] = {
            "ok": True,
            "verified_modes": ["legacy", "ade"],
        }

    summary["ok"] = True
    summary["detail"] = "Feature-flag rollout and rollback checks passed"
    print(_as_json(summary))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[FAIL] migration_flag_rollout_check: {exc}")
        raise
