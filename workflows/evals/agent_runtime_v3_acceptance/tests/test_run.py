import asyncio
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from workflows.evals.agent_runtime_v3_acceptance import run as run_module
from workflows.evals.agent_runtime_v3_acceptance.cleanup import CleanupScope
from workflows.evals.agent_runtime_v3_acceptance.runner import (
    QualificationRound,
    ResourceScope,
    _resource_key,
)


_new_run_id = run_module._new_run_id


def test_run_id_uses_portable_utc_timestamp() -> None:
    eastern = timezone(-timedelta(hours=4))

    run_id = _new_run_id(
        now=datetime(2026, 8, 29, 18, 22, 17, tzinfo=eastern),
        random_suffix="deadbeef",
    )

    assert run_id == "agent-runtime-v3-20260829t222217z-deadbeef"
    assert len(run_id) == 42


def test_run_id_defaults_to_an_eight_character_suffix() -> None:
    run_id = _new_run_id(now=datetime(2026, 8, 29, tzinfo=UTC))

    timestamp, suffix = run_id.rsplit("-", 1)
    assert timestamp == "agent-runtime-v3-20260829t000000z"
    assert len(suffix) == 8


def test_generated_resource_keys_are_bound_to_cleanup_run_id() -> None:
    run_id = _new_run_id(
        now=datetime(2026, 8, 29, tzinfo=UTC), random_suffix="ABCDEF12"
    )
    round_namespace = _resource_key(run_id, "round-1")
    definition_key = _resource_key(
        round_namespace, "chat_memory_baseline", "agent-primary"
    )
    subject_key = _resource_key(
        round_namespace, "chat_memory_baseline", "subject-primary"
    )

    scope = CleanupScope(
        run_id=run_id,
        definition_keys=(definition_key,),
        subject_external_keys=(subject_key,),
    )

    scope.validate()
    assert run_id == "agent-runtime-v3-20260829t000000z-abcdef12"
    assert definition_key.startswith(run_id)
    assert subject_key.startswith(run_id)


def test_client_close_failure_cannot_skip_scoped_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cleanup_calls: list[object] = []

    class FailingClient:
        async def aclose(self) -> None:
            raise RuntimeError("close failed")

    class RecordingCleanup:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def cleanup(self, scope: object) -> None:
            cleanup_calls.append(scope)

    monkeypatch.setattr(run_module, "ScopedPostgresCleanup", RecordingCleanup)
    config = SimpleNamespace(
        database_url="postgresql://example",
        output_dir=tmp_path,
    )
    scopes = [
        ResourceScope(
            definition_keys=("run-definition",),
            subject_external_keys=("run-subject",),
            deployment_fingerprints={},
            deployment_snapshots=(),
        )
    ]

    with pytest.raises(RuntimeError, match="close failed"):
        asyncio.run(
            run_module._close_client_and_cleanup(
                FailingClient(),
                config,
                "run-a",
                scopes,  # type: ignore[arg-type]
            )
        )

    assert len(cleanup_calls) == 1
    assert cleanup_calls[0].definition_keys == ("run-definition",)
    assert cleanup_calls[0].subject_external_keys == ("run-subject",)


def test_case_selection_is_one_round_without_llama_or_promotion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: dict[str, object] = {}
    cases = (
        SimpleNamespace(key="case-a"),
        SimpleNamespace(key="case-b"),
    )

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

    async def llama(**_kwargs: object) -> QualificationRound:
        raise AssertionError("diagnostics must not launch llama compatibility")

    def proposal(**_kwargs: object) -> object:
        raise AssertionError("diagnostics must not build a promotion proposal")

    monkeypatch.setattr(run_module, "load_cases", lambda _path: cases)
    monkeypatch.setattr(run_module, "RuntimeV3Client", _Client)
    monkeypatch.setattr(run_module, "run_primary_rounds", primary)
    monkeypatch.setattr(run_module, "run_llama_compatibility_round", llama)
    monkeypatch.setattr(run_module, "build_promotion_proposal", proposal)
    monkeypatch.setattr(run_module, "_source_revision", lambda: "a" * 40)
    monkeypatch.setattr(run_module, "_source_dirty", lambda: False)
    monkeypatch.setattr(run_module, "_source_fingerprint", lambda: "b" * 64)

    config = run_module.AcceptanceConfig(
        api_base_url="https://ade.test",
        api_key="operator-key",
        output_dir=tmp_path,
        database_url="postgresql://example",
        case_keys=("case-b",),
    )
    result = asyncio.run(run_module.run_acceptance(config))

    assert calls["rounds"] == 1
    assert calls["diagnostic"] is True
    assert [case.key for case in calls["cases"]] == ["case-b"]
    assert result["llama_compatibility"] is None
    assert result["promotion_proposal"] is None
    assert result["eligible"] is False


def test_case_selection_rejects_noncanonical_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cases = (
        SimpleNamespace(key="case-a"),
        SimpleNamespace(key="case-b"),
    )
    monkeypatch.setattr(run_module, "load_cases", lambda _path: cases)

    config = run_module.AcceptanceConfig(
        api_base_url="https://ade.test",
        api_key="operator-key",
        output_dir=tmp_path,
        database_url="postgresql://example",
        case_keys=("case-b", "case-a"),
    )

    with pytest.raises(RuntimeError, match="canonical case order"):
        asyncio.run(run_module.run_acceptance(config))


def test_not_ready_worker_preflight_stops_before_primary_work(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[str] = []

    class _Client:
        def __init__(self, *_args: object) -> None:
            pass

        async def get_worker_health(self) -> dict[str, object]:
            return {
                "http_status": 503,
                "status": "not_ready",
                "database_ready": True,
                "worker_ready": False,
                "matching_build_worker_count": 0,
            }

        async def aclose(self) -> None:
            calls.append("close")

    async def primary(**_kwargs: object) -> tuple[QualificationRound, ...]:
        raise AssertionError("a failed preflight must not launch primary rounds")

    monkeypatch.setattr(
        run_module,
        "load_cases",
        lambda _path: (SimpleNamespace(key="case-a"),),
    )
    monkeypatch.setattr(run_module, "RuntimeV3Client", _Client)
    monkeypatch.setattr(run_module, "run_primary_rounds", primary)
    monkeypatch.setattr(run_module, "_source_revision", lambda: "a" * 40)
    monkeypatch.setattr(run_module, "_source_dirty", lambda: False)
    monkeypatch.setattr(run_module, "_source_fingerprint", lambda: "b" * 64)

    config = run_module.AcceptanceConfig(
        api_base_url="https://ade.test",
        api_key="operator-key",
        output_dir=tmp_path,
        database_url="postgresql://unused",
    )
    result = asyncio.run(run_module.run_acceptance(config))

    assert result["passed"] is False
    assert result["eligible"] is False
    assert result["primary_rounds"] == []
    assert result["promotion_proposal"] is None
    assert calls == ["close"]
    preflight = Path(result["preflight_path"])
    assert preflight.is_file()
    assert not list(preflight.parent.glob("round-*"))


def test_full_run_rejects_dirty_or_mismatched_source_before_primary_work(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class _Client:
        def __init__(self, *_args: object) -> None:
            pass

        async def get_worker_health(self) -> dict[str, object]:
            return {
                "http_status": 200,
                "status": "ready",
                "database_ready": True,
                "worker_ready": True,
                "matching_build_worker_count": 1,
                "source_revision": "a" * 40,
                "source_dirty": True,
                "source_fingerprint": "c" * 64,
            }

        async def aclose(self) -> None:
            pass

    async def primary(**_kwargs: object) -> tuple[QualificationRound, ...]:
        raise AssertionError("source mismatch must stop before primary rounds")

    monkeypatch.setattr(
        run_module,
        "load_cases",
        lambda _path: (SimpleNamespace(key="case-a"),),
    )
    monkeypatch.setattr(run_module, "RuntimeV3Client", _Client)
    monkeypatch.setattr(run_module, "run_primary_rounds", primary)
    monkeypatch.setattr(run_module, "_source_revision", lambda: "a" * 40)
    monkeypatch.setattr(run_module, "_source_dirty", lambda: True)
    monkeypatch.setattr(run_module, "_source_fingerprint", lambda: "b" * 64)

    config = run_module.AcceptanceConfig(
        api_base_url="https://ade.test",
        api_key="operator-key",
        output_dir=tmp_path,
        database_url="postgresql://unused",
    )
    result = asyncio.run(run_module.run_acceptance(config))

    assert result["passed"] is False
    preflight = Path(result["preflight_path"])
    assert preflight.is_file()
    assert not list(preflight.parent.glob("round-*"))
