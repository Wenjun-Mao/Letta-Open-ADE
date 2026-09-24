from __future__ import annotations

from copy import deepcopy
from uuid import UUID

import pytest

from ade_api.features.agent_runtime.context import (
    ContextBudget,
    ConversationHistoryMetadata,
)
from ade_api.features.agent_runtime.natural_context import (
    build_natural_context,
    full_lifecycle_snapshot_fits,
)
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    preflight_reviewer_bundle,
)
from workflows.evals.character_memory_dev.natural_memory_contract import (
    expanded_cells,
    load_cases,
    load_matrix,
    validate_cases,
    validate_matrix,
)


def test_all_worked_arcs_are_chronological_isolated_fixtures() -> None:
    cases = load_cases()
    assert [arc["section"] for arc in cases["arcs"]] == list(range(1, 23))
    assert sum(len(arc["branches"]) for arc in cases["arcs"]) >= 40
    branches = {branch["id"] for arc in cases["arcs"] for branch in arc["branches"]}
    assert {
        "partial-assent",
        "no-save-endorsement",
        "reply-write-contradiction",
        "identity-race",
        "compaction-after-breakup",
    } <= branches


def test_future_turn_cannot_be_an_expected_checkpoint_source() -> None:
    cases = deepcopy(load_cases())
    first = cases["arcs"][0]["branches"][0]
    first["expected"] = [first["expected"][1], first["expected"][0]]
    with pytest.raises(ValueError, match="chronological"):
        validate_cases(cases)


def test_matrix_freezes_mandatory_cells_and_request_accounting() -> None:
    matrix = load_matrix()
    names = [name for name, _, _ in expanded_cells(matrix)]
    assert len(names) == len(set(names)) == 30
    assert "pressure-dog::A" in names
    assert "pressure-dog::B" in names
    assert "summary-after-change::A0" in names
    assert (
        matrix["live_request_schedule_proposed_not_authorized"][
            "outbound_provider_calls_at_checkpoint_1"
        ]
        == 0
    )


def test_pressure_must_withhold_for_a_while_b_and_reviewer_fit() -> None:
    matrix = deepcopy(load_matrix())
    matrix["budgets"]["pressure"]["reviewer_full_packet_max_tokens"] = 8000
    with pytest.raises(ValueError, match="mechanically distinguishable"):
        validate_matrix(matrix, load_cases())


def test_every_mandatory_response_has_same_selectable_variants() -> None:
    matrix = deepcopy(load_matrix())
    response = next(cell for cell in matrix["cells"] if cell["id"] == "pressure-dog")
    response["variants"] = ["B"]
    with pytest.raises(ValueError, match="compare A and B"):
        validate_matrix(matrix, load_cases())


def test_compaction_must_preserve_useful_information_outside_raw_suffix() -> None:
    matrix = deepcopy(load_matrix())
    matrix["positive_compaction_assertion"]["raw_suffix_excludes"] = []
    with pytest.raises(ValueError, match="outside raw suffix"):
        validate_matrix(matrix, load_cases())


@pytest.mark.parametrize(
    ("cell_id", "minimum_full_tokens", "reviewer_tokens", "required_source"),
    [
        ("pressure-dog", 3074, 6706, "u1"),
        ("pressure-interview", 3079, 6720, "u2"),
    ],
)
def test_pressure_packets_execute_the_frozen_serialized_boundary(
    cell_id: str,
    minimum_full_tokens: int,
    reviewer_tokens: int,
    required_source: str,
) -> None:
    cases, matrix = load_cases(), load_matrix()
    pressure = matrix["budgets"]["pressure"]
    generation = matrix["budgets"]["generation"]
    reviewer = matrix["budgets"]["reviewer"]
    cell = next(item for item in matrix["cells"] if item["id"] == cell_id)
    branch = next(
        item
        for arc in cases["arcs"]
        if arc["id"] == cell["arc"]
        for item in arc["branches"]
        if item["id"] == cell["branch"]
    )
    facts = [
        {
            "id": str(UUID(int=index + 1000)),
            "entity_id": str(UUID(int=1)),
            "fact_type": "person.preference",
            "normalized_key": f"person.preference|{index:03d}",
            "qualifier": "other",
            "value": f"M{index}" + " x" * pressure["synthetic_value_repetitions"],
            "status": "inactive" if index % 3 == 0 else "active",
            "version": 1,
        }
        for index in range(pressure["record_count"])
    ]
    entities = [{"id": str(UUID(int=1)), "kind": "subject", "label": ""}]
    messages = []
    run_number = 0
    for index, (label, role, content) in enumerate(branch["turns"]):
        if role == "user":
            run_number += 1
        messages.append(
            {
                "id": str(UUID(int=index + 2000)),
                "label": label,
                "run_id": str(UUID(int=run_number + 3000)),
                "sequence": index + 1,
                "role": role,
                "content": content,
            }
        )
    cutoff = next(
        index
        for index, message in enumerate(messages)
        if message["label"] == cell["cutoff"]
    )
    current, prior = messages[cutoff], messages[:cutoff]
    history = ConversationHistoryMetadata(
        completed_user_turns=sum(message["role"] == "user" for message in prior),
        summary_through_sequence=0,
    )
    policy = "Policy " + "a" * pressure["synthetic_prompt_repeat_bytes"]
    budget = ContextBudget(
        context_window=generation["context_window"],
        max_output_tokens=generation["output_reserve"],
        tool_schema_tokens=generation["tool_schema"],
    )
    reviewer_budget = ContextBudget(
        context_window=reviewer["context_window"],
        max_output_tokens=reviewer["output_reserve"],
        tool_schema_tokens=0,
    )
    assert budget.input_limit == generation["input_limit"]
    assert reviewer_budget.input_limit == reviewer["input_limit"]
    assert full_lifecycle_snapshot_fits(
        system_prompt=policy,
        persona="Companion",
        current_user_content=current["content"],
        lifecycle_facts=facts,
        history_metadata=history,
        input_limit=minimum_full_tokens,
    )
    assert not full_lifecycle_snapshot_fits(
        system_prompt=policy,
        persona="Companion",
        current_user_content=current["content"],
        lifecycle_facts=facts,
        history_metadata=history,
        input_limit=minimum_full_tokens - 1,
    )
    bundles = {
        variant: build_natural_context(
            variant=variant,
            system_prompt=policy,
            persona="Companion",
            current_user=current,
            eligible_recent_messages=prior,
            lifecycle_facts=facts,
            retrieved_facts=[facts[0]],
            entities=entities,
            summary_content="",
            history_metadata=history,
            budget=budget,
            reviewer_suffix_limit=reviewer["shared_suffix_max"],
        )
        for variant in ("A", "A0", "B")
    }
    assert bundles["A"].lifecycle_withheld
    assert bundles["A0"].lifecycle_withheld
    assert bundles["A"].context.messages == bundles["A0"].context.messages
    assert [message["label"] for message in bundles["A"].source_messages] == [
        cell["cutoff"]
    ]
    b_sources = [message["label"] for message in bundles["B"].source_messages]
    assert required_source in b_sources
    assert b_sources[-1] == cell["cutoff"]
    assert (
        bundles["B"].context.estimated_input_tokens
        <= pressure["b_selective_packet_max_tokens"]
    )
    assert (
        preflight_reviewer_bundle(
            model_key="fake::reviewer",
            provider_adapter="deepseek_openai",
            current_user_message=current,
            source_messages=list(bundles["B"].source_messages),
            facts=facts,
            entities=entities,
            candidate_reply_reserve=generation["output_reserve"],
            input_token_limit=reviewer_budget.input_limit,
        )
        == reviewer_tokens
    )
    assert reviewer_tokens <= pressure["reviewer_full_packet_max_tokens"]
