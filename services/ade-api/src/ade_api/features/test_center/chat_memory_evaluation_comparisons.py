from __future__ import annotations

from typing import Any

from .contracts import ChatMemoryEvaluationComparisonResponse


class ChatMemoryEvaluationComparisonUnavailable(RuntimeError):
    """Raised when historical artifacts cannot support a trustworthy comparison."""


_CONFIG_FIELDS = (
    "model",
    "prompt_key",
    "persona_key",
    "embedding",
    "fixture_key",
    "rounds",
    "timeout_seconds",
    "retry_count",
    "judge_enabled",
)

_IDENTITY_FIELDS = (
    "model_identity_sha256",
    "embedding_identity_sha256",
    "prompt_content_sha256",
    "persona_content_sha256",
    "fixture_sha256",
)

_METRIC_FIELDS = (
    "pass_rate",
    "average_elapsed_seconds",
    "forbidden_hit_count",
    "memory_changed_rounds",
    "expected_facts_passed_rounds",
    "memory_tool_call_count",
    "total_tool_call_count",
    "cleanup_passed_rounds",
)


def build_chat_memory_evaluation_comparison(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    baseline_provenance = baseline.get("provenance")
    candidate_provenance = candidate.get("provenance")
    baseline_detail = baseline.get("provenance_detail")
    candidate_detail = candidate.get("provenance_detail")
    if (
        not isinstance(baseline_provenance, dict)
        or not isinstance(candidate_provenance, dict)
        or not isinstance(baseline_detail, dict)
        or not isinstance(candidate_detail, dict)
    ):
        raise ChatMemoryEvaluationComparisonUnavailable(
            "Both runs need verified provenance before they can be compared"
        )

    changes: dict[str, dict[str, Any]] = {}
    for field in _CONFIG_FIELDS:
        changes[field] = _comparison_value(
            baseline["config"].get(field), candidate["config"].get(field)
        )
    for field in _IDENTITY_FIELDS:
        changes[field] = _comparison_value(
            baseline_provenance.get(field), candidate_provenance.get(field)
        )
    baseline_controls = baseline_detail.get("controls", {})
    candidate_controls = candidate_detail.get("controls", {})
    if not isinstance(baseline_controls, dict) or not isinstance(
        candidate_controls, dict
    ):
        raise ChatMemoryEvaluationComparisonUnavailable(
            "Both runs need valid effective controls before they can be compared"
        )
    for field in sorted(baseline_controls.keys() | candidate_controls.keys()):
        changes[f"control.{field}"] = _comparison_value(
            baseline_controls.get(field), candidate_controls.get(field)
        )
    changes["prompt_content"] = _comparison_value(
        baseline_detail["prompt"]["content"],
        candidate_detail["prompt"]["content"],
    )
    changes["persona_content"] = _comparison_value(
        baseline_detail["persona"]["content"],
        candidate_detail["persona"]["content"],
    )
    changes["model_deployment"] = _comparison_value(
        baseline_detail["model"].get("deployment"),
        candidate_detail["model"].get("deployment"),
    )

    baseline_metrics = baseline.get("metrics") or {}
    candidate_metrics = candidate.get("metrics") or {}
    metric_deltas = {
        field: _numeric(candidate_metrics.get(field))
        - _numeric(baseline_metrics.get(field))
        for field in _METRIC_FIELDS
    }
    response = ChatMemoryEvaluationComparisonResponse(
        baseline=_list_item(baseline),
        candidate=_list_item(candidate),
        same_configuration=(
            baseline_provenance["configuration_sha256"]
            == candidate_provenance["configuration_sha256"]
        ),
        configuration_changes=changes,
        metric_deltas=metric_deltas,
    )
    return response.model_dump()


def _list_item(detail: dict[str, Any]) -> dict[str, Any]:
    return {
        key: detail[key]
        for key in (
            "run_id",
            "run_status",
            "created_at",
            "finished_at",
            "ready",
            "config",
            "metrics",
            "provenance",
            "decision",
            "preferred_baseline",
        )
    }


def _comparison_value(baseline: Any, candidate: Any) -> dict[str, Any]:
    return {
        "baseline": baseline,
        "candidate": candidate,
        "changed": baseline != candidate,
    }


def _numeric(value: object) -> float:
    if type(value) in {int, float}:
        return float(value)
    return 0.0
