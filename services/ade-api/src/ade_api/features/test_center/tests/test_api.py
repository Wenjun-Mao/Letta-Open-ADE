from __future__ import annotations

import asyncio
import json
import sys
from io import StringIO

import pytest
from pydantic import TypeAdapter, ValidationError

from ade_api.features.test_center import api
from ade_api.features.test_center.contracts import (
    AgentRuntimeAcceptanceRunRequest,
    ChatMemoryEvaluationRunRequest,
    CurrentStackSmokeRunRequest,
    TestRunRequest,
)


RUN_REQUEST_ADAPTER = TypeAdapter(TestRunRequest)


def _parse_request(payload: dict[str, object]):
    return RUN_REQUEST_ADAPTER.validate_python(payload)


def test_run_request_discriminator_accepts_only_the_three_workflows() -> None:
    assert isinstance(
        _parse_request({"run_type": "ade_api_e2e_check"}),
        CurrentStackSmokeRunRequest,
    )
    assert isinstance(
        _parse_request({"run_type": "chat_memory_eval"}),
        ChatMemoryEvaluationRunRequest,
    )
    assert isinstance(
        _parse_request({"run_type": "agent_runtime_acceptance"}),
        AgentRuntimeAcceptanceRunRequest,
    )

    with pytest.raises(ValidationError):
        _parse_request({"run_type": "ade_mvp_smoke_e2e_check"})
    with pytest.raises(ValidationError):
        _parse_request({"run_type": "agent_runtime_parity_eval"})


def test_run_request_models_forbid_fields_owned_by_another_workflow() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        _parse_request(
            {
                "run_type": "ade_api_e2e_check",
                "model": "test::model",
            }
        )
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        _parse_request(
            {
                "run_type": "agent_runtime_acceptance",
                "fixture_key": "recent_user_chat_turns",
            }
        )
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        _parse_request(
            {
                "run_type": "chat_memory_eval",
                "case_keys": ["chat_memory_baseline"],
            }
        )


def test_chat_memory_request_keeps_its_retry_contract() -> None:
    request = _parse_request(
        {
            "run_type": "chat_memory_eval",
            "model": "test::model",
            "fixture_key": "recent_user_chat_turns",
            "rounds": 2,
            "retry_count": 1,
            "judge_enabled": False,
        }
    )

    assert request.model == "test::model"
    assert request.rounds == 2
    assert request.retry_count == 1
    assert request.judge_enabled is False

    with pytest.raises(ValidationError, match="fixture_key must be one of"):
        _parse_request(
            {
                "run_type": "chat_memory_eval",
                "fixture_key": "unknown_fixture",
            }
        )


def test_native_runtime_request_canonicalizes_case_keys_and_enforces_bounds() -> None:
    request = _parse_request(
        {
            "run_type": "agent_runtime_acceptance",
            "case_keys": ["weather_tool_failure", "chat_memory_baseline"],
            "rounds": 3,
            "timeout_seconds": 180,
        }
    )

    assert request.case_keys == ["chat_memory_baseline", "weather_tool_failure"]

    with pytest.raises(ValidationError, match="must be canonical"):
        _parse_request(
            {
                "run_type": "agent_runtime_acceptance",
                "case_keys": ["unknown_case"],
            }
        )
    with pytest.raises(ValidationError):
        _parse_request({"run_type": "agent_runtime_acceptance", "rounds": 4})
    with pytest.raises(ValidationError):
        _parse_request({"run_type": "agent_runtime_acceptance", "timeout_seconds": 4.9})


def test_options_endpoint_returns_the_canonical_defaults_and_choices(
    monkeypatch,
) -> None:
    monkeypatch.setattr(api, "ensure_ade_api_enabled", lambda: None)
    monkeypatch.setattr(
        api,
        "runtime_options",
        lambda *_args, **_kwargs: (
            [
                {
                    "key": "dgx_vllm::chat-model",
                    "label": "DGX chat model",
                    "available": True,
                }
            ],
            [
                {
                    "key": "dgx_embedding_sidecar::embedding-model",
                    "label": "DGX embedding model",
                    "available": True,
                }
            ],
        ),
    )
    monkeypatch.setattr(
        api,
        "prompt_option_entries",
        lambda *_args: [{"key": "chat_prompt", "label": "Chat prompt"}],
    )
    monkeypatch.setattr(
        api,
        "persona_option_entries",
        lambda *_args: [{"key": "chat_persona", "label": "Chat persona"}],
    )

    payload = asyncio.run(api.get_test_center_options(object(), object()))

    assert [item["key"] for item in payload["run_types"]] == [
        "chat_memory_eval",
        "agent_runtime_acceptance",
        "ade_api_e2e_check",
    ]
    assert payload["chat_memory_eval"]["defaults"]["fixture_key"] == (
        "recent_user_chat_turns"
    )
    assert payload["chat_memory_eval"]["fixtures"] == [
        {"key": "recent_user_chat_turns", "label": "Recent user chat turns"}
    ]
    assert payload["catalog"] == {
        "models": [
            {
                "key": "dgx_vllm::chat-model",
                "label": "DGX chat model",
                "available": True,
            }
        ],
        "embeddings": [
            {
                "key": "dgx_embedding_sidecar::embedding-model",
                "label": "DGX embedding model",
                "available": True,
            }
        ],
        "prompts": [{"key": "chat_prompt", "label": "Chat prompt", "available": True}],
        "personas": [
            {"key": "chat_persona", "label": "Chat persona", "available": True}
        ],
    }
    assert payload["agent_runtime_acceptance"]["defaults"]["rounds"] == 3
    assert {item["key"] for item in payload["agent_runtime_acceptance"]["cases"]} == {
        "chat_memory_baseline",
        "weather_tool_failure",
        "correction_chain",
        "explicit_forgetting",
        "cross_agent_subject_sharing",
        "cross_subject_isolation",
        "old_memory_deep_search",
        "long_history_compaction",
        "false_memory_prevention",
        "weather_tool_selection",
    }


def test_create_test_run_passes_only_the_discriminated_request_fields(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class _FakeOrchestrator:
        def create_run(self, **kwargs):
            captured.update(kwargs)
            return {
                "run_id": "run-1",
                "run_type": kwargs["run_type"],
                "status": "queued",
                "command": ["python", "workflow.py"],
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
    request = _parse_request(
        {
            "run_type": "chat_memory_eval",
            "model": "test::model",
            "judge_enabled": False,
        }
    )

    payload = asyncio.run(api.create_test_run(request, _FakeOrchestrator()))

    assert captured == {
        "run_type": "chat_memory_eval",
        "model": "test::model",
        "judge_enabled": False,
    }
    assert payload["run_id"] == "run-1"


def test_descriptors_own_the_three_commands_and_reject_unowned_options(
    tmp_path,
) -> None:
    from ade_api.features.test_center.orchestrator import TestRunOrchestrator
    from ade_api.features.test_center.run_descriptors import RUN_DESCRIPTORS

    assert set(RUN_DESCRIPTORS) == {
        "ade_api_e2e_check",
        "chat_memory_eval",
        "agent_runtime_acceptance",
    }

    orchestrator = TestRunOrchestrator(project_root=tmp_path)
    assert orchestrator._build_command(
        run_type="ade_api_e2e_check",
        output_dir=tmp_path / "smoke-output",
        options={},
    ) == [sys.executable, "workflows/smoke/ade_api_e2e_check.py"]

    output_dir = tmp_path / "00000000-0000-0000-0000-000000000001"
    assert orchestrator._build_command(
        run_type="chat_memory_eval",
        output_dir=output_dir,
        options={"model": "test::model", "judge_enabled": False},
    ) == [
        sys.executable,
        "workflows/evals/chat_memory_eval/run.py",
        "--config",
        "workflows/evals/chat_memory_eval/config.toml",
        "--output-dir",
        str(output_dir),
        "--run-id",
        output_dir.name,
        "--model",
        "test::model",
        "--no-judge-enabled",
    ]

    assert orchestrator._build_command(
        run_type="agent_runtime_acceptance",
        output_dir=tmp_path / "qualification-output",
        options={"case_keys": ["weather_tool_failure", "chat_memory_baseline"]},
    ) == [
        sys.executable,
        "workflows/evals/agent_runtime_acceptance/run.py",
        "--config",
        "workflows/evals/agent_runtime_acceptance/config.toml",
        "--output-dir",
        str(tmp_path / "qualification-output"),
        "--case-key",
        "chat_memory_baseline",
        "--case-key",
        "weather_tool_failure",
        "--rounds",
        "1",
        "--no-include-llama-compatibility",
    ]

    with pytest.raises(
        ValueError, match="only accepted when run_type='chat_memory_eval'"
    ):
        orchestrator._build_command(
            run_type="ade_api_e2e_check",
            output_dir=tmp_path / "smoke-output",
            options={"model": "test::model"},
        )


def test_artifact_discovery_stays_rooted_and_ignores_internal_files(tmp_path) -> None:
    from ade_api.features.test_center.run_descriptors import (
        ArtifactDiscoveryContext,
        discover_run_directory_artifacts,
    )

    state_root = tmp_path / "runtime" / "test-runs"
    output_dir = state_root / "run-1"
    output_dir.mkdir(parents=True)
    (output_dir / ".run.json.tmp").write_text("temporary", encoding="utf-8")
    (output_dir / "run.json").write_text("manifest", encoding="utf-8")
    (output_dir / "result.json").write_text("{}", encoding="utf-8")

    assert discover_run_directory_artifacts(
        ArtifactDiscoveryContext(
            output_dir=output_dir,
            log_file=None,
            state_root=state_root,
        )
    ) == [
        {
            "artifact_id": "result.json",
            "type": "json",
            "path": str((output_dir / "result.json").resolve()),
            "exists": True,
            "size_bytes": 2,
        }
    ]

    assert (
        discover_run_directory_artifacts(
            ArtifactDiscoveryContext(
                output_dir=tmp_path / "outside",
                log_file=None,
                state_root=state_root,
            )
        )
        == []
    )


def test_retired_persisted_runs_are_not_part_of_the_current_product_surface(
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
                "run_type": "agent_runtime_parity_eval",
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

    assert orchestrator.get_run("retired-run") is None
    assert orchestrator.list_runs() == []


def test_process_executor_streams_output_without_persisting_process_handles(
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
    manifest = json.loads((output_dir / "run.json").read_text(encoding="utf-8"))
    assert completed is not None
    assert completed["status"] == "passed"
    assert completed["output_tail"] == ["first output", "second output"]
    assert manifest["status"] == "passed"
    assert "_process" not in manifest
