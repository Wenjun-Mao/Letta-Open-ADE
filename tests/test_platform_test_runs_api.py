from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from agent_platform_api.models.platform import PlatformTestRunRequest
from agent_platform_api.routers import platform_runtime


def test_platform_test_run_request_accepts_only_kept_run_types() -> None:
    assert PlatformTestRunRequest(run_type="platform_api_e2e_check").run_type == "platform_api_e2e_check"
    assert PlatformTestRunRequest(run_type="ade_mvp_smoke_e2e_check").run_type == "ade_mvp_smoke_e2e_check"

    with pytest.raises(ValidationError):
        PlatformTestRunRequest(run_type="agent_bootstrap_check")


def test_platform_test_run_request_rejects_removed_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PlatformTestRunRequest(
            run_type="platform_api_e2e_check",
            model="lmstudio_openai/gemma-4-31b-it",
            embedding="letta/letta-free",
            rounds=5,
            config_path="legacy-config.json",
        )


def test_platform_create_test_run_passes_only_run_type(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeOrchestrator:
        def create_run(self, *, run_type: str):
            captured["run_type"] = run_type
            return {
                "run_id": "run-1",
                "run_type": run_type,
                "status": "queued",
                "command": ["python", "tests/checks/platform_api_e2e_check.py"],
                "created_at": "2026-04-22T00:00:00+00:00",
                "started_at": "",
                "finished_at": "",
                "exit_code": None,
                "log_file": "tests/outputs/platform_orchestrator/run-1.log",
                "cancel_requested": False,
                "output_tail": [],
                "error": "",
                "artifacts": [],
            }

    monkeypatch.setattr(platform_runtime, "ensure_platform_api_enabled", lambda: None)
    monkeypatch.setattr(platform_runtime, "test_orchestrator", _FakeOrchestrator())

    payload = asyncio.run(
        platform_runtime.api_platform_create_test_run(
            PlatformTestRunRequest(run_type="platform_api_e2e_check")
        )
    )

    assert captured["run_type"] == "platform_api_e2e_check"
    assert payload["run_type"] == "platform_api_e2e_check"
