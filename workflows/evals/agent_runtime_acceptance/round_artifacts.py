"""Materialize acceptance rounds without widening the execution contract."""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any

from .artifacts import RoundArtifactWriter
from .chronology import case_chronology
from .runner import QualificationRound


def _write_rounds(
    writer: RoundArtifactWriter, rounds: tuple[QualificationRound, ...]
) -> tuple[QualificationRound, ...]:
    results: list[QualificationRound] = []
    for round_result in rounds:
        events = [
            {
                "event_id": str(getattr(event, "event_id", "")),
                "run_id": str(getattr(event, "run_id", "")),
                "sequence": int(getattr(event, "sequence", 0)),
                "event_type": str(getattr(event, "event_type", "")),
                "attempt": getattr(event, "attempt", None),
                "correlation_id": str(getattr(event, "correlation_id", "")),
                "causation_id": getattr(event, "causation_id", None),
                "payload": getattr(event, "payload", {}),
            }
            for case in round_result.cases
            for event in case.events
        ]
        artifact = writer.write_round(
            round_result.index, _round_summary(round_result), events
        )
        results.append(replace(round_result, artifact_sha256=artifact.sha256))
    return tuple(results)


def _round_summary(round_result: QualificationRound) -> dict[str, Any]:
    return {
        "index": round_result.index,
        "kind": round_result.kind,
        "execution_mode": round_result.execution_mode,
        "complete_matrix": round_result.complete_matrix,
        "passed": round_result.passed,
        "case_keys": list(round_result.case_keys),
        "deployment_fingerprints": round_result.deployment_fingerprints,
        "deployment_snapshots": [
            snapshot
            for case in round_result.cases
            for snapshot in case.resources.deployment_snapshots
        ],
        "artifact_sha256": round_result.artifact_sha256,
        "cases": [
            {
                "case_key": case.case_key,
                "score": case.score,
                "infrastructure": case.infrastructure,
                "turns": [asdict(item) for item in case.turns],
                "chronology": case_chronology(case),
                "tools": [asdict(item) for item in case.tools],
                "facts": [asdict(item) for item in case.facts],
                "setup_run_ids": list(case.setup_run_ids),
                "resources": {
                    "conversation_ids": list(case.resources.conversation_ids),
                },
            }
            for case in round_result.cases
        ],
    }
