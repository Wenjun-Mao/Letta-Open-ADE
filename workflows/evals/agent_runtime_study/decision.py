from __future__ import annotations

import ast
import importlib.metadata
import statistics
from pathlib import Path
from typing import Any

from agent_runtime_eval_contracts import weighted_candidate_score

from .contract_benchmarks import run_contract_benchmarks
from .scripted import ScriptStep, SharedScript, scripted_adapter
from .contracts import (
    AgentDefinition,
    Conversation,
    MemorySubject,
    RuntimePolicy,
    TurnRequest,
)
from .repository import InMemoryStudyRepository
from .runtime import StudyAgentRuntime


def source_metrics(workflow_root: Path) -> dict[str, dict[str, Any]]:
    candidates = {
        "custom_loop": (
            workflow_root / "adapters" / "custom_loop.py",
            workflow_root / "adapters" / "transport.py",
        ),
        "pydantic_ai": (workflow_root / "adapters" / "pydantic_ai_adapter.py",),
    }
    result: dict[str, dict[str, Any]] = {}
    for candidate, paths in candidates.items():
        logical_lines = 0
        branch_nodes = 0
        for path in paths:
            source = path.read_text(encoding="utf-8")
            logical_lines += sum(
                1
                for line in source.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            )
            tree = ast.parse(source)
            branch_nodes += sum(
                isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.Match))
                for node in ast.walk(tree)
            )
        result[candidate] = {
            "files": [str(path.relative_to(workflow_root)) for path in paths],
            "logical_lines": logical_lines,
            "branch_nodes": branch_nodes,
        }
    return result


def dependency_metrics() -> dict[str, dict[str, Any]]:
    closure = _distribution_closure("pydantic-ai-slim", enabled_extra="openai")
    existing_runtime = set().union(
        *(
            _distribution_closure(name)
            for name in (
                "fastapi",
                "httpx",
                "letta-client",
                "pydantic-settings",
                "python-dotenv",
                "tenacity",
                "uvicorn",
            )
        )
    )
    incremental = closure - existing_runtime
    return {
        "custom_loop": {
            "incremental_distributions": [],
            "incremental_distribution_count": 0,
            "note": "Uses the workflow's existing httpx dependency.",
        },
        "pydantic_ai": {
            "dependency_closure": sorted(closure),
            "incremental_distributions": sorted(incremental),
            "incremental_distribution_count": len(incremental),
            "note": (
                "Official slim OpenAI extra, compared with the current ADE API "
                "runtime dependency closure."
            ),
        },
    }


def _distribution_closure(name: str, *, enabled_extra: str = "") -> set[str]:
    discovered: set[str] = set()
    pending: list[tuple[str, str]] = [(name, enabled_extra)]
    while pending:
        current, extra = pending.pop()
        normalized = current.casefold().replace("_", "-")
        if normalized in discovered:
            continue
        try:
            distribution = importlib.metadata.distribution(current)
        except importlib.metadata.PackageNotFoundError:
            continue
        discovered.add(normalized)
        for requirement in distribution.requires or ():
            if "extra ==" in requirement and (not extra or extra not in requirement):
                continue
            dependency = requirement.split(";", 1)[0].strip()
            dependency = dependency.split("[", 1)[0]
            for marker in (" ", "<", ">", "=", "!", "~"):
                dependency = dependency.split(marker, 1)[0]
            if dependency:
                pending.append((dependency, ""))
    return discovered


async def overhead_metrics(
    adapter_names: tuple[str, ...], *, iterations: int = 20
) -> dict[str, dict[str, float]]:
    measurements: dict[str, list[float]] = {name: [] for name in adapter_names}
    for adapter_name in adapter_names:
        for index in range(iterations):
            script = SharedScript((ScriptStep(text="ok"),))
            repository = InMemoryStudyRepository()
            repository.add_agent_definition(
                AgentDefinition(
                    id="agent",
                    name="agent",
                    model_key="scripted",
                    system_prompt="system",
                    persona="persona",
                    tool_names=(),
                )
            )
            repository.add_subject(MemorySubject(id="subject", external_key="subject"))
            repository.add_conversation(
                Conversation(
                    id="conversation",
                    agent_definition_id="agent",
                    memory_subject_id="subject",
                )
            )
            runtime = StudyAgentRuntime(
                repository=repository,
                executor=scripted_adapter(adapter_name, script),
            )
            result = await runtime.run_turn(
                TurnRequest(
                    conversation_id="conversation",
                    user_content="hello",
                    idempotency_key=f"overhead-{index}",
                    policy=RuntimePolicy(timeout_seconds=2.0),
                )
            )
            measurements[adapter_name].append(result.elapsed_seconds * 1000)
    return {
        name: {
            "median_ms": round(statistics.median(values), 6),
            "p95_ms": round(sorted(values)[max(0, int(len(values) * 0.95) - 1)], 6),
        }
        for name, values in measurements.items()
    }


async def build_candidate_decision_evidence(
    workflow_root: Path,
    adapter_names: tuple[str, ...] = ("custom_loop", "pydantic_ai"),
) -> dict[str, Any]:
    contracts = await run_contract_benchmarks(adapter_names)
    sources = source_metrics(workflow_root)
    dependencies = dependency_metrics()
    overhead = await overhead_metrics(adapter_names)
    fastest = min(item["median_ms"] for item in overhead.values()) or 0.001
    scorecards = {}
    for name in adapter_names:
        checks = contracts[name]["checks"]
        explicit_names = {
            "one_additional_retry_is_exact",
            "zero_retry_is_exact",
            "nontransient_error_is_not_retried",
            "whole_attempt_timeout_is_exact",
            "cancellation_has_no_partial_assistant_or_memory_commit",
            "idempotency_replays_terminal_result",
        }
        explicit = [check for check in checks if check["name"] in explicit_names]
        protocol = [
            check
            for check in checks
            if check["name"]
            in {
                "normal_reply_and_reasoning",
                "reasoning_only_completion_recovers",
                "multiple_tool_steps",
                "malformed_arguments_recover",
                "tool_failure_is_returned_and_traced",
            }
        ]
        source = sources[name]
        maintainability = max(
            0.0,
            100.0
            - min(45.0, source["logical_lines"] / 8)
            - min(20.0, source["branch_nodes"]),
        )
        dependency_score = max(
            0.0,
            100.0 - dependencies[name]["incremental_distribution_count"] * 2.0,
        )
        dimensions = {
            "comprehension_maintainability": maintainability,
            "explicit_control": _pass_percent(explicit),
            "observability": _trace_percent(checks),
            "protocol_fidelity": _pass_percent(protocol),
            "dependency_security_burden": dependency_score,
            "measured_overhead": min(
                100.0, 100.0 * fastest / max(overhead[name]["median_ms"], 0.001)
            ),
        }
        mandatory = {
            "normal_reply": _named_pass(checks, "normal_reply_and_reasoning"),
            "reasoning_only_recovery": _named_pass(
                checks, "reasoning_only_completion_recovers"
            ),
            "multiple_tools": _named_pass(checks, "multiple_tool_steps"),
            "malformed_arguments": _named_pass(checks, "malformed_arguments_recover"),
            "exact_retry_timeout": all(check["pass"] for check in explicit),
            "tool_failure": _named_pass(checks, "tool_failure_is_returned_and_traced"),
            "trace_preservation": _trace_percent(checks) == 100.0,
        }
        scorecards[name] = weighted_candidate_score(
            candidate=name,
            dimensions=dimensions,
            mandatory_gates=mandatory,
        )
    passing = [score for score in scorecards.values() if score.passed_mandatory_gates]
    selected = (
        max(
            passing,
            key=lambda item: (
                item.weighted_total,
                -sources[item.candidate]["logical_lines"],
            ),
        ).candidate
        if passing
        else None
    )
    return {
        "contracts": contracts,
        "source_metrics": sources,
        "dependency_metrics": dependencies,
        "overhead_metrics": overhead,
        "scorecards": scorecards,
        "selected_candidate": selected,
        "qualification_scope": "deterministic_contracts_only",
        "production_qualified": False,
        "selection_rule": (
            "Eliminate mandatory-gate failures, then choose the highest weighted "
            "score; exact ties favor fewer ADE-owned protocol lines."
        ),
    }


def _pass_percent(checks: list[dict[str, Any]]) -> float:
    return 100.0 * sum(bool(check["pass"]) for check in checks) / max(1, len(checks))


def _trace_percent(checks: list[dict[str, Any]]) -> float:
    relevant = [
        check
        for check in checks
        if check["run_status"] == "succeeded"
        and check["name"] != "idempotency_replays_terminal_result"
    ]
    return (
        100.0
        * sum(
            "model.request" in check["event_types"]
            and "model.response" in check["event_types"]
            and check["tool_trace_correlated"]
            for check in relevant
        )
        / max(1, len(relevant))
    )


def _named_pass(checks: list[dict[str, Any]], name: str) -> bool:
    return next(bool(check["pass"]) for check in checks if check["name"] == name)
