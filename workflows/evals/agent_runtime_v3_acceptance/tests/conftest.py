from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# The shared package is delivered by a sibling task. This strict local stand-in
# lets this bounded workflow test the public contract boundary before integration.
contracts = types.ModuleType("agent_runtime_eval_contracts")


@dataclass(frozen=True)
class FactObservation:
    subject_key: str
    facts: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class TurnObservation:
    case_key: str
    conversation_key: str
    run_id: str
    status: str
    assistant_content: str
    attempt_count: int


@dataclass(frozen=True)
class EventObservation:
    run_id: str
    sequence: int
    event_type: str
    attempt: int | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class ToolObservation:
    run_id: str
    name: str
    succeeded: bool
    payload: dict[str, Any]


def score_case(*, case: object, observations: dict[str, Any]) -> dict[str, Any]:
    failures = list(observations.get("failures", ()))
    return {
        "case_key": str(getattr(case, "key")),
        "pass": not failures,
        "failed_checks": failures,
        "turn_count": len(observations.get("turns", ())),
    }


def load_cases() -> tuple[object, ...]:
    return ()


contracts.FactObservation = FactObservation
contracts.TurnObservation = TurnObservation
contracts.EventObservation = EventObservation
contracts.ToolObservation = ToolObservation
contracts.score_case = score_case
contracts.load_cases = load_cases
sys.modules.setdefault("agent_runtime_eval_contracts", contracts)
