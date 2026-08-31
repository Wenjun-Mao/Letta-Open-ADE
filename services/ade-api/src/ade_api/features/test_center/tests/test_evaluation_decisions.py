from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException

from ade_api.features.test_center import api
from ade_api.features.test_center.chat_memory_evaluation_comparisons import (
    ChatMemoryEvaluationComparisonUnavailable,
)
from ade_api.features.test_center.chat_memory_evaluation_decisions import (
    ChatMemoryEvaluationDecisionConflict,
)
from ade_api.features.test_center.chat_memory_evaluations import (
    ChatMemoryEvaluationArtifactUnavailable,
)
from ade_api.features.test_center.contracts import (
    ChatMemoryEvaluationDecisionRequest,
)
from ade_api.features.test_center.orchestrator import (
    TestRunOrchestrator as RunOrchestrator,
)


def _sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _option_snapshot(*, key: str, revision: str) -> dict[str, Any]:
    identity_payload = {
        "key": key,
        "source_id": "test",
        "provider_model_id": key.split("/", 1)[-1],
        "upstream_provider_model_id": None,
        "sampling_defaults": {"temperature": 1.0},
        "scenario_sampling_defaults": {},
        "supports_top_k": True,
        "supports_thinking": False,
        "thinking_default_enabled": False,
        "profile_applied": True,
        "profile_source": "test-profile",
        "agent_studio_candidate": True,
        "agent_studio_compatible": True,
        "deployment": {"fingerprint": {"artifact_revision": revision}},
    }
    return {
        **identity_payload,
        "label": "Test chat",
        "source_label": "Test source",
        "identity_sha256": _sha256(identity_payload),
    }


def _template(kind: str, key: str, content: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "scenario": "chat",
        "key": key,
        "label": key,
        "description": "",
        "content": content,
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "updated_at": "2026-08-30T00:00:00Z",
    }


def _fixture() -> dict[str, Any]:
    return {
        "key": "recent_user_chat_turns",
        "description": "Memory behavior",
        "turns": ["My dog is Rocky"],
        "expected_facts": [
            {"key": "dog_name", "label": "Dog name", "aliases": ["Rocky"]}
        ],
        "forbidden_reply_substrings": ["我是AI"],
    }


def _provenance(
    *, run_id: str, prompt_content: str, model_revision: str, captured_at: str
) -> dict[str, Any]:
    prompt = _template("prompt", "chat_prompt", prompt_content)
    persona = _template("persona", "chat_persona", "Warm persona")
    model = _option_snapshot(key="openai-proxy/test::chat", revision=model_revision)
    embedding = _option_snapshot(key="letta/letta-free", revision="embedding-r1")
    fixture_sha256 = _sha256(_fixture())
    controls = {
        "rounds": 1,
        "timeout_seconds": 180.0,
        "retry_count": 0,
        "judge_enabled": False,
        "judge_model_key": "",
    }
    configuration = {
        "scenario": "chat",
        "model_identity_sha256": model["identity_sha256"],
        "embedding_identity_sha256": embedding["identity_sha256"],
        "prompt_content_sha256": prompt["content_sha256"],
        "persona_content_sha256": persona["content_sha256"],
        "fixture_sha256": fixture_sha256,
        "controls": controls,
    }
    provenance = {
        "schema_version": 2,
        "run_id": run_id,
        "captured_at": captured_at,
        "configuration_sha256": _sha256(configuration),
        "fixture_sha256": fixture_sha256,
        "controls": controls,
        "prompt": prompt,
        "persona": persona,
        "model": model,
        "embedding": embedding,
    }
    provenance["provenance_sha256"] = _sha256(provenance)
    return provenance


def _create_run(
    orchestrator: RunOrchestrator,
    *,
    run_id: str,
    prompt_content: str,
    model_revision: str,
    passed: bool,
    elapsed_seconds: float,
    created_at: str,
) -> dict[str, Any]:
    output_dir = orchestrator._run_store.state_root / run_id
    output_dir.mkdir()
    orchestrator._run_store.create_run(
        run_id=run_id,
        run_type="chat_memory_eval",
        output_dir=output_dir,
        command=["python", "run.py"],
    )
    with orchestrator._run_store.locked_run(run_id) as run:
        assert run is not None
        run["status"] = "passed" if passed else "failed"
        run["created_at"] = created_at
        run["finished_at"] = created_at
        run["exit_code"] = 0 if passed else 1
        orchestrator._run_store.persist(run)

    provenance = _provenance(
        run_id=run_id,
        prompt_content=prompt_content,
        model_revision=model_revision,
        captured_at=created_at,
    )
    config = {
        "model": "openai-proxy/test::chat",
        "prompt_key": "chat_prompt",
        "persona_key": "chat_persona",
        "embedding": "letta/letta-free",
        "fixture_key": "recent_user_chat_turns",
        "rounds": 1,
        "timeout_seconds": 180.0,
        "retry_count": 0,
        "judge_enabled": False,
    }
    summary = {
        "run_id": run_id,
        "rounds_total": 1,
        "rounds_passed": int(passed),
        "rounds_failed": int(not passed),
        "errors": 0,
        "pass_rate": float(passed),
        "config": config,
        "fixture": _fixture(),
        "provenance": provenance,
    }
    final_memory = "Rocky" if passed else ""
    fact_score = {
        "key": "dog_name",
        "label": "Dog name",
        "passed": passed,
        "matched_aliases": ["Rocky"] if passed else [],
        "aliases": ["Rocky"],
    }
    deterministic_score = {
        "pass": passed,
        "forbidden_hits": [],
        "forbidden_hit_count": 0,
        "human_memory_changed": passed,
        "expected_fact_scores": [fact_score],
        "expected_facts_passed": passed,
        "missing_expected_facts": [] if passed else ["dog_name"],
    }
    round_payload = {
        "run_id": run_id,
        "round": 1,
        "status": "ok",
        "pass": passed,
        "elapsed_seconds": elapsed_seconds,
        "agent_id": f"agent-{run_id}",
        "archived": True,
        "purged": True,
        "error": "",
        "configuration_sha256": provenance["configuration_sha256"],
        "provenance_sha256": provenance["provenance_sha256"],
        "initial_human_memory": "",
        "final_human_memory": final_memory,
        "deterministic_score": deterministic_score,
        "judge": {"skipped": True},
        "turns": [
            {
                "turn_index": 1,
                "user_input": "My dog is Rocky",
                "assistant_replies": ["Rocky is lovely."],
                "elapsed_seconds": elapsed_seconds,
                "memory_changed_this_turn": passed,
                "human_memory_before_turn": "",
                "human_memory_after_turn": final_memory,
                "tool_calls": [],
                "memory_tool_calls": [],
            }
        ],
        "persistent_state": {"memory_blocks": []},
    }
    (output_dir / "chat_memory_eval_20260830_summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )
    (output_dir / "chat_memory_eval_20260830.jsonl").write_text(
        json.dumps(round_payload) + "\n", encoding="utf-8"
    )
    (output_dir / "chat_memory_eval_20260830_provenance.json").write_text(
        json.dumps(provenance), encoding="utf-8"
    )
    detail = orchestrator.get_chat_memory_evaluation(run_id)
    assert detail is not None
    return {**provenance, "evidence_sha256": detail["evidence_sha256"]}


def _orchestrator(tmp_path: Path) -> RunOrchestrator:
    return RunOrchestrator(
        project_root=tmp_path,
        state_root=tmp_path / "runtime" / "test-runs",
    )


def test_reader_verifies_and_exposes_content_addressed_provenance(
    tmp_path: Path,
) -> None:
    orchestrator = _orchestrator(tmp_path)
    provenance = _create_run(
        orchestrator,
        run_id="candidate",
        prompt_content="Candidate prompt",
        model_revision="model-r1",
        passed=True,
        elapsed_seconds=4.0,
        created_at="2026-08-30T00:00:01+00:00",
    )

    detail = orchestrator.get_chat_memory_evaluation("candidate")

    assert detail is not None
    assert detail["provenance"]["provenance_sha256"] == provenance["provenance_sha256"]
    assert detail["evidence_sha256"] == provenance["evidence_sha256"]
    assert detail["provenance_detail"]["prompt"]["content"] == "Candidate prompt"


def test_reader_rejects_tampered_provenance(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path)
    _create_run(
        orchestrator,
        run_id="candidate",
        prompt_content="Candidate prompt",
        model_revision="model-r1",
        passed=True,
        elapsed_seconds=4.0,
        created_at="2026-08-30T00:00:01+00:00",
    )
    provenance_path = (
        orchestrator._run_store.state_root
        / "candidate"
        / "chat_memory_eval_20260830_provenance.json"
    )
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    payload["prompt"]["content"] = "Tampered"
    provenance_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ChatMemoryEvaluationArtifactUnavailable, match="do not match"):
        orchestrator.get_chat_memory_evaluation("candidate")


def test_reader_rejects_v2_summary_rehomed_to_another_run(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path)
    _create_run(
        orchestrator,
        run_id="candidate",
        prompt_content="Candidate prompt",
        model_revision="model-r1",
        passed=True,
        elapsed_seconds=4.0,
        created_at="2026-08-30T00:00:01+00:00",
    )
    summary_path = (
        orchestrator._run_store.state_root
        / "candidate"
        / "chat_memory_eval_20260830_summary.json"
    )
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    payload["run_id"] = "another-run"
    summary_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ChatMemoryEvaluationArtifactUnavailable,
        match="summary does not match its Test Center run",
    ):
        orchestrator.get_chat_memory_evaluation("candidate")


def test_reader_rejects_round_outcome_that_disagrees_with_deterministic_score(
    tmp_path: Path,
) -> None:
    orchestrator = _orchestrator(tmp_path)
    _create_run(
        orchestrator,
        run_id="candidate",
        prompt_content="Candidate prompt",
        model_revision="model-r1",
        passed=True,
        elapsed_seconds=4.0,
        created_at="2026-08-30T00:00:01+00:00",
    )
    jsonl_path = (
        orchestrator._run_store.state_root
        / "candidate"
        / "chat_memory_eval_20260830.jsonl"
    )
    payload = json.loads(jsonl_path.read_text(encoding="utf-8"))
    payload["pass"] = False
    jsonl_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(
        ChatMemoryEvaluationArtifactUnavailable,
        match="do not match deterministic evidence",
    ):
        orchestrator.get_chat_memory_evaluation("candidate")


def test_reader_recomputes_score_instead_of_trusting_self_consistent_claims(
    tmp_path: Path,
) -> None:
    orchestrator = _orchestrator(tmp_path)
    _create_run(
        orchestrator,
        run_id="candidate",
        prompt_content="Candidate prompt",
        model_revision="model-r1",
        passed=True,
        elapsed_seconds=4.0,
        created_at="2026-08-30T00:00:01+00:00",
    )
    jsonl_path = (
        orchestrator._run_store.state_root
        / "candidate"
        / "chat_memory_eval_20260830.jsonl"
    )
    payload = json.loads(jsonl_path.read_text(encoding="utf-8"))
    payload["pass"] = False
    payload["deterministic_score"] = {
        "pass": False,
        "forbidden_hits": [],
        "forbidden_hit_count": 0,
        "human_memory_changed": False,
        "expected_fact_scores": [
            {
                "key": "dog_name",
                "label": "Dog name",
                "passed": False,
                "matched_aliases": [],
                "aliases": ["Rocky"],
            }
        ],
        "expected_facts_passed": False,
        "missing_expected_facts": ["dog_name"],
    }
    jsonl_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(
        ChatMemoryEvaluationArtifactUnavailable,
        match="does not match its persisted evidence",
    ):
        orchestrator.get_chat_memory_evaluation("candidate")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("config", {"rounds": 99}, "summary config does not match provenance"),
        ("pass_rate", 0.5, "summary metrics do not match"),
    ],
)
def test_reader_rejects_summary_claims_not_derived_from_evidence(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    orchestrator = _orchestrator(tmp_path)
    _create_run(
        orchestrator,
        run_id="candidate",
        prompt_content="Candidate prompt",
        model_revision="model-r1",
        passed=True,
        elapsed_seconds=4.0,
        created_at="2026-08-30T00:00:01+00:00",
    )
    summary_path = (
        orchestrator._run_store.state_root
        / "candidate"
        / "chat_memory_eval_20260830_summary.json"
    )
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    if field == "config":
        assert isinstance(value, dict)
        payload["config"].update(value)
    else:
        payload[field] = value
    summary_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ChatMemoryEvaluationArtifactUnavailable, match=message):
        orchestrator.get_chat_memory_evaluation("candidate")


def test_comparison_reports_exact_content_identity_and_metric_deltas(
    tmp_path: Path,
) -> None:
    orchestrator = _orchestrator(tmp_path)
    _create_run(
        orchestrator,
        run_id="baseline",
        prompt_content="Baseline prompt",
        model_revision="model-r1",
        passed=False,
        elapsed_seconds=8.0,
        created_at="2026-08-30T00:00:01+00:00",
    )
    _create_run(
        orchestrator,
        run_id="candidate",
        prompt_content="Candidate prompt",
        model_revision="model-r2",
        passed=True,
        elapsed_seconds=5.0,
        created_at="2026-08-30T00:00:02+00:00",
    )

    comparison = orchestrator.compare_chat_memory_evaluations("baseline", "candidate")

    assert comparison is not None
    assert comparison["same_configuration"] is False
    assert comparison["configuration_changes"]["prompt_content"] == {
        "baseline": "Baseline prompt",
        "candidate": "Candidate prompt",
        "changed": True,
    }
    assert comparison["configuration_changes"]["model_deployment"]["changed"]
    assert comparison["configuration_changes"]["control.judge_model_key"] == {
        "baseline": "",
        "candidate": "",
        "changed": False,
    }
    assert comparison["metric_deltas"]["pass_rate"] == 1.0
    assert comparison["metric_deltas"]["average_elapsed_seconds"] == -3.0


def test_decisions_are_audited_and_promotion_sets_preferred_baseline(
    tmp_path: Path,
) -> None:
    orchestrator = _orchestrator(tmp_path)
    baseline_provenance = _create_run(
        orchestrator,
        run_id="baseline",
        prompt_content="Baseline prompt",
        model_revision="model-r1",
        passed=True,
        elapsed_seconds=8.0,
        created_at="2026-08-30T00:00:01+00:00",
    )
    provenance = _create_run(
        orchestrator,
        run_id="candidate",
        prompt_content="Candidate prompt",
        model_revision="model-r2",
        passed=True,
        elapsed_seconds=5.0,
        created_at="2026-08-30T00:00:02+00:00",
    )

    decision = orchestrator.record_chat_memory_evaluation_decision(
        "candidate",
        outcome="promote",
        baseline_run_id="baseline",
        expected_baseline_provenance_sha256=baseline_provenance["provenance_sha256"],
        expected_baseline_evidence_sha256=baseline_provenance["evidence_sha256"],
        expected_provenance_sha256=provenance["provenance_sha256"],
        expected_evidence_sha256=provenance["evidence_sha256"],
        note="Improved memory behavior.",
    )

    assert decision is not None
    assert decision["outcome"] == "promote"
    assert (
        decision["baseline_provenance_sha256"]
        == baseline_provenance["provenance_sha256"]
    )
    items = orchestrator.list_chat_memory_evaluations()
    candidate = next(item for item in items if item["run_id"] == "candidate")
    assert candidate["preferred_baseline"] is True
    assert candidate["decision"]["note"] == "Improved memory behavior."
    manifest = json.loads(
        (orchestrator._run_store.state_root / "candidate" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(manifest["evaluation_decisions"]) == 1


def test_decision_rejects_stale_or_failed_promotion(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path)
    provenance = _create_run(
        orchestrator,
        run_id="failed",
        prompt_content="Failed prompt",
        model_revision="model-r1",
        passed=False,
        elapsed_seconds=5.0,
        created_at="2026-08-30T00:00:01+00:00",
    )

    with pytest.raises(ChatMemoryEvaluationDecisionConflict, match="evidence changed"):
        orchestrator.record_chat_memory_evaluation_decision(
            "failed",
            outcome="reject",
            expected_provenance_sha256="0" * 64,
            expected_evidence_sha256=provenance["evidence_sha256"],
        )
    with pytest.raises(ChatMemoryEvaluationDecisionConflict, match="complete"):
        orchestrator.record_chat_memory_evaluation_decision(
            "failed",
            outcome="promote",
            expected_provenance_sha256=provenance["provenance_sha256"],
            expected_evidence_sha256=provenance["evidence_sha256"],
        )


def test_promotion_requires_the_orchestrator_to_finish_passed(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path)
    provenance = _create_run(
        orchestrator,
        run_id="candidate",
        prompt_content="Candidate prompt",
        model_revision="model-r1",
        passed=True,
        elapsed_seconds=3.0,
        created_at="2026-08-30T00:00:01+00:00",
    )
    with orchestrator._run_store.locked_run("candidate") as run:
        assert run is not None
        run["status"] = "failed"
        orchestrator._run_store.persist(run)

    with pytest.raises(ChatMemoryEvaluationDecisionConflict, match="complete"):
        orchestrator.record_chat_memory_evaluation_decision(
            "candidate",
            outcome="promote",
            expected_provenance_sha256=provenance["provenance_sha256"],
            expected_evidence_sha256=provenance["evidence_sha256"],
        )


def test_decision_rejects_stale_baseline_evidence(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path)
    baseline_provenance = _create_run(
        orchestrator,
        run_id="baseline",
        prompt_content="Baseline prompt",
        model_revision="model-r1",
        passed=True,
        elapsed_seconds=4.0,
        created_at="2026-08-30T00:00:01+00:00",
    )
    candidate_provenance = _create_run(
        orchestrator,
        run_id="candidate",
        prompt_content="Candidate prompt",
        model_revision="model-r2",
        passed=True,
        elapsed_seconds=3.0,
        created_at="2026-08-30T00:00:02+00:00",
    )

    with pytest.raises(ChatMemoryEvaluationDecisionConflict, match="Baseline evidence"):
        orchestrator.record_chat_memory_evaluation_decision(
            "candidate",
            outcome="keep",
            baseline_run_id="baseline",
            expected_baseline_provenance_sha256="0" * 64,
            expected_baseline_evidence_sha256=baseline_provenance["evidence_sha256"],
            expected_provenance_sha256=candidate_provenance["provenance_sha256"],
            expected_evidence_sha256=candidate_provenance["evidence_sha256"],
        )


def test_reader_hides_decision_that_no_longer_matches_provenance(
    tmp_path: Path,
) -> None:
    orchestrator = _orchestrator(tmp_path)
    provenance = _create_run(
        orchestrator,
        run_id="candidate",
        prompt_content="Candidate prompt",
        model_revision="model-r1",
        passed=True,
        elapsed_seconds=3.0,
        created_at="2026-08-30T00:00:01+00:00",
    )
    orchestrator.record_chat_memory_evaluation_decision(
        "candidate",
        outcome="keep",
        expected_provenance_sha256=provenance["provenance_sha256"],
        expected_evidence_sha256=provenance["evidence_sha256"],
    )
    with orchestrator._run_store.locked_run("candidate") as run:
        assert run is not None
        run["evaluation_decisions"][-1]["candidate_provenance_sha256"] = "0" * 64
        orchestrator._run_store.persist(run)

    items = orchestrator.list_chat_memory_evaluations()
    assert items[0]["ready"] is False
    with pytest.raises(
        ChatMemoryEvaluationArtifactUnavailable,
        match="decision does not match",
    ):
        orchestrator.get_chat_memory_evaluation("candidate")


def test_modified_output_invalidates_decision_and_preferred_baseline(
    tmp_path: Path,
) -> None:
    orchestrator = _orchestrator(tmp_path)
    provenance = _create_run(
        orchestrator,
        run_id="candidate",
        prompt_content="Candidate prompt",
        model_revision="model-r1",
        passed=True,
        elapsed_seconds=3.0,
        created_at="2026-08-30T00:00:01+00:00",
    )
    orchestrator.record_chat_memory_evaluation_decision(
        "candidate",
        outcome="promote",
        expected_provenance_sha256=provenance["provenance_sha256"],
        expected_evidence_sha256=provenance["evidence_sha256"],
    )
    jsonl_path = (
        orchestrator._run_store.state_root
        / "candidate"
        / "chat_memory_eval_20260830.jsonl"
    )
    payload = json.loads(jsonl_path.read_text(encoding="utf-8"))
    payload["elapsed_seconds"] = 99.0
    jsonl_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    items = orchestrator.list_chat_memory_evaluations()

    assert items[0]["ready"] is False
    assert items[0]["preferred_baseline"] is False
    with pytest.raises(
        ChatMemoryEvaluationArtifactUnavailable,
        match="decision does not match its evidence",
    ):
        orchestrator.get_chat_memory_evaluation("candidate")


def test_comparison_refuses_historical_runs_without_provenance(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path)
    _create_run(
        orchestrator,
        run_id="candidate",
        prompt_content="Candidate",
        model_revision="model-r1",
        passed=True,
        elapsed_seconds=1.0,
        created_at="2026-08-30T00:00:01+00:00",
    )
    candidate_dir = orchestrator._run_store.state_root / "candidate"
    summary_path = candidate_dir / "chat_memory_eval_20260830_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.pop("provenance")
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    detail = orchestrator.get_chat_memory_evaluation("candidate")
    assert detail is not None
    with pytest.raises(ChatMemoryEvaluationComparisonUnavailable):
        orchestrator.compare_chat_memory_evaluations("candidate", "candidate")


def test_evaluation_decision_api_maps_conflicts_to_409(monkeypatch) -> None:
    class _FakeOrchestrator:
        def record_chat_memory_evaluation_decision(self, _run_id: str, **_kwargs):
            raise ChatMemoryEvaluationDecisionConflict("stale evidence")

    monkeypatch.setattr(api, "ensure_ade_api_enabled", lambda: None)
    request = ChatMemoryEvaluationDecisionRequest(
        outcome="reject",
        expected_provenance_sha256="a" * 64,
        expected_evidence_sha256="b" * 64,
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            api.record_chat_memory_evaluation_decision(
                "candidate", request, _FakeOrchestrator()
            )
        )

    assert error.value.status_code == 409


def test_evaluation_comparison_api_rejects_same_run(monkeypatch) -> None:
    monkeypatch.setattr(api, "ensure_ade_api_enabled", lambda: None)

    with pytest.raises(HTTPException) as error:
        asyncio.run(api.compare_chat_memory_evaluations("same", "same", object()))

    assert error.value.status_code == 400
