from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import MemoryFact, RunEventType, RunStatus, TurnResult
from .fixtures import StudyCase


@dataclass(frozen=True)
class WeightedScore:
    candidate: str
    passed_mandatory_gates: bool
    dimensions: dict[str, float]
    weighted_total: float
    failed_gates: tuple[str, ...]


SCORE_WEIGHTS = {
    "comprehension_maintainability": 0.30,
    "explicit_control": 0.25,
    "observability": 0.15,
    "protocol_fidelity": 0.15,
    "dependency_security_burden": 0.10,
    "measured_overhead": 0.05,
}


def score_case(
    *,
    case: StudyCase,
    facts_by_subject: dict[str, tuple[MemoryFact, ...]],
    results_by_conversation: dict[str, tuple[TurnResult, ...]],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for assertion in case.fact_assertions:
        facts = facts_by_subject.get(assertion.subject_key, ())
        searchable = "\n".join(f"{fact.key}: {fact.value}" for fact in facts).casefold()
        aliases = tuple(
            alias for alias in assertion.aliases if alias.casefold() in searchable
        )
        key_matches = not assertion.key or any(
            fact.key.casefold() == assertion.key.casefold() for fact in facts
        )
        present = bool(aliases) and key_matches
        passed = not present if assertion.absent else present
        checks.append(
            {
                "kind": "fact_absent" if assertion.absent else "fact_present",
                "subject_key": assertion.subject_key,
                "key": assertion.key,
                "aliases": list(assertion.aliases),
                "matched_aliases": list(aliases),
                "pass": passed,
            }
        )

    for assertion in case.assistant_assertions:
        results = results_by_conversation.get(assertion.conversation_key, ())
        text = "\n".join(
            result.assistant_message.content
            for result in results
            if result.assistant_message is not None
        ).casefold()
        contains = [item for item in assertion.contains_any if item.casefold() in text]
        forbidden = [item for item in assertion.forbidden if item.casefold() in text]
        checks.append(
            {
                "kind": "assistant_content",
                "conversation_key": assertion.conversation_key,
                "contains_any": list(assertion.contains_any),
                "matched_contains": contains,
                "forbidden_hits": forbidden,
                "pass": (not assertion.contains_any or bool(contains))
                and not forbidden,
            }
        )

    all_results = tuple(
        result for values in results_by_conversation.values() for result in values
    )
    used_tools = {
        execution.name for result in all_results for execution in result.tool_executions
    }
    for tool_name in case.required_tools:
        checks.append(
            {
                "kind": "required_tool",
                "tool_name": tool_name,
                "pass": tool_name in used_tools,
            }
        )
    if case.require_failed_tool_result:
        has_failed_tool = any(
            not execution.succeeded
            for result in all_results
            for execution in result.tool_executions
        )
        checks.append({"kind": "failed_tool_was_observed", "pass": has_failed_tool})

    all_succeeded = all(
        result.run.status is RunStatus.SUCCEEDED for result in all_results
    )
    trace_preserved = all(
        any(event.type is RunEventType.MODEL_REQUEST for event in result.events)
        and any(event.type is RunEventType.MODEL_RESPONSE for event in result.events)
        for result in all_results
    )
    checks.extend(
        (
            {"kind": "all_runs_succeeded", "pass": all_succeeded},
            {"kind": "normalized_trace_preserved", "pass": trace_preserved},
        )
    )
    failed = [check for check in checks if not check["pass"]]
    return {
        "case_key": case.key,
        "pass": not failed,
        "checks": checks,
        "failed_checks": failed,
        "turn_count": len(all_results),
        "used_tools": sorted(used_tools),
        "latency_seconds": round(
            sum(result.elapsed_seconds for result in all_results), 6
        ),
        "input_tokens": sum(
            int(result.usage.get("input_tokens", result.usage.get("prompt_tokens", 0)))
            for result in all_results
        ),
        "output_tokens": sum(
            int(
                result.usage.get(
                    "output_tokens", result.usage.get("completion_tokens", 0)
                )
            )
            for result in all_results
        ),
    }


def weighted_candidate_score(
    *,
    candidate: str,
    dimensions: dict[str, float],
    mandatory_gates: dict[str, bool],
) -> WeightedScore:
    missing = sorted(set(SCORE_WEIGHTS) - set(dimensions))
    if missing:
        raise ValueError(f"Missing score dimensions: {missing}")
    normalized = {
        key: max(0.0, min(100.0, float(value)))
        for key, value in dimensions.items()
        if key in SCORE_WEIGHTS
    }
    total = sum(normalized[key] * SCORE_WEIGHTS[key] for key in SCORE_WEIGHTS)
    failed_gates = tuple(key for key, passed in mandatory_gates.items() if not passed)
    return WeightedScore(
        candidate=candidate,
        passed_mandatory_gates=not failed_gates,
        dimensions=normalized,
        weighted_total=round(total, 3),
        failed_gates=failed_gates,
    )
