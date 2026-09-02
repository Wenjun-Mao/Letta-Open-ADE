from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ade_api.features.test_center.agent_runtime_parity_evaluations import (
    AgentRuntimeParityArtifactUnavailable,
)
from ade_api.features.test_center.orchestrator import (
    TestRunOrchestrator as RunOrchestrator,
)


def _canonical_sha256(payload: object) -> str:
    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_signed_json(path: Path, payload: dict[str, object]) -> str:
    digest = _canonical_sha256(payload)
    path.write_text(
        json.dumps(
            {**payload, "artifact_sha256": digest},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    return digest


def _run_id() -> str:
    return "test-center-parity-001"


def _create_completed_parity_run(
    tmp_path: Path,
) -> tuple[RunOrchestrator, str, Path]:
    state_root = tmp_path / "runtime" / "test-runs"
    orchestrator = RunOrchestrator(project_root=tmp_path, state_root=state_root)
    run_id = _run_id()
    output_dir = state_root / run_id
    output_dir.mkdir(parents=True)
    orchestrator._run_store.create_run(
        run_id=run_id,
        run_type="agent_runtime_parity_eval",
        output_dir=output_dir,
        command=["python", "workflows/evals/agent_runtime_parity/run.py"],
        options={"rounds": 3, "retry_count": 0},
    )
    with orchestrator._run_store.locked_run(run_id) as run:
        assert run is not None
        run["status"] = "passed"
        run["finished_at"] = "2026-09-02T00:00:03+00:00"
        run["exit_code"] = 0
        orchestrator._run_store.persist(run)

    artifact_run_id = f"parity-{run_id}"
    evidence_root = output_dir / artifact_run_id
    evidence_root.mkdir()
    turns = [
        {
            "schema_version": 1,
            "engine": engine,
            "round": 1,
            "turn_index": 1,
            "user_content": "你好",
            "assistant_replies": ["你好呀"],
            "terminal_status": "succeeded",
            "timeout_seconds": 180.0,
            "retry_count": 0,
            "attempt_count": None if engine == "letta-v2" else 1,
            "transport_attempt_count": 1,
            "elapsed_seconds": 1.5,
            "tool_outcomes": [],
            "run_events": [] if engine == "ade-native-v3" else None,
            "memory_outcome": {"changed": True},
        }
        for engine in ("letta-v2", "ade-native-v3")
    ]
    turns_bytes = b"".join(
        (
            json.dumps(turn, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
        for turn in turns
    )
    (evidence_root / "normalized-turns.jsonl").write_bytes(turns_bytes)
    turns_sha256 = hashlib.sha256(turns_bytes).hexdigest()
    fixture_sha256 = hashlib.sha256(b"fixture").hexdigest()
    content_sha256 = hashlib.sha256(b"chat prompt").hexdigest()
    persona_sha256 = hashlib.sha256(b"chat persona").hexdigest()
    spec = {
        "schema_version": 1,
        "kind": "agent-runtime-parity-spec",
        "run_id": artifact_run_id,
        "fixture": {"key": "recent_user_chat_turns", "sha256": fixture_sha256},
        "controls": {
            "rounds": 3,
            "timeout_seconds": 180.0,
            "retry_count": 0,
            "client_transport_retries": 0,
        },
        "requested_inputs": {
            "prompt_key": "chat_v20260516",
            "persona_key": "chat_linxiaotang",
            "legacy": {
                "model": "openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8",
                "model_router_key": "dgx_vllm::qwen3.6-35b-a3b-fp8",
                "embedding": "letta/letta-free",
            },
            "native": {
                "conversation_model": "dgx_vllm::qwen3.6-35b-a3b-fp8",
                "reviewer_model": "dgx_vllm::qwen3.6-35b-a3b-fp8",
                "embedding_model": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
            },
        },
    }
    spec_sha256 = _write_signed_json(evidence_root / "parity-spec.json", spec)
    cleanup = {
        "legacy": {
            "required": True,
            "completed": True,
            "creation_indeterminate": False,
            "outcomes": [],
        },
        "native": {"required": True, "completed": True, "error": None},
        "completed": True,
    }
    provenance = {
        "schema_version": 1,
        "kind": "agent-runtime-parity-provenance",
        "run_id": artifact_run_id,
        "parity_spec_sha256": spec_sha256,
        "normalized_turns_sha256": turns_sha256,
        "source_identity": {
            "revision": "abc123",
            "dirty": False,
            "fingerprint": "source-fingerprint",
        },
        "legacy": {
            "inputs": {
                "prompt": {"content_sha256": content_sha256},
                "persona": {"content_sha256": persona_sha256},
            }
        },
        "native": {"worker_health": {"worker_ready": True}, "definitions": []},
        "cleanup": cleanup,
    }
    provenance_sha256 = _write_signed_json(
        evidence_root / "provenance.json", provenance
    )
    shared_checks = {
        "no_forbidden_disclosure": True,
        "expected_facts_captured": True,
        "all_turns_terminal": True,
        "timeout_retry_controls_exact": True,
    }
    comparison = {
        "schema_version": 1,
        "kind": "agent-runtime-parity-comparison",
        "run_id": artifact_run_id,
        "pass": True,
        "checks": {
            "preflight_completed": True,
            "inputs_comparable": True,
            "all_paired_rounds_pass": True,
            "cleanup_complete": True,
            "zero_retry_policy": True,
        },
        "artifact_inputs": {
            "parity_spec_sha256": spec_sha256,
            "provenance_sha256": provenance_sha256,
            "normalized_turns_sha256": turns_sha256,
        },
        "preflight_error": None,
        "comparability": {
            "pass": True,
            "checks": {"native_worker_build_matches_evaluator": True},
            "fixture_sha256": fixture_sha256,
        },
        "cleanup": cleanup,
        "rounds": [
            {
                "round": index,
                "pass": True,
                "legacy_score": {"pass": True, "checks": shared_checks},
                "native_score": {"pass": True, "checks": shared_checks},
            }
            for index in range(1, 4)
        ],
    }
    comparison_sha256 = _write_signed_json(
        evidence_root / "comparison.json", comparison
    )
    summary = {
        "schema_version": 1,
        "kind": "agent-runtime-parity-summary",
        "run_id": artifact_run_id,
        "pass": True,
        "rounds_requested": 3,
        "rounds_completed": 3,
        "rounds_passed": 3,
        "fixture": {"key": "recent_user_chat_turns", "sha256": fixture_sha256},
        "controls": {
            "timeout_seconds": 180.0,
            "retry_count": 0,
            "client_transport_retries": 0,
        },
        "artifact_inputs": {
            "parity_spec_sha256": spec_sha256,
            "provenance_sha256": provenance_sha256,
            "normalized_turns_sha256": turns_sha256,
            "comparison_sha256": comparison_sha256,
        },
        "preflight_error": None,
        "inputs_comparable": True,
        "cleanup_complete": True,
    }
    _write_signed_json(evidence_root / "summary.json", summary)
    return orchestrator, run_id, evidence_root


def test_parity_reader_projects_verified_paired_evidence(tmp_path: Path) -> None:
    orchestrator, run_id, _ = _create_completed_parity_run(tmp_path)

    items = orchestrator.list_agent_runtime_parity_evaluations()
    assert len(items) == 1
    assert items[0]["ready"] is True
    assert items[0]["passed"] is True
    assert items[0]["inputs_comparable"] is True
    assert items[0]["cleanup_complete"] is True
    assert items[0]["artifact_digests"]["evidence_sha256"]

    detail = orchestrator.get_agent_runtime_parity_evaluation(run_id)
    assert detail is not None
    assert detail["config"]["prompt_key"] == "chat_v20260516"
    assert detail["config"]["retry_count"] == 0
    assert detail["provenance"]["native_worker_build_matches"] is True
    assert [item["passed"] for item in detail["rounds"]] == [True, True, True]
    assert [item["engine"] for item in detail["turns"]] == [
        "letta-v2",
        "ade-native-v3",
    ]


def test_parity_reader_fails_closed_on_tampered_artifact(tmp_path: Path) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)
    comparison_path = evidence_root / "comparison.json"
    payload = json.loads(comparison_path.read_text(encoding="utf-8"))
    payload["pass"] = False
    comparison_path.write_text(json.dumps(payload), encoding="utf-8")

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(AgentRuntimeParityArtifactUnavailable, match="digest"):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


def test_parity_reader_keeps_a_completed_preflight_failure_inspectable(
    tmp_path: Path,
) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)
    comparison_path = evidence_root / "comparison.json"
    summary_path = evidence_root / "summary.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    comparison.update(
        {
            "pass": False,
            "checks": {
                "preflight_completed": False,
                "inputs_comparable": False,
                "all_paired_rounds_pass": False,
                "cleanup_complete": True,
                "zero_retry_policy": False,
            },
            "comparability": {
                "pass": False,
                "checks": {"legacy_inputs_available": False},
                "fixture_sha256": comparison["comparability"]["fixture_sha256"],
            },
            "preflight_error": {"kind": "public_api_error", "code": "offline"},
            "rounds": [],
        }
    )
    comparison.pop("artifact_sha256", None)
    comparison_sha256 = _write_signed_json(comparison_path, comparison)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update(
        {
            "pass": False,
            "rounds_completed": 0,
            "rounds_passed": 0,
            "preflight_error": {"kind": "public_api_error", "code": "offline"},
            "inputs_comparable": False,
        }
    )
    summary["artifact_inputs"]["comparison_sha256"] = comparison_sha256
    summary.pop("artifact_sha256", None)
    _write_signed_json(summary_path, summary)

    item = orchestrator.list_agent_runtime_parity_evaluations()[0]
    assert item["ready"] is True
    assert item["passed"] is False
    detail = orchestrator.get_agent_runtime_parity_evaluation(run_id)
    assert detail is not None
    assert detail["rounds"] == []
    assert detail["preflight_error"] == {
        "kind": "public_api_error",
        "code": "offline",
    }


def test_parity_descriptor_uses_ephemeral_service_credentials(monkeypatch) -> None:
    from ade_api.features.test_center.run_descriptors import get_run_descriptor

    parent = {
        "ADE_API_ADMIN_KEY": "legacy-secret",
        "ADE_API_OPERATOR_KEY": "native-secret",
        "ADE_API_DATABASE_URL": "postgresql+psycopg://private-db/ade",
    }
    environment = get_run_descriptor("agent_runtime_parity_eval").build_environment(
        {}, parent
    )

    assert (
        environment["AGENT_RUNTIME_PARITY_LEGACY_API_BASE_URL"]
        == "http://127.0.0.1:8000"
    )
    assert (
        environment["AGENT_RUNTIME_PARITY_NATIVE_API_BASE_URL"]
        == "http://ade-native-api:8000"
    )
    assert environment["AGENT_RUNTIME_PARITY_LEGACY_API_KEY"] == "legacy-secret"
    assert environment["AGENT_RUNTIME_PARITY_NATIVE_API_KEY"] == "native-secret"
    assert (
        environment["AGENT_RUNTIME_PARITY_DATABASE_URL"]
        == "postgresql+psycopg://private-db/ade"
    )


def test_parity_run_manifest_never_persists_launch_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "do-not-persist-this-secret"
    monkeypatch.setenv("ADE_API_ADMIN_KEY", secret)
    monkeypatch.setenv("ADE_API_OPERATOR_KEY", secret)
    monkeypatch.setenv("ADE_API_DATABASE_URL", f"postgresql+psycopg://{secret}/ade")
    orchestrator = RunOrchestrator(
        project_root=tmp_path,
        state_root=tmp_path / "runtime" / "test-runs",
    )
    orchestrator._process_executor.start = lambda _run_id: None

    created = orchestrator.create_run(
        run_type="agent_runtime_parity_eval",
        retry_count=0,
    )

    manifest_path = tmp_path / "runtime" / "test-runs" / created["run_id"] / "run.json"
    manifest = manifest_path.read_text(encoding="utf-8")
    assert secret not in manifest
    assert secret not in " ".join(created["command"])
    assert (
        orchestrator._process_executor._run_environments[created["run_id"]][
            "AGENT_RUNTIME_PARITY_LEGACY_API_KEY"
        ]
        == secret
    )


def test_cancelled_parity_run_discards_launch_credentials(tmp_path: Path) -> None:
    orchestrator = RunOrchestrator(
        project_root=tmp_path,
        state_root=tmp_path / "runtime" / "test-runs",
    )
    orchestrator._process_executor.start = lambda _run_id: None
    created = orchestrator.create_run(
        run_type="agent_runtime_parity_eval",
        retry_count=0,
    )
    run_id = created["run_id"]
    assert run_id in orchestrator._process_executor._run_environments

    assert orchestrator._process_executor.cancel(run_id) is True
    orchestrator._process_executor._run_worker(run_id)

    assert run_id not in orchestrator._process_executor._run_environments
