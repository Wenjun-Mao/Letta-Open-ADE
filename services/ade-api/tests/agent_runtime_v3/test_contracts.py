from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ade_api.features.agent_runtime_v3.contracts import (
    AcceptTurnRequest,
    AgentStudioResetRequest,
    ConversationStateResponse,
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
    MemoryFactResponse,
    RunResponse,
)
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


def test_agent_studio_session_requires_exactly_one_definition_and_subject_source() -> (
    None
):
    definition = CreateAgentDefinitionRequest(
        definition_key="companion",
        name="Companion",
        model_key="dgx_vllm::qwen",
        reviewer_model_key="dgx_vllm::qwen",
        embedding_model_key="dgx_embedding::qwen",
    )
    subject = CreateMemorySubjectRequest(
        external_key="person:zhang-wei",
        display_name="Zhang Wei",
    )
    request = CreateAgentStudioSessionRequest(
        idempotency_key="studio-session-1",
        title="First conversation",
        new_definition=definition,
        new_subject=subject,
    )

    assert request.new_definition == definition
    assert request.new_subject == subject

    with pytest.raises(ValidationError, match="exactly one definition source"):
        CreateAgentStudioSessionRequest(
            idempotency_key="studio-session-2",
            title="Invalid",
            agent_definition_id="definition-1",
            new_definition=definition,
            new_subject=subject,
        )

    with pytest.raises(ValidationError, match="exactly one subject source"):
        CreateAgentStudioSessionRequest(
            idempotency_key="studio-session-3",
            title="Invalid",
            new_definition=definition,
        )


def test_agent_studio_reset_requires_the_explicit_confirmation_phrase() -> None:
    request = AgentStudioResetRequest(
        idempotency_key="reset-1",
        confirmation="RESET ADE AGENT STUDIO",
    )
    assert request.confirmation == "RESET ADE AGENT STUDIO"

    with pytest.raises(ValidationError):
        AgentStudioResetRequest(
            idempotency_key="reset-2",
            confirmation="reset",
        )


def test_read_models_expose_summary_provenance_and_run_controls() -> None:
    now = datetime(2026, 8, 30, tzinfo=UTC)
    state = ConversationStateResponse.model_validate(
        {
            "id": "conversation-1",
            "agent_definition_id": "definition-1",
            "memory_subject_id": "subject-1",
            "version": 2,
            "created_at": now,
            "messages": [],
            "summary": {
                "id": "summary-2",
                "version": 2,
                "previous_summary_id": "summary-1",
                "content": "The user has a dog named Rocky.",
                "source_boundary": {
                    "through_sequence": 4,
                    "message_ids": ["message-1", "message-2"],
                },
                "provenance": {
                    "run_id": "run-2",
                    "model_key": "dgx_vllm::qwen",
                    "model_fingerprint": "a" * 64,
                    "provider_request_id": "provider-2",
                    "content_sha256": "b" * 64,
                    "prompt_sha256": "c" * 64,
                    "input_sha256": "d" * 64,
                    "policy_sha256": "e" * 64,
                },
                "created_at": now,
            },
        }
    )
    run = RunResponse.model_validate(
        {
            "id": "run-2",
            "conversation_id": "conversation-1",
            "status": "succeeded",
            "qualification_state": "unqualified",
            "attempt_count": 2,
            "timeout_seconds": 180.0,
            "retry_count": 1,
            "created_at": now,
        }
    )
    fact = MemoryFactResponse.model_validate(
        {
            "id": "fact-1",
            "key": "pet.name|entity-1|",
            "fact_type": "pet.name",
            "entity_id": "entity-1",
            "entity_kind": "pet",
            "entity_label": "Rocky",
            "value": "Rocky",
            "status": "active",
            "version": 2,
            "revisions": [
                {
                    "id": "revision-2",
                    "operation": "correct",
                    "fact_version": 2,
                    "value": "Rocky",
                    "run_id": "run-2",
                    "predecessor_revision_ids": ["revision-1"],
                    "evidence": [],
                    "created_at": now,
                }
            ],
            "updated_at": now,
        }
    )

    assert state.summary is not None
    assert state.summary.source_boundary.through_sequence == 4
    assert state.summary.provenance.model_key == "dgx_vllm::qwen"
    assert run.timeout_seconds == 180.0
    assert run.retry_count == 1
    assert fact.entity_label == "Rocky"
    assert fact.revisions[0].predecessor_revision_ids == ["revision-1"]


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


def test_no_active_facts_schema_excludes_existing_fact_operations() -> None:
    schema_text = str(review_json_schema(mode="add"))
    assert "AddProposal" in schema_text
    assert "CorrectProposal" not in schema_text
    assert "ForgetProposal" not in schema_text

    proposal = parse_review_decision(
        {
            "proposals": [
                {
                    "operation": "add",
                    "fact_type": "person.preference",
                    "qualifier": "color",
                    "value": "蓝色",
                    "evidence_quote": "蓝色",
                }
            ]
        },
        mode="add",
    ).proposals[0]
    assert proposal.operation.value == "add"


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
