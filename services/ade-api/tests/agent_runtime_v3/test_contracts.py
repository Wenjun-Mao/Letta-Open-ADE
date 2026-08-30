from __future__ import annotations

import pytest
from pydantic import ValidationError

from ade_api.features.agent_runtime_v3.contracts import AcceptTurnRequest
from ade_api.features.agent_runtime_v3.errors import RuntimeValidationError
from ade_api.features.agent_runtime_v3.fact_registry import (
    FACT_TYPE_REGISTRY,
    PREFERENCE_QUALIFIERS,
    RELATIONSHIP_QUALIFIERS,
    FactRegistryError,
    fact_key,
    fact_type_spec,
    normalize_qualifier,
)
from ade_api.features.agent_runtime_v3.memory_review import (
    bind_evidence,
    parse_review_decision,
    review_json_schema,
)


def test_turn_defaults_have_one_attempt_and_180_second_timeout() -> None:
    request = AcceptTurnRequest(content="hello", idempotency_key="turn-1")
    assert request.timeout_seconds == 180
    assert request.retry_count == 0


@pytest.mark.parametrize("field", ["content", "idempotency_key"])
def test_turn_rejects_blank_required_text(field: str) -> None:
    payload = {"content": "hello", "idempotency_key": "turn-1", field: "   "}
    with pytest.raises(ValidationError):
        AcceptTurnRequest.model_validate(payload)


def test_fact_registry_rejects_model_invented_namespaces() -> None:
    with pytest.raises(FactRegistryError, match="Unknown fact type"):
        fact_type_spec("model.invented")


def test_fact_key_binds_type_entity_and_qualifier() -> None:
    spec = fact_type_spec("person.preference")
    assert normalize_qualifier(spec, "Music") == "music"
    assert fact_key("person.preference", "subject-1", "music") == (
        "person.preference|subject-1|music"
    )


def test_review_operation_shapes_are_closed_and_explicit() -> None:
    with pytest.raises(RuntimeValidationError, match="expected_version"):
        parse_review_decision(
            {
                "proposals": [
                    {
                        "operation": "correct",
                        "fact_id": "fact-1",
                        "value": "张伟",
                        "evidence_quote": "我叫张伟",
                    }
                ]
            }
        )

    with pytest.raises(RuntimeValidationError, match="subject_id"):
        parse_review_decision(
            {
                "proposals": [
                    {
                        "operation": "add",
                        "fact_type": "person.name",
                        "value": "张伟",
                        "evidence_quote": "我叫张伟",
                        "subject_id": "another-subject",
                    }
                ]
            }
        )


def test_review_operation_versions_reject_coercion() -> None:
    with pytest.raises(RuntimeValidationError, match="expected_version"):
        parse_review_decision(
            {
                "proposals": [
                    {
                        "operation": "correct",
                        "fact_id": "fact-1",
                        "expected_version": "1",
                        "value": "张伟",
                        "evidence_quote": "我叫张伟",
                    }
                ]
            }
        )


def test_review_rejects_deferred_merge_operation() -> None:
    with pytest.raises(RuntimeValidationError, match="Input tag 'merge'"):
        parse_review_decision(
            {
                "proposals": [
                    {
                        "operation": "merge",
                        "target_fact_ids": ["fact-1", "fact-2"],
                        "expected_versions": {"fact-1": 1, "fact-2": 1},
                        "value": "jazz",
                        "evidence_quote": "jazz",
                    }
                ]
            }
        )


def test_review_schema_discriminates_operation_specific_shapes() -> None:
    schema = review_json_schema()
    schema_text = str(schema)
    assert "discriminator" in schema_text
    assert "oneOf" in schema_text

    add_properties = schema["$defs"]["AddProposal"]["properties"]
    assert set(add_properties["fact_type"]["enum"]) == set(FACT_TYPE_REGISTRY)
    qualifier_variants = add_properties["qualifier"]["anyOf"]
    qualifier_enum = next(item["enum"] for item in qualifier_variants if "enum" in item)
    assert set(qualifier_enum) == set(
        (*PREFERENCE_QUALIFIERS, *RELATIONSHIP_QUALIFIERS)
    )
    assert "favorite_place" not in qualifier_enum

    proposal = parse_review_decision(
        {
            "proposals": [
                {
                    "operation": "add",
                    "fact_type": "person.name",
                    "value": "张伟",
                    "evidence_quote": "我叫张伟",
                }
            ]
        }
    ).proposals[0]
    assert proposal.operation.value == "add"


def test_explicit_forgetting_schema_excludes_other_operations() -> None:
    schema = review_json_schema(mode="forget")
    schema_text = str(schema)
    assert "ForgetProposal" in schema_text
    assert "AddProposal" not in schema_text
    assert "CorrectProposal" not in schema_text

    proposal = parse_review_decision(
        {
            "proposals": [
                {
                    "operation": "forget",
                    "value": None,
                    "fact_id": "fact-1",
                    "expected_version": 1,
                    "evidence_quote": "forget jazz",
                }
            ]
        },
        mode="forget",
    ).proposals[0]
    assert proposal.operation.value == "forget"

    with pytest.raises(RuntimeValidationError, match="Invalid memory review output"):
        parse_review_decision(
            {
                "proposals": [
                    {
                        "operation": "add",
                        "fact_type": "person.name",
                        "value": "张伟",
                        "evidence_quote": "张伟",
                    }
                ]
            },
            mode="forget",
        )


def test_review_schema_rejects_noncanonical_qualifier_aliases() -> None:
    with pytest.raises(RuntimeValidationError, match="qualifier"):
        parse_review_decision(
            {
                "proposals": [
                    {
                        "operation": "add",
                        "fact_type": "person.preference",
                        "qualifier": "favorite_place",
                        "value": "Royal Ontario Museum",
                        "evidence_quote": "Royal Ontario Museum",
                    }
                ]
            }
        )


@pytest.mark.parametrize("operation", ["correct", "forget"])
def test_existing_fact_operations_reject_model_selected_metadata(
    operation: str,
) -> None:
    payloads = {
        "correct": {
            "operation": "correct",
            "fact_id": "fact-1",
            "expected_version": 1,
            "value": "张伟",
            "evidence_quote": "我叫张伟",
        },
        "forget": {
            "operation": "forget",
            "fact_id": "fact-1",
            "expected_version": 1,
            "value": None,
            "evidence_quote": "forget jazz",
        },
    }
    proposal = {**payloads[operation], "fact_type": "person.name"}

    with pytest.raises(RuntimeValidationError, match="fact_type"):
        parse_review_decision({"proposals": [proposal]})


def test_evidence_must_bind_one_user_authored_span() -> None:
    proposal = parse_review_decision(
        {
            "proposals": [
                {
                    "operation": "add",
                    "fact_type": "pet.name",
                    "value": "Rocky",
                    "evidence_quote": "Rocky",
                    "new_entity_label": "Rocky",
                }
            ]
        }
    ).proposals[0]
    evidence = bind_evidence(
        proposal,
        user_messages=[{"id": "message-1", "content": "我的狗叫 Rocky。"}],
    )
    assert evidence.message_id == "message-1"
    assert evidence.quote == "Rocky"
    assert evidence.start_char == 5
    assert evidence.end_char == 10
    assert len(evidence.message_sha256) == 64
