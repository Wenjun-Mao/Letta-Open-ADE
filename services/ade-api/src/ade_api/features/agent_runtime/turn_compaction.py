"""Plan and execute only the narrative compaction eligible for this turn."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from .compaction import plan_compaction
from .context import conversation_history_metadata
from .natural_context import full_lifecycle_snapshot_fits

if TYPE_CHECKING:
    from .context import ContextBudget
    from .executor import ConversationExecutor, ModelCompaction
    from .natural_attempt_evidence import NaturalAttemptEvidence


async def compact_turn(
    *,
    state: dict[str, Any],
    definition: dict[str, Any],
    current_user: dict[str, Any],
    natural_variant: str | None,
    budget: ContextBudget,
    executor: ConversationExecutor,
    deployment: dict[str, Any],
    deadline: float,
    evidence: NaturalAttemptEvidence | None,
) -> ModelCompaction | None:
    plan = (
        None
        if natural_variant == "B"
        else plan_compaction(
            messages=state["messages"],
            current_user_message_id=str(current_user["id"]),
            summary=state["summary"],
            recent_token_budget=budget.recent_tokens,
            compaction_input_token_budget=budget.input_limit,
        )
    )
    if natural_variant in {"A", "A0"} and plan is not None:
        history = conversation_history_metadata(
            messages=state["messages"],
            current_sequence=int(current_user["sequence"]),
            summary_through_sequence=plan.through_sequence,
        )
        if not full_lifecycle_snapshot_fits(
            system_prompt=str(definition["prompt_content"]),
            persona=str(definition["persona_content"]),
            current_user_content=str(current_user["content"]),
            lifecycle_facts=state["facts"],
            history_metadata=history,
            input_limit=budget.input_limit,
        ):
            # Do not compact narrative that A/A0's selected bundle will withhold.
            plan = None
    if plan is None:
        return None
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("whole runtime attempt timed out")
    result = await executor.compact(
        model_key=str(deployment["route_alias"]),
        model_fingerprint=str(deployment["fingerprint"]),
        plan=plan,
        timeout_seconds=remaining,
        max_output_tokens=budget.max_output_tokens,
        summary_token_budget=budget.summary_tokens,
        observe_request=evidence.capture_compaction_request if evidence else None,
    )
    if evidence is not None:
        evidence.capture_compaction_result(result)
    return result
