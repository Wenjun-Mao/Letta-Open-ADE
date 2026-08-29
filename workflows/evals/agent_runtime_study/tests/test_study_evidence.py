from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from workflows.evals.agent_runtime_study.config import load_config
from workflows.evals.agent_runtime_study.deployment_qualification import (
    DeploymentLifecycle,
    DeploymentRole,
    load_deployments,
    replace_fingerprint,
)
from workflows.evals.agent_runtime_study.study_evidence import (
    build_qualification_evidence,
    run_semantic_retrieval_evaluation,
)


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = WORKFLOW_ROOT / "config.toml"
REGISTRY_PATH = WORKFLOW_ROOT / "deployments.toml"


class KeywordEmbeddings:
    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._vector(text) for text in texts)

    @staticmethod
    def _vector(text: str) -> tuple[float, ...]:
        normalized = text.casefold()
        if any(term in normalized for term in ("museum", "博物馆", "安大略")):
            return (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        if any(
            term in normalized
            for term in ("toronto", "city", "residence", "live", "多伦多", "城市", "住")
        ):
            return (0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        if any(term in normalized for term in ("concert", "massey", "jazz")):
            return (0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        if any(term in normalized for term in ("rocky", "husky", "哈士奇", "狗")):
            return (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0)
        if any(
            term in normalized for term in ("language", "mandarin", "语言", "普通话")
        ):
            return (0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
        if any(term in normalized for term in ("shoe", "eu 38", "38码")):
            return (0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        if any(term in normalized for term in ("sister", "mei", "小美")):
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        if "blue-orchid" in normalized:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


class StepClock:
    def __init__(self, step: float = 0.001) -> None:
        self.value = 0.0
        self.step = step

    def __call__(self) -> float:
        current = self.value
        self.value += self.step
        return current


def _passing_rows() -> list[dict[str, object]]:
    return [
        {
            "model_key": model,
            "adapter": "custom_loop",
            "case_key": "required-case",
            "score": {"pass": True},
            "role_scores": {
                "conversation": {"observed": True, "pass": True},
                "reviewer": {"observed": True, "pass": True},
            },
        }
        for model in (
            "dgx_vllm::qwen3.6-35b-a3b-fp8",
            "local_llama_server::gemma4",
        )
    ]


def _write_qualification_round(
    output_dir: Path, run_id: str, evidence: dict[str, object]
) -> None:
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "qualification.json").write_text(
        json.dumps(evidence),
        encoding="utf-8",
    )


def test_semantic_retrieval_evidence_applies_all_acceptance_gates() -> None:
    config = load_config(CONFIG_PATH)

    evidence = run_semantic_retrieval_evaluation(
        config,
        embeddings=KeywordEmbeddings(),
        clock=StepClock(),
    )

    assert evidence["corpus_size"] == 1000
    assert evidence["acceptance"]["pass"] is True
    assert all(evidence["acceptance"]["checks"].values())
    assert evidence["metrics"]["evaluated_case_count"] == 12


def test_qualification_aggregator_requires_three_rounds_per_exact_role(
    tmp_path: Path,
) -> None:
    evidence: dict[str, object] = {}
    for sequence in range(1, 4):
        run_id = f"run-{sequence}"
        evidence = build_qualification_evidence(
            run_id=run_id,
            registry_path=REGISTRY_PATH,
            output_dir=tmp_path,
            models=(
                "dgx_vllm::qwen3.6-35b-a3b-fp8",
                "local_llama_server::gemma4",
            ),
            reviewer_model_key="dgx_vllm::qwen3.6-35b-a3b-fp8",
            rows=_passing_rows(),
            retrieval_evidence={"acceptance": {"pass": True}},
            required_case_keys=("required-case",),
            qualification_adapter="custom_loop",
            allow_unqualified_study_models=True,
        )
        if sequence < 3:
            assert evidence["all_qualified"] is False
            _write_qualification_round(tmp_path, run_id, evidence)

    assert evidence["all_qualified"] is True
    assert evidence["study_gate_pass"] is True
    current_rounds = evidence["current_rounds"]
    assert len(current_rounds) == 4
    assert {item["sequence"] for item in current_rounds} == {3}
    lifecycle_by_id = {
        item["deployment"]["deployment_id"]: item["deployment"]["lifecycle"]
        for item in evidence["assessments"]
    }
    assert lifecycle_by_id == {
        "dgx-qwen3-embedding-0_6b": DeploymentLifecycle.QUALIFIED.value,
        "dgx-qwen3_6-chat": DeploymentLifecycle.QUALIFIED.value,
        # The binary digest is not observable from llama-server's API.
        "llama-server-qwen3_5-27b": DeploymentLifecycle.CANDIDATE.value,
    }


def test_study_override_is_explicit_and_never_applies_to_production(
    tmp_path: Path,
) -> None:
    evidence = build_qualification_evidence(
        run_id="strict-study",
        registry_path=REGISTRY_PATH,
        output_dir=tmp_path,
        models=("dgx_vllm::qwen3.6-35b-a3b-fp8",),
        reviewer_model_key="dgx_vllm::qwen3.6-35b-a3b-fp8",
        rows=_passing_rows()[:1],
        retrieval_evidence={"acceptance": {"pass": True}},
        required_case_keys=("required-case",),
        qualification_adapter="custom_loop",
        allow_unqualified_study_models=False,
    )

    assert evidence["all_qualified"] is False
    assert evidence["study_gate_pass"] is False
    assert not any(
        item["decision"]["override_used"]
        for item in evidence["study_release_decisions"]
    )


def test_changed_fingerprint_cannot_inherit_aggregated_rounds(tmp_path: Path) -> None:
    deployments = load_deployments(REGISTRY_PATH)
    initial = build_qualification_evidence(
        run_id="before-change",
        registry_path=REGISTRY_PATH,
        output_dir=tmp_path,
        models=("dgx_vllm::qwen3.6-35b-a3b-fp8",),
        reviewer_model_key="dgx_vllm::qwen3.6-35b-a3b-fp8",
        rows=_passing_rows()[:1],
        retrieval_evidence={"acceptance": {"pass": True}},
        required_case_keys=("required-case",),
        qualification_adapter="custom_loop",
        allow_unqualified_study_models=True,
        deployments=deployments,
    )
    _write_qualification_round(tmp_path, "before-change", initial)
    changed = tuple(
        replace_fingerprint(
            deployment,
            replace(deployment.fingerprint, runtime_version="changed-runtime"),
        )
        if deployment.deployment_id == "dgx-qwen3_6-chat"
        else deployment
        for deployment in deployments
    )

    after = build_qualification_evidence(
        run_id="after-change",
        registry_path=REGISTRY_PATH,
        output_dir=tmp_path,
        models=("dgx_vllm::qwen3.6-35b-a3b-fp8",),
        reviewer_model_key="dgx_vllm::qwen3.6-35b-a3b-fp8",
        rows=_passing_rows()[:1],
        retrieval_evidence={"acceptance": {"pass": True}},
        required_case_keys=("required-case",),
        qualification_adapter="custom_loop",
        allow_unqualified_study_models=True,
        deployments=changed,
    )

    chat_rounds = [
        item
        for item in after["current_rounds"]
        if item["deployment_id"] == "dgx-qwen3_6-chat"
    ]
    assert {item["role"] for item in chat_rounds} == {
        DeploymentRole.CONVERSATION.value,
        DeploymentRole.REVIEWER.value,
    }
    assert {item["sequence"] for item in chat_rounds} == {1}
    chat_assessment = next(
        item
        for item in after["assessments"]
        if item["deployment"]["deployment_id"] == "dgx-qwen3_6-chat"
    )
    assert chat_assessment["assessment"]["stale_round_count"] == 2


def test_partial_diagnostic_does_not_change_chat_or_reviewer_streaks(
    tmp_path: Path,
) -> None:
    evidence = build_qualification_evidence(
        run_id="partial",
        registry_path=REGISTRY_PATH,
        output_dir=tmp_path,
        models=("dgx_vllm::qwen3.6-35b-a3b-fp8",),
        reviewer_model_key="dgx_vllm::qwen3.6-35b-a3b-fp8",
        rows=_passing_rows()[:1],
        retrieval_evidence={"acceptance": {"pass": True}},
        required_case_keys=("required-case", "missing-case"),
        qualification_adapter="custom_loop",
        allow_unqualified_study_models=True,
    )

    assert {
        (item["deployment_id"], item["role"]) for item in evidence["current_rounds"]
    } == {("dgx-qwen3-embedding-0_6b", DeploymentRole.RETRIEVER.value)}
    assert all(coverage["complete"] is False for coverage in evidence["role_coverage"])


def test_qualification_attributes_failures_to_the_observed_role_only(
    tmp_path: Path,
) -> None:
    rows = [
        {
            "model_key": "dgx_vllm::qwen3.6-35b-a3b-fp8",
            "adapter": "custom_loop",
            "case_key": "required-case",
            "score": {"pass": False},
            "role_scores": {
                "conversation": {"observed": True, "pass": False},
                "reviewer": {"observed": True, "pass": True},
            },
        }
    ]

    evidence = build_qualification_evidence(
        run_id="role-specific",
        registry_path=REGISTRY_PATH,
        output_dir=tmp_path,
        models=("dgx_vllm::qwen3.6-35b-a3b-fp8",),
        reviewer_model_key="dgx_vllm::qwen3.6-35b-a3b-fp8",
        rows=rows,
        retrieval_evidence={"acceptance": {"pass": True}},
        required_case_keys=("required-case",),
        qualification_adapter="custom_loop",
        allow_unqualified_study_models=True,
    )

    rounds = {item["role"]: item["passed"] for item in evidence["current_rounds"]}
    assert rounds[DeploymentRole.CONVERSATION.value] is False
    assert rounds[DeploymentRole.REVIEWER.value] is True


def test_unobserved_role_does_not_create_a_qualification_round(tmp_path: Path) -> None:
    rows = [
        {
            "model_key": "dgx_vllm::qwen3.6-35b-a3b-fp8",
            "adapter": "custom_loop",
            "case_key": "required-case",
            "score": {"pass": False},
            "role_scores": {
                "conversation": {"observed": True, "pass": False},
                "reviewer": {"observed": False, "pass": None},
            },
        }
    ]

    evidence = build_qualification_evidence(
        run_id="unobserved-reviewer",
        registry_path=REGISTRY_PATH,
        output_dir=tmp_path,
        models=("dgx_vllm::qwen3.6-35b-a3b-fp8",),
        reviewer_model_key="dgx_vllm::qwen3.6-35b-a3b-fp8",
        rows=rows,
        retrieval_evidence={"acceptance": {"pass": True}},
        required_case_keys=("required-case",),
        qualification_adapter="custom_loop",
        allow_unqualified_study_models=True,
    )

    roles = {item["role"] for item in evidence["current_rounds"]}
    assert DeploymentRole.CONVERSATION.value in roles
    assert DeploymentRole.REVIEWER.value not in roles
    reviewer_coverage = next(
        item
        for item in evidence["role_coverage"]
        if item["role"] == DeploymentRole.REVIEWER.value
    )
    assert reviewer_coverage["complete"] is False
