"""Serialized 0/12/48/128/256 short/long packet and reviewer capacity grid."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import UUID

import pytest

from ade_api.features.agent_runtime.context import (
    ContextBudget,
    ConversationHistoryMetadata,
)
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.executor import ConversationExecutor
from ade_api.features.agent_runtime.natural_context import build_natural_context
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    natural_review_request,
    preflight_reviewer_bundle,
    serialized_review_tokens,
)
from workflows.evals.character_memory_dev.natural_memory_contract import (
    load_cases,
    load_matrix,
)
from workflows.evals.character_memory_dev.tests.test_natural_matrix_packets import (
    PacketRouter,
    _branch,
    _facts,
    _history,
)


def test_grid_records_full_serialized_requests_and_independent_reviewer_capacity(
    tmp_path: Path,
) -> None:
    cases, matrix = load_cases(), load_matrix()
    branch = _branch(
        cases,
        {"arc": "17-clarification-spans", "branch": "clear-answer"},
    )
    prior, current, _ = _history(branch, "u2")
    generation_budget = ContextBudget(
        context_window=4096, max_output_tokens=512, tool_schema_tokens=256
    )
    reviewer_limit = matrix["budgets"]["reviewer"]["input_limit"]
    output = tmp_path / "grid"
    output.mkdir()
    results = asyncio.run(
        _execute_grid(
            output=output,
            prior=prior,
            current=current,
            generation_budget=generation_budget,
            reviewer_limit=reviewer_limit,
        )
    )
    assert len(results) == 30
    assert all(
        item["reviewer_target_count"] == item["record_count"] for item in results
    )
    assert all(
        item["generation_input_tokens"] <= generation_budget.input_limit
        for item in results
    )
    assert all(
        item["reviewer_overflow"] for item in results if item["record_count"] == 256
    )
    assert all(
        not item["reviewer_overflow"] for item in results if item["record_count"] == 0
    )


async def _execute_grid(
    *,
    output: Path,
    prior: list[dict],
    current: dict,
    generation_budget: ContextBudget,
    reviewer_limit: int,
) -> list[dict]:
    results = []
    entities = [{"id": str(UUID(int=1)), "kind": "subject", "label": ""}]
    for count in (0, 12, 48, 128, 256):
        for size in ("short", "long"):
            facts = _facts({"id": "grid", "record_count": count}, size=size)
            for variant in ("A", "A0", "B"):
                built = build_natural_context(
                    variant=variant,
                    system_prompt="Policy",
                    persona="Companion",
                    current_user=current,
                    eligible_recent_messages=prior,
                    lifecycle_facts=facts,
                    retrieved_facts=facts[:8],
                    entities=entities,
                    summary_content="",
                    history_metadata=ConversationHistoryMetadata(
                        completed_user_turns=sum(
                            row["role"] == "user" for row in prior
                        ),
                        summary_through_sequence=0,
                    ),
                    budget=generation_budget,
                    reviewer_suffix_limit=640,
                )
                requests = []
                await ConversationExecutor(PacketRouter()).execute(
                    model_key="fake::conversation",
                    messages=built.context.messages,
                    timeout_seconds=30,
                    max_output_tokens=512,
                    input_token_limit=generation_budget.input_limit,
                    observe_request=requests.append,
                )
                review = natural_review_request(
                    model_key="fake::reviewer",
                    provider_adapter="synthetic",
                    current_user_message=current,
                    source_messages=list(built.source_messages),
                    facts=facts,
                    entities=entities,
                    candidate_reply="R" * 2048,
                )
                review_tokens = serialized_review_tokens(review)
                overflow = review_tokens > reviewer_limit
                if overflow:
                    with pytest.raises(RuntimeValidationError, match="reviewer"):
                        preflight_reviewer_bundle(
                            model_key="fake::reviewer",
                            provider_adapter="synthetic",
                            current_user_message=current,
                            source_messages=list(built.source_messages),
                            facts=facts,
                            entities=entities,
                            candidate_reply_reserve=512,
                            input_token_limit=reviewer_limit,
                        )
                else:
                    assert (
                        preflight_reviewer_bundle(
                            model_key="fake::reviewer",
                            provider_adapter="synthetic",
                            current_user_message=current,
                            source_messages=list(built.source_messages),
                            facts=facts,
                            entities=entities,
                            candidate_reply_reserve=512,
                            input_token_limit=reviewer_limit,
                        )
                        == review_tokens
                    )
                packet = json.loads(review["messages"][1]["content"])
                result = {
                    "record_count": count,
                    "size_class": size,
                    "variant": variant,
                    "lifecycle_withheld": built.lifecycle_withheld,
                    "generation_input_tokens": built.context.estimated_input_tokens,
                    "generation_input_limit": generation_budget.input_limit,
                    "reviewer_tokens_with_max_reply": review_tokens,
                    "reviewer_input_limit": reviewer_limit,
                    "reviewer_overflow": overflow,
                    "reviewer_target_count": len(packet["targets"]),
                    "selected_fact_ids": built.context.retrieved_fact_ids,
                    "omitted_message_ids": built.context.omitted_message_ids,
                    "generation_request": requests[0],
                    "reviewer_request": review,
                }
                (output / f"{count}-{size}-{variant}.json").write_text(
                    json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n"
                )
                results.append(result)
    return results
