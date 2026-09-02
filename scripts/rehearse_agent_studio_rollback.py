from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Sequence

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ade_api.features.agent_runtime_v3.release_evidence import canonical_sha256
from scripts.agent_studio_rollback_state import (
    get_json as _get_json,
    snapshot_native_state as _snapshot_native_state,
    wait_for_native as _wait_for_native,
)
from scripts.agent_studio_rollback_web import verify_legacy_web as _verify_legacy_web
from scripts.source_fingerprint import source_fingerprint


def rehearse_rollback(
    *,
    project_root: Path,
    legacy_revision: str,
    legacy_base_url: str,
    native_base_url: str,
    legacy_api_key: str,
    native_api_key: str,
    compose_network: str,
    output_path: Path,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    owned_client = client is None
    http = client or httpx.Client(timeout=15)
    revision = _git(project_root, "rev-parse", "HEAD")
    dirty = bool(_git(project_root, "status", "--porcelain"))
    steps: list[dict[str, Any]] = []
    stopped = False
    state_before_sha256 = ""
    state_after_sha256 = ""
    legacy_health_passed = False
    legacy_web_image_built = False
    legacy_web_smoke_passed = False
    legacy_web_api_read_passed = False
    legacy_web_api_write_passed = False
    legacy_web_api_cleanup_passed = False
    native_state_preserved = False
    legacy_source_verified = False
    error_code: str | None = None
    try:
        if dirty:
            raise RuntimeError("dirty_source")
        legacy_source = _git_show(
            project_root,
            legacy_revision,
            "apps/ade-web/src/features/agent-studio/api.ts",
        )
        legacy_source_verified = "/api/v2/agent-studio/" in legacy_source
        if not legacy_source_verified:
            raise RuntimeError("legacy_source_unavailable")
        legacy_web = _verify_legacy_web(
            project_root=project_root,
            legacy_revision=legacy_revision,
            compose_network=compose_network,
            legacy_api_key=legacy_api_key,
            command_runner=command_runner,
            client=http,
            sleep=sleep,
        )
        legacy_web_image_built = legacy_web.image_built
        legacy_web_smoke_passed = legacy_web.smoke_passed
        legacy_web_api_read_passed = legacy_web.api_read_passed
        legacy_web_api_write_passed = legacy_web.api_write_passed
        legacy_web_api_cleanup_passed = legacy_web.api_cleanup_passed
        if not legacy_web_image_built or not legacy_web_smoke_passed:
            raise RuntimeError("legacy_web_unavailable")
        steps.append({"step": "verify_prior_v2_web_release", "passed": True})
        before = _snapshot_native_state(
            http,
            native_base_url,
            native_api_key,
        )
        state_before_sha256 = canonical_sha256(before)
        steps.append({"step": "snapshot_native_state", "passed": True})

        _compose(
            command_runner,
            project_root,
            "stop",
            "ade-runtime-worker",
            "ade-native-api",
        )
        stopped = True
        steps.append({"step": "withdraw_native_lane", "passed": True})
        legacy_health = _get_json(
            http,
            f"{legacy_base_url.rstrip('/')}/api/v2/health",
            legacy_api_key,
        )
        legacy_health_passed = str(legacy_health.get("status") or "").casefold() in {
            "ok",
            "healthy",
        }
        if not legacy_health_passed:
            raise RuntimeError("legacy_health_failed")
        steps.append({"step": "verify_legacy_lane", "passed": True})
    except Exception as exc:
        error_code = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
    finally:
        if stopped:
            try:
                _compose(
                    command_runner,
                    project_root,
                    "up",
                    "-d",
                    "ade-runtime-worker",
                    "ade-native-api",
                )
                _wait_for_native(http, native_base_url, native_api_key, sleep=sleep)
                after = _snapshot_native_state(
                    http,
                    native_base_url,
                    native_api_key,
                )
                state_after_sha256 = canonical_sha256(after)
                native_state_preserved = state_after_sha256 == state_before_sha256
                steps.append(
                    {
                        "step": "restore_native_lane_without_state_mutation",
                        "passed": native_state_preserved,
                    }
                )
            except Exception as exc:
                error_code = error_code or (
                    str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
                )
        if owned_client:
            http.close()

    passed = (
        not dirty
        and legacy_source_verified
        and legacy_web_image_built
        and legacy_web_smoke_passed
        and stopped
        and legacy_health_passed
        and native_state_preserved
        and error_code is None
    )
    payload: dict[str, Any] = {
        "schema_version": 1,
        "kind": "ade-agent-studio-rollback-rehearsal",
        "source_revision": revision,
        "source_dirty": dirty,
        "source_fingerprint": source_fingerprint(project_root),
        "legacy_revision": legacy_revision,
        "rehearsed_at": now().astimezone(UTC).isoformat(),
        "rehearsed": passed,
        "legacy_source_verified": legacy_source_verified,
        "legacy_web_image_built": legacy_web_image_built,
        "legacy_web_smoke_passed": legacy_web_smoke_passed,
        "legacy_web_api_read_passed": legacy_web_api_read_passed,
        "legacy_web_api_write_passed": legacy_web_api_write_passed,
        "legacy_web_api_cleanup_passed": legacy_web_api_cleanup_passed,
        "legacy_health_passed": legacy_health_passed,
        "native_state_preserved": native_state_preserved,
        "native_state_before_sha256": state_before_sha256,
        "native_state_after_sha256": state_after_sha256,
        "steps": steps,
        "error_code": error_code,
    }
    payload["receipt_sha256"] = canonical_sha256(payload)
    _atomic_write(output_path, payload)
    return payload


def _compose(
    runner: Callable[..., subprocess.CompletedProcess[str]],
    project_root: Path,
    *args: str,
) -> None:
    completed = runner(
        ["docker", "compose", *args],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("compose_command_failed")


def _git(project_root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=project_root, text=True, stderr=subprocess.DEVNULL
    ).strip()


def _git_show(project_root: Path, revision: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{revision}:{path}"],
        cwd=project_root,
        text=True,
        stderr=subprocess.DEVNULL,
    )


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
            "Rehearse release-level Agent Studio rollback by withdrawing the native "
            "lane, proving v2 health, restoring v3, and comparing its state."
        )
    )
    parser.add_argument("--legacy-revision", required=True)
    parser.add_argument("--legacy-base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--native-base-url", default="http://127.0.0.1:8002")
    parser.add_argument("--compose-network", default="letta-open-ade_default")
    parser.add_argument("--legacy-api-key", default=os.getenv("ADE_API_ADMIN_KEY", ""))
    parser.add_argument(
        "--native-api-key",
        default=os.getenv("ADE_API_OPERATOR_KEY") or os.getenv("ADE_API_ADMIN_KEY", ""),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.legacy_api_key or not args.native_api_key:
        parser.error("legacy and native API keys are required")
    receipt = rehearse_rollback(
        project_root=PROJECT_ROOT,
        legacy_revision=args.legacy_revision,
        legacy_base_url=args.legacy_base_url,
        native_base_url=args.native_base_url,
        legacy_api_key=args.legacy_api_key,
        native_api_key=args.native_api_key,
        compose_network=args.compose_network,
        output_path=args.output,
    )
    print(
        f"Agent Studio rollback rehearsal passed={receipt['rehearsed']} "
        f"receipt={receipt['receipt_sha256']}"
    )
    return 0 if receipt["rehearsed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
