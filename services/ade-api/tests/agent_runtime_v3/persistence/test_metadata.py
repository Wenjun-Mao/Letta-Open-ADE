from __future__ import annotations

from pgvector.sqlalchemy import Vector

from ade_api.features.agent_runtime_v3.persistence.metadata import (
    METADATA,
    SCHEMA_NAME,
    conversation_summaries,
    memory_embeddings,
    run_attempts,
)
from ade_api.features.agent_runtime_v3.persistence.validation import (
    validate_metadata_contract,
)


EXPECTED_TABLES = {
    "agent_definition_versions",
    "conversation_leases",
    "conversation_summaries",
    "conversations",
    "memory_embeddings",
    "memory_entities",
    "memory_facts",
    "memory_revision_predecessors",
    "memory_revision_sources",
    "memory_revisions",
    "memory_subjects",
    "messages",
    "outbox",
    "run_attempts",
    "run_events",
    "runs",
    "summary_sources",
    "workspaces",
}


def test_metadata_has_the_complete_ade_runtime_table_set() -> None:
    assert {table.name for table in METADATA.tables.values()} == EXPECTED_TABLES
    assert {table.schema for table in METADATA.tables.values()} == {SCHEMA_NAME}
    assert isinstance(memory_embeddings.c.embedding.type, Vector)
    assert run_attempts.c.timeout_seconds.type.precision == 8
    assert run_attempts.c.timeout_seconds.type.scale == 3


def test_metadata_uses_named_constraints_and_indexes() -> None:
    validate_metadata_contract()


def test_active_state_guards_are_partial_unique_indexes() -> None:
    indexes = {
        index.name: index
        for table in METADATA.tables.values()
        for index in table.indexes
    }
    assert set(indexes) >= {
        "uq_conversation_leases_active_conversation",
        "uq_memory_facts_active_subject_key",
        "uq_runs_active_conversation",
    }
    assert all(index.unique for index in indexes.values())
    assert all(
        index.dialect_options["postgresql"]["where"] is not None
        for index in indexes.values()
    )


def test_conversation_summaries_persist_generation_provenance() -> None:
    assert set(conversation_summaries.c.keys()) >= {
        "previous_summary_id",
        "model_key",
        "provider_request_id",
        "prompt_sha256",
        "input_sha256",
    }
