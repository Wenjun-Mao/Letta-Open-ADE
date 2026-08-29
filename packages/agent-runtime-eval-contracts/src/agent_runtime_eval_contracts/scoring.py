from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .fixtures import StudyCase
from .observations import FactObservation, TurnObservation


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

PRIVATE_REASONING_MARKERS = (
    "<think>",
    "</think>",
    "thinking process:",
    "internal monologue:",
    "思考过程:",
    "思考过程：",
)


def visible_private_reasoning_markers(text: str) -> tuple[str, ...]:
    normalized = str(text or "").casefold()
    return tuple(marker for marker in PRIVATE_REASONING_MARKERS if marker in normalized)


def score_case(
    *,
    case: StudyCase,
    facts_by_subject: Mapping[str, Sequence[FactObservation]],
    results_by_conversation: Mapping[str, Sequence[TurnObservation]],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    reviewer_checks: list[dict[str, Any]] = []
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
        check = {
            "kind": "fact_absent" if assertion.absent else "fact_present",
            "subject_key": assertion.subject_key,
            "key": assertion.key,
            "aliases": list(assertion.aliases),
            "matched_aliases": list(aliases),
            "pass": passed,
        }
        checks.append(check)
        reviewer_checks.append(check)

    conversation_checks: list[dict[str, Any]] = []
    for assertion in case.assistant_assertions:
        results = results_by_conversation.get(assertion.conversation_key, ())
        committed_text = "\n".join(
            result.assistant_text or "" for result in results if result.assistant_text
        )
        candidate_text = "\n".join(
            result.candidate_assistant_text or result.assistant_text or ""
            for result in results
            if result.candidate_assistant_text or result.assistant_text
        )
        checks.append(
            _assistant_content_check(
                assertion.conversation_key,
                assertion.contains_any,
                assertion.forbidden,
                committed_text,
            )
        )
        conversation_checks.append(
            _assistant_content_check(
                assertion.conversation_key,
                assertion.contains_any,
                assertion.forbidden,
                candidate_text,
            )
        )

    all_results = tuple(
        result for values in results_by_conversation.values() for result in values
    )
    assistant_text = "\n".join(
        result.assistant_text or "" for result in all_results if result.assistant_text
    )
    reasoning_markers = visible_private_reasoning_markers(assistant_text)
    checks.append(_private_reasoning_check(reasoning_markers))
    candidate_text = "\n".join(
        result.candidate_assistant_text or result.assistant_text or ""
        for result in all_results
        if result.candidate_assistant_text or result.assistant_text
    )
    conversation_checks.append(
        _private_reasoning_check(visible_private_reasoning_markers(candidate_text))
    )
    used_tools = {
        execution.name for result in all_results for execution in result.tools
    }
    for tool_name in case.required_tools:
        check = {
            "kind": "required_tool",
            "tool_name": tool_name,
            "pass": tool_name in used_tools,
        }
        checks.append(check)
        conversation_checks.append(check)
    if case.require_failed_tool_result:
        has_failed_tool = any(
            not execution.succeeded
            for result in all_results
            for execution in result.tools
        )
        check = {"kind": "failed_tool_was_observed", "pass": has_failed_tool}
        checks.append(check)
        conversation_checks.append(check)

    all_succeeded = all(result.status == "succeeded" for result in all_results)
    trace_preserved = all(
        any(event.type == "model.request" for event in result.events)
        and any(event.type == "model.response" for event in result.events)
        for result in all_results
    )
    checks.extend(
        (
            {"kind": "all_runs_succeeded", "pass": all_succeeded},
            {"kind": "normalized_trace_preserved", "pass": trace_preserved},
        )
    )
    conversation_checks.append(
        {"kind": "normalized_trace_preserved", "pass": trace_preserved}
    )
    reviewer_checks.append({"kind": "reviewed_turns_committed", "pass": all_succeeded})
    conversation_observed = len(all_results) == len(case.turns) and all(
        result.candidate_assistant_text is not None or result.assistant_text is not None
        for result in all_results
    )
    reviewer_observed = len(all_results) == len(case.turns) and all(
        any(event.type == "memory.review.request" for event in result.events)
        for result in all_results
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
        "role_scores": {
            "conversation": _role_score(conversation_observed, conversation_checks),
            "reviewer": _role_score(reviewer_observed, reviewer_checks),
        },
    }


def _assistant_content_check(
    conversation_key: str,
    contains_any: tuple[str, ...],
    forbidden: tuple[str, ...],
    text: str,
) -> dict[str, Any]:
    normalized = text.casefold()
    contains = [item for item in contains_any if item.casefold() in normalized]
    forbidden_hits = [item for item in forbidden if item.casefold() in normalized]
    return {
        "kind": "assistant_content",
        "conversation_key": conversation_key,
        "contains_any": list(contains_any),
        "matched_contains": contains,
        "forbidden_hits": forbidden_hits,
        "pass": (not contains_any or bool(contains)) and not forbidden_hits,
    }


def _private_reasoning_check(markers: tuple[str, ...]) -> dict[str, Any]:
    return {
        "kind": "private_reasoning_not_exposed",
        "visible_markers": list(markers),
        "pass": not markers,
    }


def _role_score(observed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check for check in checks if not check["pass"]]
    return {
        "observed": observed,
        "pass": not failed if observed else None,
        "checks": checks,
        "failed_checks": failed,
    }


def weighted_candidate_score(
    *,
    candidate: str,
    dimensions: Mapping[str, float],
    mandatory_gates: Mapping[str, bool],
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
