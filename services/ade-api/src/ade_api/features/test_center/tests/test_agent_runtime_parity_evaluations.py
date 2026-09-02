from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

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
    *,
    schema_version: int = 2,
    legacy_passed: bool = True,
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
            "round": round_index,
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
        for round_index in range(1, 4)
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
        "schema_version": schema_version,
        "kind": "agent-runtime-parity-spec",
        "run_id": artifact_run_id,
        "fixture": {
            "key": "recent_user_chat_turns",
            "turns": ["你好"],
            "sha256": fixture_sha256,
        },
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
        "schema_version": schema_version,
        "kind": "agent-runtime-parity-provenance",
        "run_id": artifact_run_id,
        "parity_spec_sha256": spec_sha256,
        "normalized_turns_sha256": turns_sha256,
        "source_identity": {
            "revision": "a" * 40,
            "dirty": False,
            "fingerprint": "b" * 64,
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
        "all_turns_succeeded": True,
        "timeout_retry_controls_exact": True,
    }
    legacy_checks = {
        **shared_checks,
        "expected_facts_captured": legacy_passed,
    }
    comparison_checks = (
        {
            "preflight_completed": True,
            "inputs_comparable": True,
            "all_paired_rounds_pass": legacy_passed,
            "cleanup_complete": True,
            "zero_retry_policy": True,
        }
        if schema_version == 1
        else {
            "preflight_completed": True,
            "inputs_comparable": True,
            "all_native_rounds_pass": True,
            "native_not_worse_than_legacy": True,
            "cleanup_complete": True,
            "zero_retry_policy": True,
        }
    )
    comparison = {
        "schema_version": schema_version,
        "kind": "agent-runtime-parity-comparison",
        "run_id": artifact_run_id,
        "pass": True if schema_version == 2 else legacy_passed,
        "checks": comparison_checks,
        "artifact_inputs": {
            "parity_spec_sha256": spec_sha256,
            "provenance_sha256": provenance_sha256,
            "normalized_turns_sha256": turns_sha256,
        },
        "preflight_error": None,
        "comparability": {
            "pass": True,
            "checks": {
                "parity_spec_hash_present": True,
                "source_identity_complete": True,
                "native_worker_build_matches_evaluator": True,
                "legacy_inputs_available": True,
                "fixture_hash_present": True,
                "all_native_rounds_have_definitions": True,
                "prompt_snapshots_match": True,
                "persona_snapshots_match": True,
                "conversation_models_match": True,
                "reviewer_models_match": True,
                "native_embedding_matches": True,
            },
            "fixture_sha256": fixture_sha256,
        },
        "cleanup": cleanup,
        **(
            {
                "baseline": {
                    "engine": "letta-v2",
                    "role": "observed_incumbent",
                    "rounds_passed": 3 if legacy_passed else 0,
                    "rounds_completed": 3,
                },
                "candidate": {
                    "engine": "ade-native-v3",
                    "role": "cutover_candidate",
                    "rounds_passed": 3,
                    "rounds_completed": 3,
                },
            }
            if schema_version == 2
            else {}
        ),
        "rounds": [
            {
                "round": index,
                "pass": True if schema_version == 2 else legacy_passed,
                **(
                    {"native_not_worse_than_legacy": True}
                    if schema_version == 2
                    else {}
                ),
                "legacy_score": {
                    "pass": legacy_passed,
                    "checks": legacy_checks,
                },
                "native_score": {
                    "pass": True,
                    "checks": {
                        **shared_checks,
                        "agent_studio_session_lifecycle": True,
                    },
                },
            }
            for index in range(1, 4)
        ],
    }
    comparison_sha256 = _write_signed_json(
        evidence_root / "comparison.json", comparison
    )
    summary = {
        "schema_version": schema_version,
        "kind": "agent-runtime-parity-summary",
        "run_id": artifact_run_id,
        "pass": True if schema_version == 2 else legacy_passed,
        "rounds_requested": 3,
        "rounds_completed": 3,
        "rounds_passed": 3 if schema_version == 2 else (3 if legacy_passed else 0),
        **(
            {
                "native_rounds_passed": 3,
                "legacy_rounds_passed": 3 if legacy_passed else 0,
                "native_not_worse_than_legacy": True,
            }
            if schema_version == 2
            else {}
        ),
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


def _read_unsigned_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    payload.pop("artifact_sha256", None)
    return payload


def _rewrite_bundle(
    evidence_root: Path,
    mutate: Callable[
        [
            dict[str, object],
            dict[str, object],
            dict[str, object],
            dict[str, object],
            list[dict[str, Any]],
        ],
        None,
    ],
) -> None:
    """Re-sign a test artifact bundle after a deliberate semantic mutation."""

    spec = _read_unsigned_json(evidence_root / "parity-spec.json")
    provenance = _read_unsigned_json(evidence_root / "provenance.json")
    comparison = _read_unsigned_json(evidence_root / "comparison.json")
    summary = _read_unsigned_json(evidence_root / "summary.json")
    turns_path = evidence_root / "normalized-turns.jsonl"
    turns = [
        json.loads(line)
        for line in turns_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    mutate(spec, provenance, comparison, summary, turns)

    turns_bytes = b"".join(
        (
            json.dumps(turn, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
        for turn in turns
    )
    turns_path.write_bytes(turns_bytes)
    turns_sha256 = hashlib.sha256(turns_bytes).hexdigest()
    spec_sha256 = _write_signed_json(evidence_root / "parity-spec.json", spec)
    provenance["parity_spec_sha256"] = spec_sha256
    provenance["normalized_turns_sha256"] = turns_sha256
    provenance_sha256 = _write_signed_json(
        evidence_root / "provenance.json", provenance
    )
    comparison["artifact_inputs"] = {
        "parity_spec_sha256": spec_sha256,
        "provenance_sha256": provenance_sha256,
        "normalized_turns_sha256": turns_sha256,
    }
    comparison_sha256 = _write_signed_json(
        evidence_root / "comparison.json", comparison
    )
    summary["artifact_inputs"] = {
        **comparison["artifact_inputs"],
        "comparison_sha256": comparison_sha256,
    }
    _write_signed_json(evidence_root / "summary.json", summary)


def test_parity_reader_projects_verified_paired_evidence(tmp_path: Path) -> None:
    orchestrator, run_id, _ = _create_completed_parity_run(tmp_path)

    items = orchestrator.list_agent_runtime_parity_evaluations()
    assert len(items) == 1
    assert items[0]["ready"] is True
    assert items[0]["evidence_schema_version"] == 2
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
    assert {(item["engine"], item["round"]) for item in detail["turns"]} == {
        (engine, round_index)
        for engine in ("letta-v2", "ade-native-v3")
        for round_index in range(1, 4)
    }


def test_parity_reader_keeps_a_failing_legacy_baseline_visible_without_veto(
    tmp_path: Path,
) -> None:
    orchestrator, run_id, _ = _create_completed_parity_run(
        tmp_path,
        legacy_passed=False,
    )

    detail = orchestrator.get_agent_runtime_parity_evaluation(run_id)

    assert detail["passed"] is True
    assert detail["native_rounds_passed"] == 3
    assert detail["legacy_rounds_passed"] == 0
    assert detail["native_not_worse_than_legacy"] is True
    assert [item["native_passed"] for item in detail["rounds"]] == [True] * 3
    assert [item["legacy_passed"] for item in detail["rounds"]] == [False] * 3


def test_parity_reader_keeps_schema_v1_history_readable(tmp_path: Path) -> None:
    orchestrator, run_id, _ = _create_completed_parity_run(
        tmp_path,
        schema_version=1,
    )

    detail = orchestrator.get_agent_runtime_parity_evaluation(run_id)

    assert detail["passed"] is True
    assert detail["evidence_schema_version"] == 1
    assert detail["native_rounds_passed"] == 3
    assert detail["legacy_rounds_passed"] == 3


def test_parity_reader_preserves_a_divergent_schema_v1_gate_as_history(
    tmp_path: Path,
) -> None:
    orchestrator, run_id, _ = _create_completed_parity_run(
        tmp_path,
        schema_version=1,
        legacy_passed=False,
    )

    detail = orchestrator.get_agent_runtime_parity_evaluation(run_id)

    assert detail["passed"] is False
    assert detail["evidence_schema_version"] == 1
    assert detail["native_rounds_passed"] == 3
    assert detail["legacy_rounds_passed"] == 0
    assert detail["native_not_worse_than_legacy"] is True


def test_parity_reader_rejects_a_tampered_non_regression_result(
    tmp_path: Path,
) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)

    def mutate(_spec, _provenance, comparison, _summary, _turns) -> None:
        comparison["rounds"][0]["native_not_worse_than_legacy"] = False

    _rewrite_bundle(evidence_root, mutate)

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(AgentRuntimeParityArtifactUnavailable, match="non-regression"):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


def test_parity_reader_rejects_gate_checks_that_contradict_round_evidence(
    tmp_path: Path,
) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)

    def mutate(_spec, _provenance, comparison, summary, _turns) -> None:
        comparison["checks"]["all_native_rounds_pass"] = False
        comparison["pass"] = False
        summary["pass"] = False

    _rewrite_bundle(evidence_root, mutate)

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(AgentRuntimeParityArtifactUnavailable, match="engine evidence"):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


@pytest.mark.parametrize("section", ("baseline", "candidate"))
def test_parity_reader_rejects_engine_summaries_that_contradict_round_evidence(
    tmp_path: Path,
    section: str,
) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)

    def mutate(_spec, _provenance, comparison, _summary, _turns) -> None:
        comparison[section]["rounds_passed"] = 2

    _rewrite_bundle(evidence_root, mutate)

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(AgentRuntimeParityArtifactUnavailable, match=section):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


def test_parity_reader_rejects_summary_engine_counts_that_contradict_rounds(
    tmp_path: Path,
) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)

    def mutate(_spec, _provenance, _comparison, summary, _turns) -> None:
        summary["legacy_rounds_passed"] = 2

    _rewrite_bundle(evidence_root, mutate)

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(AgentRuntimeParityArtifactUnavailable, match="engine counts"):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


def test_parity_reader_rejects_comparability_that_contradicts_its_checks(
    tmp_path: Path,
) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)

    def mutate(_spec, _provenance, comparison, _summary, _turns) -> None:
        comparison["comparability"]["checks"]["prompt_snapshots_match"] = False

    _rewrite_bundle(evidence_root, mutate)

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(AgentRuntimeParityArtifactUnavailable, match="comparability"):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


def test_parity_reader_rejects_cleanup_that_contradicts_runtime_outcomes(
    tmp_path: Path,
) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)

    def mutate(_spec, provenance, comparison, _summary, _turns) -> None:
        comparison["cleanup"]["native"]["completed"] = False
        provenance["cleanup"]["native"]["completed"] = False

    _rewrite_bundle(evidence_root, mutate)

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(AgentRuntimeParityArtifactUnavailable, match="cleanup state"):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


def test_parity_reader_projects_malformed_signed_shapes_as_unavailable(
    tmp_path: Path,
) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)

    def mutate(_spec, _provenance, comparison, summary, _turns) -> None:
        comparison["preflight_error"] = []
        summary["preflight_error"] = []

    _rewrite_bundle(evidence_root, mutate)

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(
        AgentRuntimeParityArtifactUnavailable,
        match="invalid evidence shape",
    ):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


def test_parity_reader_rejects_an_incomplete_canonical_check_set(
    tmp_path: Path,
) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)

    def mutate(_spec, _provenance, comparison, _summary, _turns) -> None:
        comparison["checks"].pop("all_native_rounds_pass")

    _rewrite_bundle(evidence_root, mutate)

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(AgentRuntimeParityArtifactUnavailable, match="check set"):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


def test_parity_reader_rejects_partial_rounds_after_successful_preflight(
    tmp_path: Path,
) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)

    def mutate(_spec, _provenance, comparison, summary, _turns) -> None:
        comparison["checks"]["all_native_rounds_pass"] = False
        comparison["checks"]["native_not_worse_than_legacy"] = False
        comparison["pass"] = False
        comparison["rounds"] = comparison["rounds"][:2]
        summary["pass"] = False
        summary["rounds_completed"] = 2
        summary["rounds_passed"] = 2
        summary["native_rounds_passed"] = 2
        summary["legacy_rounds_passed"] = 2
        summary["native_not_worse_than_legacy"] = False

    _rewrite_bundle(evidence_root, mutate)

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(AgentRuntimeParityArtifactUnavailable, match="exactly"):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


def test_parity_reader_rejects_missing_required_engine_evidence(
    tmp_path: Path,
) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)

    def mutate(_spec, _provenance, _comparison, _summary, turns) -> None:
        turns[:] = [
            turn
            for turn in turns
            if not (turn["engine"] == "ade-native-v3" and turn["round"] == 2)
        ]

    _rewrite_bundle(evidence_root, mutate)

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(AgentRuntimeParityArtifactUnavailable, match="engine"):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


@pytest.mark.parametrize(
    ("field", "value"),
    (("revision", "not-a-git-revision"), ("fingerprint", "not-a-fingerprint")),
)
def test_parity_reader_rejects_invalid_source_identity(
    tmp_path: Path, field: str, value: str
) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)

    def mutate(_spec, provenance, _comparison, _summary, _turns) -> None:
        provenance["source_identity"][field] = value

    _rewrite_bundle(evidence_root, mutate)

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(AgentRuntimeParityArtifactUnavailable, match="source identity"):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


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

    def mutate(_spec, _provenance, comparison, summary, turns) -> None:
        turns.clear()
        comparison.update(
            {
                "pass": False,
                "checks": {
                    "preflight_completed": False,
                    "inputs_comparable": False,
                    "all_native_rounds_pass": False,
                    "native_not_worse_than_legacy": False,
                    "cleanup_complete": True,
                    "zero_retry_policy": True,
                },
                "comparability": {
                    "pass": False,
                    "checks": {
                        "parity_spec_hash_present": True,
                        "source_identity_complete": True,
                        "native_worker_build_matches_evaluator": False,
                        "legacy_inputs_available": False,
                        "fixture_hash_present": True,
                        "all_native_rounds_have_definitions": False,
                        "prompt_snapshots_match": False,
                        "persona_snapshots_match": False,
                        "conversation_models_match": False,
                        "reviewer_models_match": False,
                        "native_embedding_matches": False,
                    },
                    "fixture_sha256": comparison["comparability"]["fixture_sha256"],
                },
                "preflight_error": {
                    "kind": "public_api_error",
                    "code": "offline",
                },
                "rounds": [],
                "baseline": {
                    "engine": "letta-v2",
                    "role": "observed_incumbent",
                    "rounds_passed": 0,
                    "rounds_completed": 0,
                },
                "candidate": {
                    "engine": "ade-native-v3",
                    "role": "cutover_candidate",
                    "rounds_passed": 0,
                    "rounds_completed": 0,
                },
            }
        )
        summary.update(
            {
                "pass": False,
                "rounds_completed": 0,
                "rounds_passed": 0,
                "native_rounds_passed": 0,
                "legacy_rounds_passed": 0,
                "native_not_worse_than_legacy": False,
                "preflight_error": {
                    "kind": "public_api_error",
                    "code": "offline",
                },
                "inputs_comparable": False,
            }
        )

    _rewrite_bundle(evidence_root, mutate)

    item = orchestrator.list_agent_runtime_parity_evaluations()[0]
    assert item["ready"] is True
    assert item["passed"] is False
    detail = orchestrator.get_agent_runtime_parity_evaluation(run_id)
    assert detail is not None
    assert detail["rounds"] == []
    assert detail["turns"] == []
    assert (
        detail["artifact_digests"]["normalized_turns_sha256"]
        == hashlib.sha256(b"").hexdigest()
    )
    assert detail["preflight_error"] == {
        "kind": "public_api_error",
        "code": "offline",
    }


@pytest.mark.parametrize(
    ("mutate", "message"),
    (
        (
            lambda comparison, turns: comparison.update(
                {"checks": {**comparison["checks"], "preflight_completed": False}}
            ),
            "preflight failure must not contain rounds",
        ),
        (
            lambda comparison, turns: (
                comparison.update(
                    {"checks": {**comparison["checks"], "preflight_completed": False}}
                ),
                turns.clear(),
                comparison.update({"rounds": []}),
            ),
            "preflight failure must include a public error",
        ),
    ),
)
def test_parity_reader_rejects_invalid_preflight_failure_evidence(
    tmp_path: Path,
    mutate: Callable[[dict[str, Any], list[dict[str, Any]]], object],
    message: str,
) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)

    def rewrite(_spec, _provenance, comparison, summary, turns) -> None:
        mutate(comparison, turns)
        comparison["pass"] = False
        summary.update(
            {
                "pass": False,
                "rounds_completed": len(comparison["rounds"]),
                "rounds_passed": 0,
                "preflight_error": comparison["preflight_error"],
            }
        )

    _rewrite_bundle(evidence_root, rewrite)

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(AgentRuntimeParityArtifactUnavailable, match=message):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


def test_parity_reader_rejects_turns_on_preflight_failure(tmp_path: Path) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)

    def mutate(_spec, _provenance, comparison, summary, _turns) -> None:
        comparison.update(
            {
                "pass": False,
                "checks": {
                    **comparison["checks"],
                    "preflight_completed": False,
                },
                "rounds": [],
                "preflight_error": {
                    "kind": "public_api_error",
                    "code": "offline",
                },
            }
        )
        summary.update(
            {
                "pass": False,
                "rounds_completed": 0,
                "rounds_passed": 0,
                "preflight_error": comparison["preflight_error"],
            }
        )

    _rewrite_bundle(evidence_root, mutate)

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(
        AgentRuntimeParityArtifactUnavailable,
        match="preflight failure must not contain normalized turns",
    ):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


def test_parity_reader_rejects_empty_turns_after_completed_preflight(
    tmp_path: Path,
) -> None:
    orchestrator, run_id, evidence_root = _create_completed_parity_run(tmp_path)

    def mutate(_spec, _provenance, _comparison, _summary, turns) -> None:
        turns.clear()

    _rewrite_bundle(evidence_root, mutate)

    assert orchestrator.list_agent_runtime_parity_evaluations()[0]["ready"] is False
    with pytest.raises(AgentRuntimeParityArtifactUnavailable, match="engine or round"):
        orchestrator.get_agent_runtime_parity_evaluation(run_id)


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
