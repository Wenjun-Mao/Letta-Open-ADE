"""Shared local/fact context and reviewer-capacity selection for one turn."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context import (
    BuiltContext,
    ContextBudget,
    ConversationHistoryMetadata,
    build_context,
    context_budget_from_deployment,
)
from .errors import RuntimeValidationError
from .natural_context import (
    NaturalVariant,
    build_natural_context,
    full_lifecycle_snapshot_fits,
)
from .natural_evaluation_capacity import NaturalEvaluationCapacity
from .natural_memory_reviewer import preflight_reviewer_bundle, reviewer_suffix_limit
from .turn_memory_views import context_fact


@dataclass(frozen=True)
class TurnContextSelection:
    context: BuiltContext
    natural_source_messages: tuple[dict[str, Any], ...]
    active_facts: list[dict[str, Any]]
    reviewer_input_limit: int
    reviewer_request_max_tokens: int


def needs_selective_retrieval(
    *,
    natural_variant: NaturalVariant | None,
    definition: dict[str, Any],
    current_user: dict[str, Any],
    facts: list[dict[str, Any]],
    history_metadata: ConversationHistoryMetadata,
    input_limit: int,
) -> bool:
    if natural_variant not in {"A", "A0"}:
        return True
    return not full_lifecycle_snapshot_fits(
        system_prompt=str(definition["prompt_content"]),
        persona=str(definition["persona_content"]),
        current_user_content=str(current_user["content"]),
        lifecycle_facts=facts,
        history_metadata=history_metadata,
        input_limit=input_limit,
    )


def select_turn_context(
    *,
    state: dict[str, Any],
    definition: dict[str, Any],
    current_user: dict[str, Any],
    recent_messages: list[dict[str, Any]],
    retrieved: list[dict[str, Any]],
    summary_content: str,
    history_metadata: ConversationHistoryMetadata,
    budget: ContextBudget,
    natural_variant: NaturalVariant | None,
    evaluation_capacity: NaturalEvaluationCapacity | None,
    reviewer_deployment: dict[str, Any],
    reviewer_adapter: str,
    history_capable: bool,
) -> TurnContextSelection:
    active_facts = sorted(
        state["active_facts"],
        key=lambda item: (item["updated_at"], str(item["id"])),
        reverse=True,
    )
    if natural_variant is None:
        try:
            context = build_context(
                system_prompt=str(definition["prompt_content"]),
                persona=str(definition["persona_content"]),
                active_facts=[context_fact(item) for item in active_facts[:12]],
                conversation_summary=summary_content,
                history_metadata=history_metadata,
                retrieved_facts=[context_fact(item) for item in retrieved],
                recent_messages=recent_messages,
                current_user_content=str(current_user["content"]),
                budget=budget,
            )
        except ValueError as exc:
            raise RuntimeValidationError(str(exc)) from exc
        if context.omitted_message_ids:
            raise RuntimeValidationError(
                "Context construction omitted unsummarized conversation history"
            )
        return TurnContextSelection(context, (), active_facts, 0, 1024)

    reviewer_budget = (
        evaluation_capacity.reviewer
        if evaluation_capacity is not None
        else ContextBudget(
            context_window=context_budget_from_deployment(
                reviewer_deployment
            ).context_window,
            max_output_tokens=1024,
            tool_schema_tokens=0,
        )
    )
    reviewer_input_limit = reviewer_budget.input_limit
    reviewer_request_max_tokens = (
        evaluation_capacity.reviewer_request_max_tokens
        if evaluation_capacity is not None
        else 1024
    )
    natural_bundle = build_natural_context(
        variant=natural_variant,
        system_prompt=str(definition["prompt_content"]),
        persona=str(definition["persona_content"]),
        current_user=current_user,
        eligible_recent_messages=recent_messages,
        lifecycle_facts=state["facts"],
        retrieved_facts=retrieved,
        entities=state["entities"],
        summary_content=summary_content,
        history_metadata=history_metadata,
        budget=budget,
        reviewer_suffix_limit=(
            evaluation_capacity.reviewer_shared_suffix_tokens
            if evaluation_capacity is not None
            else reviewer_suffix_limit(
                model_key=str(reviewer_deployment["route_alias"]),
                provider_adapter=reviewer_adapter,
                current_user_message=current_user,
                facts=state["facts"],
                entities=state["entities"],
                input_token_limit=reviewer_input_limit,
                candidate_reply_reserve=budget.max_output_tokens,
                history_capable=history_capable,
            )
        ),
    )
    preflight_reviewer_bundle(
        model_key=str(reviewer_deployment["route_alias"]),
        provider_adapter=reviewer_adapter,
        current_user_message=current_user,
        source_messages=list(natural_bundle.source_messages),
        facts=state["facts"],
        entities=state["entities"],
        candidate_reply_reserve=budget.max_output_tokens,
        input_token_limit=reviewer_input_limit,
        max_output_tokens=reviewer_request_max_tokens,
        history_capable=history_capable,
    )
    return TurnContextSelection(
        natural_bundle.context,
        natural_bundle.source_messages,
        active_facts,
        reviewer_input_limit,
        reviewer_request_max_tokens,
    )
