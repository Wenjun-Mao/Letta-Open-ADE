from __future__ import annotations

import asyncio
import json
import sys
from io import StringIO
from pathlib import Path

import pytest
from pydantic import ValidationError

from ade_api.features.test_center.contracts import TestRunRequest
from ade_api.features.test_center import api


def test_run_request_accepts_supported_run_types() -> None:
    assert TestRunRequest(run_type="ade_api_e2e_check").run_type == "ade_api_e2e_check"
    assert (
        TestRunRequest(run_type="ade_mvp_smoke_e2e_check").run_type
        == "ade_mvp_smoke_e2e_check"
    )
    assert TestRunRequest(run_type="chat_memory_eval").run_type == "chat_memory_eval"

    with pytest.raises(ValidationError):
        TestRunRequest(run_type="agent_bootstrap_check")


def test_run_request_rejects_unsupported_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        TestRunRequest(
            run_type="ade_api_e2e_check",
            model="lmstudio_openai/gemma-4-31b-it",
            embedding="letta/letta-free",
            rounds=5,
            config_path="legacy-config.json",
        )


def test_create_test_run_passes_only_run_type(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeOrchestrator:
        def create_run(self, *, run_type: str):
            captured["run_type"] = run_type
            return {
                "run_id": "run-1",
                "run_type": run_type,
                "status": "queued",
                "command": ["python", "workflows/smoke/ade_api_e2e_check.py"],
                "created_at": "2026-04-22T00:00:00+00:00",
                "started_at": "",
                "finished_at": "",
                "exit_code": None,
                "log_file": "data/runtime/test-runs/run-1/orchestrator.log",
                "cancel_requested": False,
                "output_tail": [],
                "error": "",
                "artifacts": [],
            }

    monkeypatch.setattr(api, "ensure_ade_api_enabled", lambda: None)

    payload = asyncio.run(
        api.create_test_run(
            TestRunRequest(run_type="ade_api_e2e_check"),
            _FakeOrchestrator(),
        )
    )

    assert captured["run_type"] == "ade_api_e2e_check"
    assert payload["run_type"] == "ade_api_e2e_check"


def test_chat_memory_eval_request_accepts_focused_fields() -> None:
    request = TestRunRequest(
        run_type="chat_memory_eval",
        model="openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8",
        prompt_key="chat_v20260516",
        persona_key="chat_linxiaotang",
        embedding="letta/letta-free",
        rounds=1,
        fixture_key="recent_user_chat_turns",
        timeout_seconds=180,
        retry_count=0,
        judge_enabled=False,
    )

    assert request.rounds == 1
    assert request.judge_enabled is False


def test_chat_memory_eval_create_passes_options(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeOrchestrator:
        def create_run(self, **kwargs):
            captured.update(kwargs)
            return {
                "run_id": "run-2",
                "run_type": kwargs["run_type"],
                "status": "queued",
                "command": ["python", "workflows/evals/chat_memory_eval/run.py"],
                "created_at": "2026-04-22T00:00:00+00:00",
                "started_at": "",
                "finished_at": "",
                "exit_code": None,
                "log_file": "data/runtime/test-runs/run-2/orchestrator.log",
                "cancel_requested": False,
                "output_tail": [],
                "error": "",
                "artifacts": [],
            }

    monkeypatch.setattr(api, "ensure_ade_api_enabled", lambda: None)

    payload = asyncio.run(
        api.create_test_run(
            TestRunRequest(
                run_type="chat_memory_eval",
                model="openai-proxy/test::model",
                rounds=1,
                judge_enabled=False,
            ),
            _FakeOrchestrator(),
        )
    )

    assert captured["run_type"] == "chat_memory_eval"
    assert captured["model"] == "openai-proxy/test::model"
    assert captured["rounds"] == 1
    assert captured["judge_enabled"] is False
    assert payload["run_type"] == "chat_memory_eval"


def test_test_run_descriptors_own_option_validation_and_command_construction(
    tmp_path,
) -> None:
    from ade_api.features.test_center.orchestrator import TestRunOrchestrator
    from ade_api.features.test_center.run_descriptors import RUN_DESCRIPTORS

    assert set(RUN_DESCRIPTORS) == {
        "ade_api_e2e_check",
        "ade_mvp_smoke_e2e_check",
        "chat_memory_eval",
    }

    orchestrator = TestRunOrchestrator(project_root=tmp_path)
    assert orchestrator._build_command(
        run_type="ade_api_e2e_check",
        output_dir=tmp_path / "run-output",
        options={},
    ) == [sys.executable, "workflows/smoke/ade_api_e2e_check.py"]
    assert orchestrator._build_command(
        run_type="ade_mvp_smoke_e2e_check",
        output_dir=tmp_path / "run-output",
        options={},
    ) == [sys.executable, "workflows/smoke/ade_mvp_smoke_e2e_check.py"]

    command = orchestrator._build_command(
        run_type="chat_memory_eval",
        output_dir=tmp_path / "run-output",
        options={
            "model": "openai-proxy/test::model",
            "rounds": 2,
            "judge_enabled": False,
        },
    )

    assert command == [
        sys.executable,
        "workflows/evals/chat_memory_eval/run.py",
        "--config",
        "workflows/evals/chat_memory_eval/config.toml",
        "--output-dir",
        str(tmp_path / "run-output"),
        "--model",
        "openai-proxy/test::model",
        "--rounds",
        "2",
        "--no-judge-enabled",
    ]
    with pytest.raises(
        ValueError, match="only accepted when run_type='chat_memory_eval'"
    ):
        orchestrator._build_command(
            run_type="ade_api_e2e_check",
            output_dir=tmp_path / "run-output",
            options={"model": "openai-proxy/test::model"},
        )


def test_test_run_orchestrator_discovers_run_output_artifacts(tmp_path) -> None:
    from ade_api.features.test_center.orchestrator import TestRunOrchestrator

    orchestrator = TestRunOrchestrator(project_root=tmp_path)
    output_dir = tmp_path / "data" / "runtime" / "test-runs" / "run-3"
    output_dir.mkdir(parents=True)
    log_file = output_dir / "orchestrator.log"
    csv_file = output_dir / "chat_memory_eval_20260516.csv"
    log_file.write_text("log", encoding="utf-8")
    csv_file.write_text("csv", encoding="utf-8")

    artifacts = orchestrator._resolve_artifacts(
        {
            "run_type": "chat_memory_eval",
            "log_file": str(log_file),
            "output_dir": str(output_dir),
        }
    )

    assert [item["artifact_id"] for item in artifacts] == [
        "orchestrator_log",
        "chat_memory_eval_20260516.csv",
    ]


def test_artifact_discovery_ignores_internal_and_transient_files(
    tmp_path, monkeypatch
) -> None:
    from ade_api.features.test_center.run_descriptors import (
        ArtifactDiscoveryContext,
        discover_run_directory_artifacts,
    )

    state_root = tmp_path / "runtime" / "test-runs"
    output_dir = state_root / "run-racing"
    output_dir.mkdir(parents=True)
    internal_temp = output_dir / ".run.json.tmp"
    transient = output_dir / "transient.json"
    internal_temp.write_text("temporary", encoding="utf-8")
    transient.write_text("temporary", encoding="utf-8")

    original_stat = Path.stat
    transient_stat_calls = 0

    def stat_with_disappearing_artifact(path: Path, *args, **kwargs):
        nonlocal transient_stat_calls
        if path == transient:
            transient_stat_calls += 1
            if transient_stat_calls > 1:
                raise FileNotFoundError(transient)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat_with_disappearing_artifact)

    artifacts = discover_run_directory_artifacts(
        ArtifactDiscoveryContext(
            output_dir=output_dir,
            log_file=None,
            state_root=state_root,
        )
    )

    assert artifacts == []


def test_test_run_orchestrator_recovers_completed_runs_from_manifests(tmp_path) -> None:
    from ade_api.features.test_center.orchestrator import TestRunOrchestrator

    state_root = tmp_path / "runtime" / "test-runs"
    output_dir = state_root / "run-complete"
    output_dir.mkdir(parents=True)
    (output_dir / "orchestrator.log").write_text("complete\n", encoding="utf-8")
    (output_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "run-complete",
                "run_type": "ade_api_e2e_check",
                "status": "passed",
                "command": ["python", "workflows/smoke/ade_api_e2e_check.py"],
                "created_at": "2026-05-16T16:00:00+00:00",
                "started_at": "2026-05-16T16:00:01+00:00",
                "finished_at": "2026-05-16T16:00:02+00:00",
                "exit_code": 0,
                "cancel_requested": False,
                "output_tail": ["complete"],
                "error": "",
            }
        ),
        encoding="utf-8",
    )

    orchestrator = TestRunOrchestrator(project_root=tmp_path, state_root=state_root)

    recovered = orchestrator.get_run("run-complete")
    assert recovered is not None
    assert recovered["status"] == "passed"
    assert recovered["output_tail"] == ["complete"]
    assert recovered["artifacts"][0]["artifact_id"] == "orchestrator_log"


def test_test_run_orchestrator_keeps_retired_persisted_run_artifacts_readable(
    tmp_path,
) -> None:
    from ade_api.features.test_center.orchestrator import TestRunOrchestrator

    state_root = tmp_path / "runtime" / "test-runs"
    output_dir = state_root / "retired-run"
    output_dir.mkdir(parents=True)
    (output_dir / "orchestrator.log").write_text("complete\n", encoding="utf-8")
    (output_dir / "legacy-result.txt").write_text("result\n", encoding="utf-8")
    (output_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "retired-run",
                "run_type": "retired_check",
                "status": "passed",
                "command": ["python", "retired_check.py"],
                "created_at": "2026-05-16T16:00:00+00:00",
                "started_at": "2026-05-16T16:00:01+00:00",
                "finished_at": "2026-05-16T16:00:02+00:00",
                "exit_code": 0,
                "cancel_requested": False,
                "output_tail": ["complete"],
                "error": "",
            }
        ),
        encoding="utf-8",
    )

    orchestrator = TestRunOrchestrator(project_root=tmp_path, state_root=state_root)

    recovered = orchestrator.get_run("retired-run")
    assert recovered is not None
    assert recovered["run_type"] == "retired_check"
    assert [item["artifact_id"] for item in recovered["artifacts"]] == [
        "orchestrator_log",
        "legacy-result.txt",
    ]


def test_test_run_orchestrator_marks_inflight_runs_interrupted_after_restart(
    tmp_path,
) -> None:
    from ade_api.features.test_center.orchestrator import TestRunOrchestrator

    state_root = tmp_path / "runtime" / "test-runs"
    output_dir = state_root / "run-running"
    output_dir.mkdir(parents=True)
    manifest_path = output_dir / "run.json"
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": "run-running",
                "run_type": "chat_memory_eval",
                "status": "running",
                "command": ["python", "workflows/evals/chat_memory_eval/run.py"],
                "created_at": "2026-05-16T16:00:00+00:00",
                "started_at": "2026-05-16T16:00:01+00:00",
                "finished_at": "",
                "exit_code": None,
                "cancel_requested": False,
                "output_tail": [],
                "error": "",
            }
        ),
        encoding="utf-8",
    )

    orchestrator = TestRunOrchestrator(project_root=tmp_path, state_root=state_root)

    recovered = orchestrator.get_run("run-running")
    assert recovered is not None
    assert recovered["status"] == "interrupted"
    assert "restarted" in recovered["error"]
    assert (
        json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == "interrupted"
    )


def test_process_executor_cancels_queued_runs_without_starting_a_subprocess(
    tmp_path,
) -> None:
    from ade_api.features.test_center.process_executor import TestRunProcessExecutor
    from ade_api.features.test_center.run_store import TestRunStore

    state_root = tmp_path / "runtime" / "test-runs"
    run_store = TestRunStore(state_root)
    run_id, output_dir = run_store.allocate_output_directory()
    run_store.create_run(
        run_id=run_id,
        run_type="ade_api_e2e_check",
        output_dir=output_dir,
        command=[sys.executable, "workflows/smoke/ade_api_e2e_check.py"],
    )
    executor = TestRunProcessExecutor(tmp_path, run_store)

    assert executor.cancel(run_id) is True
    executor._run_worker(run_id)

    recovered = run_store.get_snapshot(run_id)
    assert recovered is not None
    assert recovered["status"] == "cancelled"
    assert recovered["cancel_requested"] is True


def test_process_executor_streams_output_and_persists_completion(
    tmp_path, monkeypatch
) -> None:
    from ade_api.features.test_center import process_executor
    from ade_api.features.test_center.process_executor import TestRunProcessExecutor
    from ade_api.features.test_center.run_store import TestRunStore

    class _SuccessfulProcess:
        stdout = StringIO("first output\nsecond output\n")

        def wait(self) -> int:
            return 0

    monkeypatch.setattr(
        process_executor.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _SuccessfulProcess(),
    )

    state_root = tmp_path / "runtime" / "test-runs"
    run_store = TestRunStore(state_root)
    run_id, output_dir = run_store.allocate_output_directory()
    run_store.create_run(
        run_id=run_id,
        run_type="ade_api_e2e_check",
        output_dir=output_dir,
        command=[sys.executable, "workflows/smoke/ade_api_e2e_check.py"],
    )

    TestRunProcessExecutor(tmp_path, run_store)._run_worker(run_id)

    completed = run_store.get_snapshot(run_id)
    assert completed is not None
    assert completed["status"] == "passed"
    assert completed["exit_code"] == 0
    assert completed["output_tail"] == ["first output", "second output"]
    assert "second output" in (output_dir / "orchestrator.log").read_text(
        encoding="utf-8"
    )
    manifest = json.loads((output_dir / "run.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "passed"


def test_run_store_does_not_persist_runtime_process_handles(tmp_path) -> None:
    from ade_api.features.test_center.run_store import TestRunStore

    state_root = tmp_path / "runtime" / "test-runs"
    run_store = TestRunStore(state_root)
    run_id, output_dir = run_store.allocate_output_directory()
    run_store.create_run(
        run_id=run_id,
        run_type="ade_api_e2e_check",
        output_dir=output_dir,
        command=[sys.executable, "workflows/smoke/ade_api_e2e_check.py"],
    )

    manifest = json.loads((output_dir / "run.json").read_text(encoding="utf-8"))
    assert "_process" not in manifest
