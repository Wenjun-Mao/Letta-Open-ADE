"""Translate study-runtime records into stable evaluation observations."""

from __future__ import annotations

from collections.abc import Iterable

from agent_runtime_eval_contracts import (
    EventObservation,
    FactObservation,
    ToolObservation,
    TurnObservation,
)

from .contracts import MemoryFact, TurnResult


def normalize_facts(facts: Iterable[MemoryFact]) -> tuple[FactObservation, ...]:
    return tuple(FactObservation(key=fact.key, value=fact.value) for fact in facts)


def normalize_turn(result: TurnResult) -> TurnObservation:
    return TurnObservation(
        status=result.run.status.value,
        assistant_text=(
            result.assistant_message.content
            if result.assistant_message is not None
            else None
        ),
        candidate_assistant_text=result.candidate_assistant_text,
        events=tuple(
            EventObservation(type=event.type.value) for event in result.events
        ),
        tools=tuple(
            ToolObservation(name=tool.name, succeeded=tool.succeeded)
            for tool in result.tool_executions
        ),
        usage=result.usage,
        elapsed_seconds=result.elapsed_seconds,
    )
