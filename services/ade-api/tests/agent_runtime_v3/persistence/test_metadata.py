from __future__ import annotations

from pgvector.sqlalchemy import Vector

from ade_api.features.agent_runtime_v3.persistence.metadata import (
    METADATA,
    SCHEMA_NAME,
    conversation_summaries,
    memory_embeddings,
    run_attempts,
    runs,
    worker_instances,
)
from ade_api.features.agent_runtime_v3.persistence.validation import (
    validate_metadata_contract,
)


EXPECTED_TABLES = {
    "agent_definitions",
    "agent_definition_versions",
    "agent_studio_reset_receipts",
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
    "worker_instances",
}


def test_metadata_has_the_complete_ade_runtime_table_set() -> None:
    assert {table.name for table in METADATA.tables.values()} == EXPECTED_TABLES
    assert {table.schema for table in METADATA.tables.values()} == {SCHEMA_NAME}
    assert isinstance(memory_embeddings.c.embedding.type, Vector)
    assert run_attempts.c.timeout_seconds.type.precision == 8
    assert run_attempts.c.timeout_seconds.type.scale == 3
    assert runs.c.accepted_runtime_mode.server_default is not None


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
    active_guard_names = {
        "uq_conversation_leases_active_conversation",
        "uq_memory_facts_active_subject_key",
        "uq_runs_active_conversation",
    }
    assert all(indexes[name].unique for name in active_guard_names)
    assert all(
        indexes[name].dialect_options["postgresql"]["where"] is not None
        for name in active_guard_names
    )


def test_worker_health_index_covers_fingerprint_state_and_heartbeat() -> None:
    health_index = next(
        index
        for index in worker_instances.indexes
        if index.name == "ix_worker_instances_health"
    )
    assert [column.name for column in health_index.columns] == [
        "compatibility_fingerprint",
        "state",
        "heartbeat_at",
    ]


def test_conversation_summaries_persist_generation_provenance() -> None:
    assert set(conversation_summaries.c.keys()) >= {
        "previous_summary_id",
        "model_key",
        "model_fingerprint",
        "provider_request_id",
        "content_sha256",
        "prompt_sha256",
        "input_sha256",
        "policy_sha256",
    }
