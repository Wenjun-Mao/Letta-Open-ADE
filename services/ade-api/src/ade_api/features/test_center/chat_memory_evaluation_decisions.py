from __future__ import annotations

from typing import Any
from uuid import uuid4

from .contracts import ChatMemoryEvaluationDecisionResponse
from .run_store import RunRecord, TestRunStore, utc_now_iso


class ChatMemoryEvaluationDecisionConflict(RuntimeError):
    """Raised when a decision no longer matches verified evaluation evidence."""


def latest_evaluation_decision(
    run: RunRecord,
) -> ChatMemoryEvaluationDecisionResponse | None:
    raw_decisions = run.get("evaluation_decisions")
    if not isinstance(raw_decisions, list):
        return None
    for raw in reversed(raw_decisions):
        if not isinstance(raw, dict):
            continue
        try:
            return ChatMemoryEvaluationDecisionResponse.model_validate(raw)
        except ValueError:
            continue
    return None


def preferred_baseline_run_id(runs: list[RunRecord]) -> str | None:
    promoted: list[ChatMemoryEvaluationDecisionResponse] = []
    for run in runs:
        decision = latest_evaluation_decision(run)
        if decision is not None and decision.outcome == "promote":
            promoted.append(decision)
    if not promoted:
        return None
    promoted.sort(key=lambda item: (item.recorded_at, item.decision_id), reverse=True)
    return promoted[0].candidate_run_id


def append_evaluation_decision(
    *,
    run_store: TestRunStore,
    run_id: str,
    detail: dict[str, Any],
    outcome: str,
    expected_provenance_sha256: str,
    expected_evidence_sha256: str,
    baseline_run_id: str | None,
    baseline_provenance_sha256: str | None,
    baseline_evidence_sha256: str | None,
    note: str,
) -> dict[str, Any]:
    provenance = detail.get("provenance_detail")
    if not isinstance(provenance, dict):
        raise ChatMemoryEvaluationDecisionConflict(
            "This historical run has no verified provenance and cannot receive a decision"
        )
    if provenance.get("provenance_sha256") != expected_provenance_sha256:
        raise ChatMemoryEvaluationDecisionConflict(
            "Evaluation evidence changed after it was reviewed; refresh before deciding"
        )
    if detail.get("evidence_sha256") != expected_evidence_sha256:
        raise ChatMemoryEvaluationDecisionConflict(
            "Evaluation output evidence changed after it was reviewed; refresh before deciding"
        )
    if provenance.get("controls", {}).get("retry_count") != 0:
        raise ChatMemoryEvaluationDecisionConflict(
            "Evaluation decisions require retry_count=0 because Agent Studio messages "
            "have no server-owned idempotency contract"
        )
    if outcome == "promote" and not _is_complete_pass(detail):
        raise ChatMemoryEvaluationDecisionConflict(
            "Only a complete deterministic pass can become the preferred baseline"
        )

    decision = ChatMemoryEvaluationDecisionResponse(
        decision_id=str(uuid4()),
        outcome=outcome,
        candidate_run_id=run_id,
        baseline_run_id=baseline_run_id,
        baseline_provenance_sha256=baseline_provenance_sha256,
        baseline_evidence_sha256=baseline_evidence_sha256,
        candidate_provenance_sha256=expected_provenance_sha256,
        candidate_evidence_sha256=expected_evidence_sha256,
        candidate_configuration_sha256=str(provenance["configuration_sha256"]),
        note=note.strip(),
        recorded_at=utc_now_iso(),
    )
    with run_store.locked_run(run_id) as run:
        if run is None or run.get("run_type") != "chat_memory_eval":
            raise KeyError(run_id)
        history = run.get("evaluation_decisions")
        decisions = list(history) if isinstance(history, list) else []
        decisions.append(decision.model_dump())
        run["evaluation_decisions"] = decisions
        run_store.persist(run)
    return decision.model_dump()


def _is_complete_pass(detail: dict[str, Any]) -> bool:
    if detail.get("run_status") != "passed":
        return False
    metrics = detail.get("metrics")
    if not isinstance(metrics, dict):
        return False
    rounds_total = metrics.get("rounds_total")
    rounds = detail.get("rounds")
    return (
        type(rounds_total) is int
        and rounds_total > 0
        and metrics.get("rounds_passed") == rounds_total
        and metrics.get("rounds_failed") == 0
        and metrics.get("errors") == 0
        and isinstance(rounds, list)
        and len(rounds) == rounds_total
        and all(
            isinstance(round_, dict)
            and round_.get("passed") is True
            and isinstance(round_.get("deterministic_score"), dict)
            and round_["deterministic_score"].get("pass") is True
            for round_ in rounds
        )
    )
