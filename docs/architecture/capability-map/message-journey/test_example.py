"""The teaching fixture fits existing contracts; this does not qualify a model."""

import json
from pathlib import Path

from ade_api.features.agent_runtime.fact_registry import fact_type_spec
from ade_api.features.agent_runtime.memory_review import (
    bind_evidence,
    parse_review_decision,
)


HERE = Path(__file__).resolve().parent


def example():
    return json.loads((HERE / "example.json").read_text())


def test_example_is_explicitly_fictional_and_not_an_actual_persona():
    data = example()
    assert data["status"] == "fictional"
    assert "Not a live trace" in data["caption"]
    assert data["persona"]["name"] == "Rowan"


def test_correction_is_a_valid_existing_typed_proposal_not_a_new_schema():
    data = example()
    decision = parse_review_decision(data["review_decision"])
    proposal = decision.proposals[0]
    assert proposal.operation == "correct"
    assert proposal.fact_id == data["existing_fact"]["fact_id"]
    assert proposal.expected_version == data["existing_fact"]["version"]
    assert proposal.value == "Toronto"
    assert fact_type_spec(data["existing_fact"]["fact_type"]).name == (
        "person.current_location"
    )


def test_evidence_binds_to_the_current_user_not_assistant_or_prior_dialogue():
    data = example()
    decision = parse_review_decision(data["review_decision"])
    evidence = bind_evidence(
        decision.proposals[0],
        user_messages=[data["previous_user"], data["current_user"]],
    )
    assert evidence.message_id == data["current_user"]["id"]
    assert evidence.quote == "I've moved to Toronto."
    assert (
        data["current_user"]["content"][evidence.start_char : evidence.end_char]
        == evidence.quote
    )
    assert evidence.quote not in data["candidate_reply"]
