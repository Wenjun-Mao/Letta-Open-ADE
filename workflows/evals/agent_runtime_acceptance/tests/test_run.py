from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from ade_api.features.agent_runtime.request_budget import budget_identity
from ade_api.features.agent_runtime.worker_health import (
    worker_compatibility_fingerprint,
)
from ade_api.platform.settings import AdeApiSettings
from workflows.evals.agent_runtime_acceptance import run as run_module
from workflows.evals.agent_runtime_acceptance import preflight
from workflows.evals.agent_runtime_acceptance.runner import (
    EvaluationSessionScope,
    QualificationRound,
)


def test_run_id_uses_portable_utc_timestamp() -> None:
    eastern = timezone(-timedelta(hours=4))
    run_id = run_module._new_run_id(
        now=datetime(2026, 8, 29, 18, 22, 17, tzinfo=eastern),
        random_suffix="deadbeef",
    )
    assert run_id == "agent-runtime-20260829t222217z-deadbeef"


def test_full_qualification_preflight_requires_matching_shared_budget(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = AdeApiSettings(_env_file=None, agent_runtime_mode="development")
    monkeypatch.setattr(preflight, "get_settings", lambda: settings)
    health: dict[str, object] = {}
    assert not preflight.budget_preflight_passed(
        health, diagnostic=False, retry_count=0
    )
    assert preflight.budget_preflight_passed(health, diagnostic=True, retry_count=0)

    settings.agent_runtime_budget_ledger_path = str(tmp_path / "stage.sqlite3")
    settings.agent_runtime_budget_stage = "qualification"
    settings.agent_runtime_budget_generation_limit = 10
    settings.agent_runtime_budget_embedding_limit = 10
    budget = budget_identity(settings)
    assert budget is not None
    health["compatibility_fingerprint"] = worker_compatibility_fingerprint(
        runtime_mode="development", budget=budget
    )
    assert preflight.budget_preflight_passed(health, diagnostic=False, retry_count=0)
    assert not preflight.budget_preflight_passed(
        health, diagnostic=False, retry_count=1
    )
    settings.agent_runtime_budget_stage = "preflight"
    assert not preflight.budget_preflight_passed(
        health, diagnostic=False, retry_count=0
    )


def test_session_purge_is_reverse_order_idempotent_and_closes_client() -> None:
    calls: list[str] = []

    class _Client:
        async def purge_evaluation_session(
            self, conversation_id: str
        ) -> dict[str, object]:
            calls.append(f"purge:{conversation_id}")
            return {"conversation_id": conversation_id, "already_purged": False}

        async def aclose(self) -> None:
            calls.append("close")

    asyncio.run(
        run_module._close_client_and_purge(
            _Client(),  # type: ignore[arg-type]
            [
                EvaluationSessionScope(("conversation-a",), {}, ()),
                EvaluationSessionScope(("conversation-b", "conversation-a"), {}, ()),
            ],
        )
    )
    assert calls == ["purge:conversation-b", "purge:conversation-a", "close"]


def test_purge_failure_still_closes_client() -> None:
    calls: list[str] = []

    class _Client:
        async def purge_evaluation_session(
            self, _conversation_id: str
        ) -> dict[str, object]:
            raise RuntimeError("purge failed")

        async def aclose(self) -> None:
            calls.append("close")

    with pytest.raises(RuntimeError, match="purge failed"):
        asyncio.run(
            run_module._close_client_and_purge(
                _Client(),  # type: ignore[arg-type]
                [EvaluationSessionScope(("conversation-a",), {}, ())],
            )
        )
    assert calls == ["close"]


def test_case_selection_runs_one_diagnostic_round_without_promotion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: dict[str, object] = {}
    cases = (SimpleNamespace(key="case-a"), SimpleNamespace(key="case-b"))

    class _Client:
        def __init__(self, *_args: object) -> None:
            pass

        async def aclose(self) -> None:
            pass

        async def get_worker_health(self) -> dict[str, object]:
            return {
                "http_status": 200,
                "status": "ready",
                "database_ready": True,
                "worker_ready": True,
                "matching_build_worker_count": 1,
                "source_revision": "a" * 40,
                "source_dirty": False,
                "source_fingerprint": "b" * 64,
            }

    async def primary(**kwargs: object) -> tuple[QualificationRound, ...]:
        calls.update(kwargs)
        return (
            QualificationRound(
                index=1,
                kind="diagnostic",
                execution_mode="live-api-diagnostic",
                complete_matrix=False,
                passed=True,
                case_keys=("case-b",),
                cases=(),
                deployment_fingerprints={},
            ),
        )

    monkeypatch.setattr(run_module, "load_cases", lambda _path: cases)
    monkeypatch.setattr(run_module, "RuntimeClient", _Client)
    monkeypatch.setattr(run_module, "run_primary_rounds", primary)
    monkeypatch.setattr(run_module, "_source_revision", lambda: "a" * 40)
    monkeypatch.setattr(run_module, "_source_dirty", lambda: False)
    monkeypatch.setattr(run_module, "_source_fingerprint", lambda: "b" * 64)
    monkeypatch.setattr(run_module, "production_policy_hashes", lambda: {})

    result = asyncio.run(
        run_module.run_acceptance(
            run_module.AcceptanceConfig(
                api_base_url="https://ade.test",
                api_key="operator-key",
                output_dir=tmp_path,
                case_keys=("case-b",),
            )
        )
    )
    assert calls["rounds"] == 1
    assert calls["diagnostic"] is True
    assert calls["prompt_key"] == "chat_v20260516"
    assert calls["persona_key"] == "chat_linxiaotang"
    assert [case.key for case in calls["cases"]] == ["case-b"]
    assert result["promotion_proposal"] is None
    assert result["eligible"] is False


def test_not_ready_worker_stops_before_primary_work(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class _Client:
        def __init__(self, *_args: object) -> None:
            pass

        async def get_worker_health(self) -> dict[str, object]:
            return {"http_status": 503, "status": "not_ready"}

        async def aclose(self) -> None:
            pass

    async def primary(**_kwargs: object) -> tuple[QualificationRound, ...]:
        raise AssertionError("a failed preflight must not run primary rounds")

    monkeypatch.setattr(
        run_module, "load_cases", lambda _path: (SimpleNamespace(key="case-a"),)
    )
    monkeypatch.setattr(run_module, "RuntimeClient", _Client)
    monkeypatch.setattr(run_module, "run_primary_rounds", primary)
    monkeypatch.setattr(run_module, "_source_revision", lambda: "a" * 40)
    monkeypatch.setattr(run_module, "_source_dirty", lambda: False)
    monkeypatch.setattr(run_module, "_source_fingerprint", lambda: "b" * 64)
    monkeypatch.setattr(run_module, "production_policy_hashes", lambda: {})

    result = asyncio.run(
        run_module.run_acceptance(
            run_module.AcceptanceConfig(
                api_base_url="https://ade.test",
                api_key="operator-key",
                output_dir=tmp_path,
            )
        )
    )
    assert result["passed"] is False
    assert result["primary_rounds"] == []
