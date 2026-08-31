from __future__ import annotations

import asyncio
import json
import tomllib
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from ade_api.features.test_center import api
from ade_api.features.test_center.contracts import (
    ChatMemoryEvaluationDetailResponse,
    ChatMemoryEvaluationListResponse,
)
from ade_api.features.test_center.run_descriptors import (
    DEFAULT_CHAT_MEMORY_EVALUATION_CONFIG,
)
import ade_api.platform.app as app_module
from ade_api.platform.app import create_app
from ade_api.platform.dependencies import get_test_orchestrator


def _summary_payload() -> dict[str, object]:
    return {
        "run_id": "workflow-run-id",
        "rounds_total": 2,
        "rounds_passed": 1,
        "rounds_failed": 1,
        "errors": 0,
        "pass_rate": 0.5,
        "config": {
            "model": "openai-proxy/dgx_vllm::qwen",
            "prompt_key": "chat_v20260516",
            "persona_key": "chat_linxiaotang",
            "embedding": "letta/letta-free",
            "fixture_key": "recent_user_chat_turns",
            "rounds": 2,
            "timeout_seconds": 180.0,
            "retry_count": 0,
            "judge_enabled": True,
        },
        "fixture": {
            "key": "recent_user_chat_turns",
            "description": "A durable-memory conversation.",
            "turns": ["Hello", "My dog is Rocky"],
            "expected_facts": [
                {
                    "key": "dog_name",
                    "label": "Dog name",
                    "aliases": ["Rocky"],
                }
            ],
            "forbidden_reply_substrings": ["我是AI"],
        },
    }


def test_chat_memory_evaluation_projection_defaults_match_runner_config() -> None:
    project_root = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (
            parent / "workflows" / "evals" / "chat_memory_eval" / "config.toml"
        ).is_file()
    )
    runner_config = tomllib.loads(
        (
            project_root / "workflows" / "evals" / "chat_memory_eval" / "config.toml"
        ).read_text(encoding="utf-8")
    )

    assert {
        key: runner_config[key] for key in DEFAULT_CHAT_MEMORY_EVALUATION_CONFIG
    } == DEFAULT_CHAT_MEMORY_EVALUATION_CONFIG


def _round_payload(
    *,
    number: int,
    passed: bool,
    elapsed_seconds: float,
    archived: bool = True,
    purged: bool = True,
) -> dict[str, object]:
    return {
        "round": number,
        "status": "ok",
        "pass": passed,
        "elapsed_seconds": elapsed_seconds,
        "agent_id": f"agent-{number}",
        "archived": archived,
        "purged": purged,
        "error": "",
        "initial_human_memory": "",
        "final_human_memory": "Rocky",
        "deterministic_score": {
            "pass": passed,
            "forbidden_hit_count": number,
            "human_memory_changed": passed,
            "expected_facts_passed": passed,
        },
        "judge": {"ok": True, "pass": passed},
        "turns": [
            {
                "turn_index": 1,
                "user_input": "My dog is Rocky",
                "assistant_replies": ["Rocky is lovely."],
                "elapsed_seconds": elapsed_seconds / 2,
                "memory_changed_this_turn": passed,
                "human_memory_before_turn": "",
                "human_memory_after_turn": "Rocky",
                "tool_calls": [{"name": "memory_replace"}],
                "memory_tool_calls": [{"name": "memory_replace"}],
                "sequence": [],
            }
        ],
        "persistent_state": (
            {
                "memory_blocks": [
                    {
                        "label": "human",
                        "value": "The user has a dog named Rocky.",
                        "description": "Durable facts about the user.",
                        "limit": 5000,
                    },
                    {"label": "persona", "value": "Be warm and concise."},
                ]
            }
            if number == 1
            else {}
        ),
    }


def _create_completed_run(tmp_path: Path):
    from ade_api.features.test_center.orchestrator import TestRunOrchestrator

    state_root = tmp_path / "runtime" / "test-runs"
    orchestrator = TestRunOrchestrator(project_root=tmp_path, state_root=state_root)
    run_id, output_dir = orchestrator._run_store.allocate_output_directory()
    orchestrator._run_store.create_run(
        run_id=run_id,
        run_type="chat_memory_eval",
        output_dir=output_dir,
        command=["python", "workflows/evals/chat_memory_eval/run.py"],
        options={
            "model": "openai-proxy/dgx_vllm::qwen",
            "rounds": 2,
            "judge_enabled": True,
        },
    )
    with orchestrator._run_store.locked_run(run_id) as run:
        assert run is not None
        run["status"] = "failed"
        run["finished_at"] = "2026-08-26T00:00:03+00:00"
        run["exit_code"] = 1
        orchestrator._run_store.persist(run)

    (output_dir / "chat_memory_eval_20260826_000000_summary.json").write_text(
        json.dumps(_summary_payload()), encoding="utf-8"
    )
    (output_dir / "chat_memory_eval_20260826_000000.jsonl").write_text(
        "\n".join(
            json.dumps(
                _round_payload(
                    number=number,
                    passed=passed,
                    elapsed_seconds=elapsed,
                )
            )
            for number, passed, elapsed in ((1, True, 2.0), (2, False, 4.0))
        )
        + "\n",
        encoding="utf-8",
    )
    return orchestrator, run_id, output_dir


def test_chat_memory_evaluation_detail_reads_scoped_artifacts_and_metrics(
    tmp_path: Path,
) -> None:
    orchestrator, run_id, _ = _create_completed_run(tmp_path)

    evaluations = orchestrator.list_chat_memory_evaluations()
    assert len(evaluations) == 1
    item = evaluations[0]
    assert item["run_id"] == run_id
    assert item["run_status"] == "failed"
    assert item["ready"] is True
    assert item["config"] == {
        "model": "openai-proxy/dgx_vllm::qwen",
        "prompt_key": "chat_v20260516",
        "persona_key": "chat_linxiaotang",
        "embedding": "letta/letta-free",
        "fixture_key": "recent_user_chat_turns",
        "rounds": 2,
        "timeout_seconds": 180.0,
        "retry_count": 0,
        "judge_enabled": True,
    }
    assert item["metrics"] == {
        "rounds_total": 2,
        "rounds_passed": 1,
        "rounds_failed": 1,
        "errors": 0,
        "pass_rate": 0.5,
        "average_elapsed_seconds": 3.0,
        "forbidden_hit_count": 3,
        "memory_changed_rounds": 1,
        "expected_facts_passed_rounds": 1,
        "memory_tool_call_count": 2,
        "total_tool_call_count": 2,
        "cleanup_passed_rounds": 2,
    }

    detail = orchestrator.get_chat_memory_evaluation(run_id)
    assert detail is not None
    assert detail["fixture"]["key"] == "recent_user_chat_turns"
    assert [round_["passed"] for round_ in detail["rounds"]] == [True, False]
    assert detail["rounds"][0]["turns"][0]["memory_tool_calls"] == [
        {"name": "memory_replace"}
    ]
    assert detail["rounds"][0]["memory_blocks"] == [
        {
            "label": "human",
            "value": "The user has a dog named Rocky.",
            "description": "Durable facts about the user.",
            "limit": 5000,
        },
        {
            "label": "persona",
            "value": "Be warm and concise.",
            "description": None,
            "limit": None,
        },
    ]
    assert detail["rounds"][1]["memory_blocks"] == []
    ChatMemoryEvaluationDetailResponse.model_validate(detail)


def test_chat_memory_evaluation_running_run_exposes_persisted_options(
    tmp_path: Path,
) -> None:
    from ade_api.features.test_center.orchestrator import TestRunOrchestrator

    orchestrator = TestRunOrchestrator(
        project_root=tmp_path,
        state_root=tmp_path / "runtime" / "test-runs",
    )
    run_id, output_dir = orchestrator._run_store.allocate_output_directory()
    orchestrator._run_store.create_run(
        run_id=run_id,
        run_type="chat_memory_eval",
        output_dir=output_dir,
        command=["python", "workflows/evals/chat_memory_eval/run.py"],
        options={
            "model": "openai-proxy/test::model",
            "rounds": 3,
            "judge_enabled": False,
        },
    )
    with orchestrator._run_store.locked_run(run_id) as run:
        assert run is not None
        run["status"] = "running"
        orchestrator._run_store.persist(run)

    item = orchestrator.list_chat_memory_evaluations()[0]
    assert item["ready"] is False
    assert item["metrics"] is None
    assert item["config"] == {
        "model": "openai-proxy/test::model",
        "prompt_key": "chat_v20260516",
        "persona_key": "chat_linxiaotang",
        "embedding": "letta/letta-free",
        "fixture_key": "recent_user_chat_turns",
        "rounds": 3,
        "timeout_seconds": 180.0,
        "retry_count": 0,
        "judge_enabled": False,
    }


def test_chat_memory_evaluation_list_filters_runs_and_sorts_newest_first(
    tmp_path: Path,
) -> None:
    from ade_api.features.test_center.orchestrator import TestRunOrchestrator

    orchestrator = TestRunOrchestrator(
        project_root=tmp_path,
        state_root=tmp_path / "runtime" / "test-runs",
    )
    for run_id, run_type, created_at in (
        ("older-eval", "chat_memory_eval", "2026-08-26T00:00:00+00:00"),
        ("non-eval", "ade_api_e2e_check", "2026-08-26T00:00:02+00:00"),
        ("newer-eval", "chat_memory_eval", "2026-08-26T00:00:03+00:00"),
    ):
        output_dir = orchestrator._run_store.state_root / run_id
        output_dir.mkdir()
        orchestrator._run_store.create_run(
            run_id=run_id,
            run_type=run_type,
            output_dir=output_dir,
            command=["python", "run.py"],
        )
        with orchestrator._run_store.locked_run(run_id) as run:
            assert run is not None
            run["created_at"] = created_at
            orchestrator._run_store.persist(run)

    payload = {"items": orchestrator.list_chat_memory_evaluations()}
    assert [item["run_id"] for item in payload["items"]] == [
        "newer-eval",
        "older-eval",
    ]
    ChatMemoryEvaluationListResponse.model_validate(payload)


def test_orchestrator_persists_chat_memory_request_options(tmp_path: Path) -> None:
    from ade_api.features.test_center.orchestrator import TestRunOrchestrator

    state_root = tmp_path / "runtime" / "test-runs"
    orchestrator = TestRunOrchestrator(project_root=tmp_path, state_root=state_root)
    orchestrator._process_executor.start = lambda _: None

    created = orchestrator.create_run(
        run_type="chat_memory_eval",
        model="openai-proxy/test::model",
        retry_count=0,
    )

    manifest_path = state_root / created["run_id"] / "run.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["options"] == {
        "model": "openai-proxy/test::model",
        "retry_count": 0,
    }


def test_chat_memory_evaluation_historical_manifest_without_options_is_readable(
    tmp_path: Path,
) -> None:
    from ade_api.features.test_center.orchestrator import TestRunOrchestrator

    state_root = tmp_path / "runtime" / "test-runs"
    output_dir = state_root / "historical-run"
    output_dir.mkdir(parents=True)
    (output_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "historical-run",
                "run_type": "chat_memory_eval",
                "status": "passed",
                "command": ["python", "workflows/evals/chat_memory_eval/run.py"],
                "created_at": "2026-08-26T00:00:00+00:00",
                "started_at": "2026-08-26T00:00:01+00:00",
                "finished_at": "2026-08-26T00:00:02+00:00",
                "exit_code": 0,
                "cancel_requested": False,
                "output_tail": [],
                "error": "",
            }
        ),
        encoding="utf-8",
    )

    item = TestRunOrchestrator(
        project_root=tmp_path,
        state_root=state_root,
    ).list_chat_memory_evaluations()[0]
    assert item["ready"] is False
    assert item["config"]["model"] == "openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8"


def test_chat_memory_evaluation_list_keeps_malformed_artifacts_unready(
    tmp_path: Path,
) -> None:
    from ade_api.features.test_center.chat_memory_evaluations import (
        ChatMemoryEvaluationArtifactUnavailable,
    )

    orchestrator, run_id, output_dir = _create_completed_run(tmp_path)
    (output_dir / "chat_memory_eval_20260826_000000.jsonl").write_text(
        "not-json\n", encoding="utf-8"
    )

    item = orchestrator.list_chat_memory_evaluations()[0]
    assert item["run_id"] == run_id
    assert item["ready"] is False
    assert item["metrics"] is None

    with pytest.raises(ChatMemoryEvaluationArtifactUnavailable) as error:
        orchestrator.get_chat_memory_evaluation(run_id)
    assert "JSONL" in str(error.value)


def test_chat_memory_evaluation_projects_reduced_error_rows(tmp_path: Path) -> None:
    orchestrator, run_id, output_dir = _create_completed_run(tmp_path)
    summary = _summary_payload()
    summary.update(
        {
            "rounds_total": 1,
            "rounds_passed": 0,
            "rounds_failed": 1,
            "errors": 1,
            "pass_rate": 0.0,
        }
    )
    summary["config"] = {**summary["config"], "rounds": 1}
    (output_dir / "chat_memory_eval_20260826_000000_summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )
    (output_dir / "chat_memory_eval_20260826_000000.jsonl").write_text(
        json.dumps(
            {
                "run_id": "workflow-run-id",
                "round": 1,
                "status": "error",
                "pass": False,
                "elapsed_seconds": 1.25,
                "forbidden_hit_count": 0,
                "human_memory_changed": False,
                "expected_facts_passed": False,
                "missing_expected_facts": "dog_name,dog_breed",
                "judge_enabled": True,
                "judge_ok": False,
                "judge_pass": "",
                "judge_score": "",
                "agent_id": "agent-error",
                "archived": True,
                "purged": True,
                "error": "provider timed out",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    item = orchestrator.list_chat_memory_evaluations()[0]
    assert item["run_id"] == run_id
    assert item["ready"] is True
    assert item["metrics"]["errors"] == 1
    assert item["metrics"]["cleanup_passed_rounds"] == 1

    detail = orchestrator.get_chat_memory_evaluation(run_id)
    assert detail is not None
    round_ = detail["rounds"][0]
    assert round_["status"] == "error"
    assert round_["error"] == "provider timed out"
    assert round_["turns"] == []
    assert round_["memory_blocks"] == []
    assert round_["deterministic_score"] == {
        "pass": False,
        "forbidden_hit_count": 0,
        "forbidden_hits": [],
        "human_memory_changed": False,
        "expected_facts_passed": False,
        "missing_expected_facts": ["dog_name", "dog_breed"],
    }


def test_chat_memory_evaluation_missing_artifacts_return_not_ready_and_409(
    tmp_path: Path,
) -> None:
    from ade_api.features.test_center.chat_memory_evaluations import (
        ChatMemoryEvaluationArtifactUnavailable,
    )
    from ade_api.features.test_center.orchestrator import TestRunOrchestrator

    orchestrator = TestRunOrchestrator(
        project_root=tmp_path,
        state_root=tmp_path / "runtime" / "test-runs",
    )
    run_id, output_dir = orchestrator._run_store.allocate_output_directory()
    orchestrator._run_store.create_run(
        run_id=run_id,
        run_type="chat_memory_eval",
        output_dir=output_dir,
        command=["python", "workflows/evals/chat_memory_eval/run.py"],
    )
    with orchestrator._run_store.locked_run(run_id) as run:
        assert run is not None
        run["status"] = "passed"
        orchestrator._run_store.persist(run)

    assert orchestrator.list_chat_memory_evaluations()[0]["ready"] is False
    with pytest.raises(ChatMemoryEvaluationArtifactUnavailable):
        orchestrator.get_chat_memory_evaluation(run_id)


def test_chat_memory_evaluation_reader_never_reads_outside_state_root(
    tmp_path: Path,
) -> None:
    from ade_api.features.test_center.orchestrator import TestRunOrchestrator

    state_root = tmp_path / "runtime" / "test-runs"
    output_dir = state_root / "run-1"
    output_dir.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "chat_memory_eval_20260826_000000_summary.json").write_text(
        json.dumps(_summary_payload()), encoding="utf-8"
    )
    (outside / "chat_memory_eval_20260826_000000.jsonl").write_text(
        json.dumps(_round_payload(number=1, passed=True, elapsed_seconds=1.0)),
        encoding="utf-8",
    )
    (output_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "run_type": "chat_memory_eval",
                "status": "passed",
                "command": ["python", "workflows/evals/chat_memory_eval/run.py"],
                "output_dir": str(outside),
                "created_at": "2026-08-26T00:00:00+00:00",
                "started_at": "2026-08-26T00:00:01+00:00",
                "finished_at": "2026-08-26T00:00:02+00:00",
                "exit_code": 0,
                "cancel_requested": False,
                "output_tail": [],
                "error": "",
            }
        ),
        encoding="utf-8",
    )

    orchestrator = TestRunOrchestrator(project_root=tmp_path, state_root=state_root)
    assert orchestrator.list_chat_memory_evaluations()[0]["ready"] is False


def test_chat_memory_evaluation_api_returns_404_and_409(monkeypatch) -> None:
    from ade_api.features.test_center.chat_memory_evaluations import (
        ChatMemoryEvaluationArtifactUnavailable,
    )

    class _FakeOrchestrator:
        def get_chat_memory_evaluation(self, run_id: str):
            if run_id == "missing":
                return None
            raise ChatMemoryEvaluationArtifactUnavailable(
                "Chat-memory evaluation JSONL artifact is invalid"
            )

    monkeypatch.setattr(api, "ensure_ade_api_enabled", lambda: None)

    with pytest.raises(HTTPException) as missing:
        asyncio.run(api.get_chat_memory_evaluation("missing", _FakeOrchestrator()))
    assert missing.value.status_code == 404

    with pytest.raises(HTTPException) as unavailable:
        asyncio.run(api.get_chat_memory_evaluation("broken", _FakeOrchestrator()))
    assert unavailable.value.status_code == 409


def test_chat_memory_evaluation_list_api_returns_typed_items(monkeypatch) -> None:
    class _FakeOrchestrator:
        def list_chat_memory_evaluations(self):
            return [
                {
                    "run_id": "run-1",
                    "run_status": "running",
                    "created_at": "2026-08-26T00:00:00+00:00",
                    "finished_at": "",
                    "ready": False,
                    "config": {
                        "model": "openai-proxy/test::model",
                        "prompt_key": "chat_v20260516",
                        "persona_key": "chat_linxiaotang",
                        "embedding": "letta/letta-free",
                        "fixture_key": "recent_user_chat_turns",
                        "rounds": 1,
                        "timeout_seconds": 180.0,
                        "retry_count": 0,
                        "judge_enabled": False,
                    },
                    "metrics": None,
                }
            ]

    monkeypatch.setattr(api, "ensure_ade_api_enabled", lambda: None)

    payload = asyncio.run(api.list_chat_memory_evaluations(_FakeOrchestrator()))
    assert payload["items"][0]["run_id"] == "run-1"
    ChatMemoryEvaluationListResponse.model_validate(payload)


def test_chat_memory_evaluation_routes_serialize_read_models(monkeypatch) -> None:
    class _Services:
        letta_agent_service = object()

    class _FakeOrchestrator:
        def list_chat_memory_evaluations(self):
            return [
                {
                    "run_id": "run-1",
                    "run_status": "running",
                    "created_at": "2026-08-26T00:00:00+00:00",
                    "finished_at": "",
                    "ready": False,
                    "config": {
                        "model": "openai-proxy/test::model",
                        "prompt_key": "chat_v20260516",
                        "persona_key": "chat_linxiaotang",
                        "embedding": "letta/letta-free",
                        "fixture_key": "recent_user_chat_turns",
                        "rounds": 1,
                        "timeout_seconds": 180.0,
                        "retry_count": 0,
                        "judge_enabled": False,
                    },
                    "metrics": None,
                }
            ]

        def get_chat_memory_evaluation(self, _run_id: str):
            raise api.ChatMemoryEvaluationArtifactUnavailable(
                "Chat-memory evaluation artifacts are not ready"
            )

    monkeypatch.setattr(app_module, "initialize_dependencies", lambda: _Services())
    monkeypatch.setattr(app_module, "shutdown_dependencies", lambda: None)
    monkeypatch.setattr(app_module, "validate_capabilities_startup", lambda _: None)
    app = create_app()
    app.dependency_overrides[get_test_orchestrator] = _FakeOrchestrator

    with TestClient(app) as client:
        list_response = client.get("/api/v2/test-center/chat-memory-evaluations")
        detail_response = client.get(
            "/api/v2/test-center/chat-memory-evaluations/run-1"
        )

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["ready"] is False
    assert detail_response.status_code == 409


def test_chat_memory_evaluation_detail_route_omits_absent_memory_metadata(
    monkeypatch, tmp_path: Path
) -> None:
    class _Services:
        letta_agent_service = object()

    orchestrator, run_id, _ = _create_completed_run(tmp_path)
    monkeypatch.setattr(app_module, "initialize_dependencies", lambda: _Services())
    monkeypatch.setattr(app_module, "shutdown_dependencies", lambda: None)
    monkeypatch.setattr(app_module, "validate_capabilities_startup", lambda _: None)
    app = create_app()
    app.dependency_overrides[get_test_orchestrator] = lambda: orchestrator

    with TestClient(app) as client:
        response = client.get(f"/api/v2/test-center/chat-memory-evaluations/{run_id}")

    assert response.status_code == 200
    memory_blocks = response.json()["rounds"][0]["memory_blocks"]
    assert memory_blocks[0]["description"] == "Durable facts about the user."
    assert "description" not in memory_blocks[1]
    assert "limit" not in memory_blocks[1]
