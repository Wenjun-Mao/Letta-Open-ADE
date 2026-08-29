import asyncio
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from workflows.evals.agent_runtime_v3_acceptance import run as run_module
from workflows.evals.agent_runtime_v3_acceptance.cleanup import CleanupScope
from workflows.evals.agent_runtime_v3_acceptance.runner import (
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
