from __future__ import annotations

from copy import deepcopy
import asyncio
from pathlib import Path
from uuid import UUID

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.executor import ConversationExecutor, curated_tools
from ade_api.features.agent_runtime.context import ConversationHistoryMetadata
from ade_api.features.agent_runtime.natural_context import build_natural_context
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    preflight_reviewer_bundle,
)
from ade_api.features.prompt_center import build_prompt_template_reader
from ade_api.features.agent_runtime.natural_evaluation_capacity import (
    bind_checkpoint6_capacity,
    checked_checkpoint6_capacity,
)
from workflows.evals.character_memory_dev.natural_memory_contract import (
    load_cases,
    load_matrix,
)
from workflows.evals.character_memory_dev.natural_live_setup import facts_for_cell


def _prepared() -> dict:
    deepseek = {
        "total_tokens": 16384,
        "max_output_tokens": 4096,
        "max_model_requests": 6,
        "reviewer_repair_count": 0,
    }
    return {
        "memory_policy_version": "natural-user-assertions-v3-b",
        "deployment_snapshot": [
            {
                "role": role,
                "route_alias": "deepseek::deepseek-flash",
                "fingerprint": "a" * 64,
                "fingerprint_payload": {"context_settings": deepseek},
            }
            for role in ("conversation", "reviewer")
        ]
        + [
            {
                "role": "retriever",
                "route_alias": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
                "fingerprint": "b" * 64,
                "fingerprint_payload": {"context_settings": {}},
            }
        ],
    }


def test_role_limits_match_frozen_matrix_and_do_not_rewrite_provider_identity() -> None:
    prepared = _prepared()
    bound = bind_checkpoint6_capacity(prepared)
    assert prepared != bound
    for before, after in zip(
        prepared["deployment_snapshot"], bound["deployment_snapshot"], strict=True
    ):
        assert before["fingerprint"] == after["fingerprint"]
        assert before["fingerprint_payload"] == after["fingerprint_payload"]
    limits = checked_checkpoint6_capacity(
        bound, purpose="evaluation", natural_variant="B"
    )
    assert limits is not None
    matrix = load_matrix()
    assert (
        limits.conversation.context_window
        == matrix["budgets"]["generation"]["context_window"]
    )
    assert (
        limits.conversation.input_limit
        == matrix["budgets"]["generation"]["input_limit"]
    )
    assert (
        limits.conversation.max_output_tokens
        == matrix["budgets"]["generation"]["output_reserve"]
    )
    assert (
        limits.reviewer.context_window
        == matrix["budgets"]["reviewer"]["context_window"]
    )
    assert limits.reviewer.input_limit == matrix["budgets"]["reviewer"]["input_limit"]
    assert limits.conversation_requests == 2
    assert limits.reviewer_request_max_tokens == 1024
    assert (
        limits.reviewer_shared_suffix_tokens
        == matrix["budgets"]["reviewer"]["shared_suffix_max"]
    )


def test_diagnostic_review_output_changes_only_named_request_envelope() -> None:
    prepared = _prepared()
    normal = checked_checkpoint6_capacity(
        bind_checkpoint6_capacity(prepared), purpose="evaluation", natural_variant="B"
    )
    diagnostic_bound = bind_checkpoint6_capacity(
        prepared, diagnostic_reviewer_output=True
    )
    diagnostic = checked_checkpoint6_capacity(
        diagnostic_bound, purpose="evaluation", natural_variant="B"
    )
    assert normal is not None and diagnostic is not None
    assert diagnostic.conversation == normal.conversation
    assert diagnostic.reviewer == normal.reviewer
    assert diagnostic.reviewer.input_limit == 6759
    assert diagnostic.reviewer_request_max_tokens == 4096
    assert (
        diagnostic_bound["deployment_snapshot"][1]["fingerprint"]
        == prepared["deployment_snapshot"][1]["fingerprint"]
    )
    with pytest.raises(RuntimeValidationError, match="native B policy"):
        checked_checkpoint6_capacity(
            diagnostic_bound, purpose="evaluation", natural_variant="A"
        )
    smaller = deepcopy(prepared)
    smaller["deployment_snapshot"][1]["fingerprint_payload"]["context_settings"][
        "max_output_tokens"
    ] = 2048
    with pytest.raises(RuntimeValidationError, match="exceeds pinned provider"):
        checked_checkpoint6_capacity(
            bind_checkpoint6_capacity(smaller, diagnostic_reviewer_output=True),
            purpose="evaluation",
            natural_variant="B",
        )
    assert (
        checked_checkpoint6_capacity(
            prepared, purpose="evaluation", natural_variant="B"
        )
        is None
    )


@pytest.mark.parametrize("cell_id", ["pressure-dog", "pressure-interview"])
def test_real_prompt_pressure_packet_fits_frozen_roles(
    tmp_path: Path, cell_id: str
) -> None:
    root = Path(__file__).resolve().parents[4]
    registry = build_prompt_template_reader(
        root, persona_db_path=tmp_path / "persona.sqlite3"
    )
    prompt = registry.get_template("prompt", "chat_v20260516", scenario="chat")[
        "content"
    ]
    persona = registry.get_template("persona", "chat_linxiaotang", scenario="chat")[
        "content"
    ]
    cases, matrix = load_cases(), load_matrix()
    cell = next(item for item in matrix["cells"] if item["id"] == cell_id)
    branch = next(
        item
        for arc in cases["arcs"]
        if arc["id"] == cell["arc"]
        for item in arc["branches"]
        if item["id"] == cell["branch"]
    )
    cutoff = next(
        i for i, item in enumerate(branch["turns"]) if item[0] == cell["cutoff"]
    )
    messages = [
        {
            "id": str(UUID(int=i + 2000)),
            "sequence": i + 1,
            "role": role,
            "content": content,
        }
        for i, (_, role, content) in enumerate(branch["turns"][: cutoff + 1])
    ]
    facts = [
        {
            "id": str(UUID(int=i + 1000)),
            "entity_id": str(UUID(int=1)),
            "fact_type": item["fact_type"],
            "normalized_key": f"person.preference|subject|case-{i}",
            "qualifier": item["qualifier"],
            "value": item["value"],
            "status": item["status"],
            "version": 2 if item["status"] == "inactive" else 1,
        }
        for i, item in enumerate(facts_for_cell(cell, branch))
    ]
    entities = [
        {
            "id": str(UUID(int=1)),
            "kind": "subject",
            "label": "Synthetic checkpoint-6 subject",
        }
    ]
    limits = checked_checkpoint6_capacity(
        bind_checkpoint6_capacity(_prepared()),
        purpose="evaluation",
        natural_variant="B",
    )
    assert limits is not None
    bundles = {
        variant: build_natural_context(
            variant=variant,
            system_prompt=prompt
            + "P" * matrix["budgets"]["pressure"]["synthetic_prompt_repeat_bytes"],
            persona=persona,
            current_user=messages[-1],
            eligible_recent_messages=messages[:-1],
            lifecycle_facts=facts,
            retrieved_facts=[facts[0]],
            entities=entities,
            summary_content="",
            history_metadata=ConversationHistoryMetadata(
                completed_user_turns=sum(m["role"] == "user" for m in messages[:-1]),
                summary_through_sequence=0,
            ),
            budget=limits.conversation,
            reviewer_suffix_limit=limits.reviewer_shared_suffix_tokens,
        )
        for variant in ("A", "B")
    }
    assert bundles["A"].lifecycle_withheld
    assert len(bundles["A"].source_messages) == 1
    assert len(bundles["B"].source_messages) == len(messages)
    assert (
        bundles["B"].context.estimated_input_tokens <= limits.conversation.input_limit
    )
    assert (
        preflight_reviewer_bundle(
            model_key="deepseek::deepseek-flash",
            provider_adapter="deepseek_openai",
            current_user_message=messages[-1],
            source_messages=list(bundles["B"].source_messages),
            facts=facts,
            entities=entities,
            candidate_reply_reserve=limits.conversation.max_output_tokens,
            input_token_limit=limits.reviewer.input_limit,
        )
        <= limits.reviewer.input_limit
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda row: row["deployment_snapshot"][0]["natural_evaluation_capacity"].update(
            context_window=8192
        ),
        lambda row: row["deployment_snapshot"][0].update(route_alias="spark::chat"),
        lambda row: row["deployment_snapshot"][1]["fingerprint_payload"][
            "context_settings"
        ].update(reviewer_repair_count=1),
        lambda row: row["deployment_snapshot"][0]["fingerprint_payload"][
            "context_settings"
        ].update(total_tokens=2048),
    ],
)
def test_changed_or_unsupported_binding_is_rejected(mutation) -> None:
    bound = bind_checkpoint6_capacity(_prepared())
    mutation(bound)
    with pytest.raises(RuntimeValidationError):
        checked_checkpoint6_capacity(bound, purpose="evaluation", natural_variant="A")


def test_binding_cannot_escape_natural_evaluation_scope() -> None:
    bound = bind_checkpoint6_capacity(_prepared())
    for purpose, variant in (("agent_studio", "B"), ("evaluation", None)):
        with pytest.raises(RuntimeValidationError, match="outside its scope"):
            checked_checkpoint6_capacity(
                deepcopy(bound), purpose=purpose, natural_variant=variant
            )


def test_native_executor_stops_after_two_tool_requests() -> None:
    limits = checked_checkpoint6_capacity(
        bind_checkpoint6_capacity(_prepared()),
        purpose="evaluation",
        natural_variant="B",
    )
    assert limits is not None

    class RepeatedToolProvider:
        def __init__(self) -> None:
            self.calls = 0

        async def chat_completion(self, payload, *, timeout_seconds):
            self.calls += 1
            assert payload["max_tokens"] == 512
            return {
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": f"call-{self.calls}",
                                    "type": "function",
                                    "function": {
                                        "name": "search_memory",
                                        "arguments": '{"query":"Roxy","limit":1}',
                                    },
                                }
                            ],
                        },
                    }
                ]
            }

    provider = RepeatedToolProvider()

    async def search(query: str, limit: int):
        return []

    async def scenario() -> None:
        with pytest.raises(RuntimeValidationError, match="tool-step budget"):
            await ConversationExecutor(provider).execute(
                model_key="deepseek::deepseek-flash",
                messages=[{"role": "user", "content": "Roxy?"}],
                timeout_seconds=180,
                max_output_tokens=limits.conversation.max_output_tokens,
                max_model_requests=limits.conversation_requests,
                input_token_limit=limits.conversation.input_limit,
                tools=curated_tools(("search_memory",), search_memory=search),
            )

    asyncio.run(scenario())
    assert provider.calls == 2
