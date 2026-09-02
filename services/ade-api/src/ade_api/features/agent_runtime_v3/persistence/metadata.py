"""SQLAlchemy Core metadata for ADE-native runtime persistence.

This module intentionally defines tables only. Runtime code must use reviewed
Alembic migrations rather than ``MetaData.create_all``.
"""

from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID


SCHEMA_NAME = "ade"
METADATA = MetaData(
    schema=SCHEMA_NAME,
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    },
)

UUID_ID = UUID(as_uuid=False)
TIMESTAMP = DateTime(timezone=True)
CREATED_AT = text("CURRENT_TIMESTAMP")


workspaces = Table(
    "workspaces",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("workspace_key", String(120), nullable=False),
    Column("name", String(200), nullable=False),
    Column("state_generation", Integer, nullable=False, server_default=text("1")),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("updated_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_workspaces"),
    UniqueConstraint("workspace_key", name="uq_workspaces_workspace_key"),
    CheckConstraint(
        "state_generation > 0", name="ck_workspaces_positive_state_generation"
    ),
)

agent_definitions = Table(
    "agent_definitions",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("workspace_id", UUID_ID, nullable=False),
    Column("definition_key", String(64), nullable=False),
    Column("name", String(120), nullable=False),
    Column("purpose", String(32), nullable=False, server_default=text("'development'")),
    Column("current_version_id", UUID_ID, nullable=True),
    Column("archived_at", TIMESTAMP, nullable=True),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("updated_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_agent_definitions"),
    ForeignKeyConstraint(
        ["workspace_id"],
        [f"{SCHEMA_NAME}.workspaces.id"],
        name="fk_agent_definitions_workspace",
    ),
    ForeignKeyConstraint(
        ["current_version_id"],
        [f"{SCHEMA_NAME}.agent_definition_versions.id"],
        name="fk_agent_definitions_current_version",
        use_alter=True,
    ),
    UniqueConstraint("id", "workspace_id", name="uq_agent_definitions_id_workspace"),
    UniqueConstraint(
        "workspace_id", "definition_key", name="uq_agent_definitions_workspace_key"
    ),
    CheckConstraint(
        "purpose IN ('development', 'agent_studio', 'evaluation', 'preview')",
        name="ck_agent_definitions_purpose",
    ),
)

agent_definition_versions = Table(
    "agent_definition_versions",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("workspace_id", UUID_ID, nullable=False),
    Column("agent_definition_id", UUID_ID, nullable=False),
    Column("definition_key", String(64), nullable=False),
    Column("version", Integer, nullable=False),
    Column("name", String(120), nullable=False),
    Column("model_key", String(300), nullable=False),
    Column("reviewer_model_key", String(300), nullable=False),
    Column("embedding_model_key", String(300), nullable=False),
    Column("prompt_key", String(128), nullable=False),
    Column("prompt_sha256", String(64), nullable=False),
    Column("prompt_content", Text, nullable=False),
    Column("persona_key", String(128), nullable=False),
    Column("persona_sha256", String(64), nullable=False),
    Column("persona_content", Text, nullable=False),
    Column("tool_names", JSONB, nullable=False),
    Column("memory_policy_version", String(128), nullable=False),
    Column("qualification_state", String(32), nullable=False),
    Column("deployment_snapshot", JSONB, nullable=False),
    Column("purpose", String(32), nullable=False, server_default=text("'development'")),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_agent_definition_versions"),
    ForeignKeyConstraint(
        ["workspace_id"],
        [f"{SCHEMA_NAME}.workspaces.id"],
        name="fk_definition_versions_workspace",
    ),
    ForeignKeyConstraint(
        ["agent_definition_id", "workspace_id"],
        [
            f"{SCHEMA_NAME}.agent_definitions.id",
            f"{SCHEMA_NAME}.agent_definitions.workspace_id",
        ],
        name="fk_definition_versions_definition_workspace",
    ),
    UniqueConstraint("id", "workspace_id", name="uq_definition_versions_id_workspace"),
    UniqueConstraint(
        "workspace_id",
        "definition_key",
        "version",
        name="uq_definition_versions_workspace_key_version",
    ),
    UniqueConstraint(
        "agent_definition_id",
        "version",
        name="uq_definition_versions_root_version",
    ),
    CheckConstraint("version > 0", name="ck_definition_versions_positive_version"),
    CheckConstraint(
        "purpose IN ('development', 'agent_studio', 'evaluation', 'preview')",
        name="ck_definition_versions_purpose",
    ),
)

memory_subjects = Table(
    "memory_subjects",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("workspace_id", UUID_ID, nullable=False),
    Column("external_key", String(200), nullable=False),
    Column("display_name", String(200), nullable=False, server_default=text("''")),
    Column("purpose", String(32), nullable=False, server_default=text("'development'")),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("archived_at", TIMESTAMP, nullable=True),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("updated_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_memory_subjects"),
    ForeignKeyConstraint(
        ["workspace_id"],
        [f"{SCHEMA_NAME}.workspaces.id"],
        name="fk_memory_subjects_workspace",
    ),
    UniqueConstraint("id", "workspace_id", name="uq_memory_subjects_id_workspace"),
    UniqueConstraint(
        "workspace_id", "external_key", name="uq_memory_subjects_workspace_external_key"
    ),
    CheckConstraint(
        "purpose IN ('development', 'agent_studio', 'evaluation', 'preview')",
        name="ck_memory_subjects_purpose",
    ),
    CheckConstraint("version > 0", name="ck_memory_subjects_positive_version"),
)
Index(
    "ix_memory_subjects_workspace_purpose_updated",
    memory_subjects.c.workspace_id,
    memory_subjects.c.purpose,
    memory_subjects.c.updated_at.desc(),
)

memory_entities = Table(
    "memory_entities",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("workspace_id", UUID_ID, nullable=False),
    Column("subject_id", UUID_ID, nullable=False),
    Column("kind", String(64), nullable=False),
    Column("label", String(200), nullable=False, server_default=text("''")),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_memory_entities"),
    ForeignKeyConstraint(
        ["subject_id", "workspace_id"],
        [
            f"{SCHEMA_NAME}.memory_subjects.id",
            f"{SCHEMA_NAME}.memory_subjects.workspace_id",
        ],
        name="fk_memory_entities_subject_workspace",
    ),
    UniqueConstraint("id", "workspace_id", name="uq_memory_entities_id_workspace"),
)

conversations = Table(
    "conversations",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("workspace_id", UUID_ID, nullable=False),
    Column("agent_definition_version_id", UUID_ID, nullable=False),
    Column("memory_subject_id", UUID_ID, nullable=False),
    Column("title", String(120), nullable=False, server_default=text("'Conversation'")),
    Column("purpose", String(32), nullable=False, server_default=text("'development'")),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("archived_at", TIMESTAMP, nullable=True),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_conversations"),
    ForeignKeyConstraint(
        ["agent_definition_version_id", "workspace_id"],
        [
            f"{SCHEMA_NAME}.agent_definition_versions.id",
            f"{SCHEMA_NAME}.agent_definition_versions.workspace_id",
        ],
        name="fk_conversations_definition_workspace",
    ),
    ForeignKeyConstraint(
        ["memory_subject_id", "workspace_id"],
        [
            f"{SCHEMA_NAME}.memory_subjects.id",
            f"{SCHEMA_NAME}.memory_subjects.workspace_id",
        ],
        name="fk_conversations_subject_workspace",
    ),
    UniqueConstraint("id", "workspace_id", name="uq_conversations_id_workspace"),
    CheckConstraint("version > 0", name="ck_conversations_positive_version"),
    CheckConstraint(
        "purpose IN ('development', 'agent_studio', 'evaluation', 'preview')",
        name="ck_conversations_purpose",
    ),
)
Index(
    "ix_conversations_workspace_purpose_created",
    conversations.c.workspace_id,
    conversations.c.purpose,
    conversations.c.created_at.desc(),
)

agent_studio_reset_receipts = Table(
    "agent_studio_reset_receipts",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("workspace_id", UUID_ID, nullable=False),
    Column("idempotency_key", String(200), nullable=False),
    Column("request_sha256", String(64), nullable=False),
    Column("reset_generation", Integer, nullable=False),
    Column("deleted_counts", JSONB, nullable=False),
    Column("reset_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_agent_studio_reset_receipts"),
    ForeignKeyConstraint(
        ["workspace_id"],
        [f"{SCHEMA_NAME}.workspaces.id"],
        name="fk_agent_studio_reset_receipts_workspace",
    ),
    UniqueConstraint(
        "workspace_id",
        "idempotency_key",
        name="uq_agent_studio_reset_receipts_workspace_key",
    ),
    CheckConstraint(
        "char_length(request_sha256) = 64",
        name="ck_agent_studio_reset_receipts_request_sha256",
    ),
    CheckConstraint(
        "reset_generation > 1",
        name="ck_agent_studio_reset_receipts_generation",
    ),
)

runs = Table(
    "runs",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("workspace_id", UUID_ID, nullable=False),
    Column("conversation_id", UUID_ID, nullable=False),
    Column("idempotency_key", String(200), nullable=False),
    Column("request_hash", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("qualification_state", String(32), nullable=False),
    Column("timeout_seconds", Numeric(8, 3), nullable=False),
    Column("retry_count", Integer, nullable=False),
    Column("accepted_conversation_version", Integer, nullable=False),
    Column("attempt_count", Integer, nullable=False, server_default=text("0")),
    Column("cancellation_requested_at", TIMESTAMP, nullable=True),
    Column("error_code", String(128), nullable=True),
    Column("error_message", Text, nullable=True),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("started_at", TIMESTAMP, nullable=True),
    Column("finished_at", TIMESTAMP, nullable=True),
    PrimaryKeyConstraint("id", name="pk_runs"),
    ForeignKeyConstraint(
        ["conversation_id", "workspace_id"],
        [
            f"{SCHEMA_NAME}.conversations.id",
            f"{SCHEMA_NAME}.conversations.workspace_id",
        ],
        name="fk_runs_conversation_workspace",
    ),
    UniqueConstraint(
        "conversation_id", "idempotency_key", name="uq_runs_conversation_idempotency"
    ),
    CheckConstraint("attempt_count >= 0", name="ck_runs_nonnegative_attempt_count"),
    CheckConstraint("retry_count BETWEEN 0 AND 5", name="ck_runs_retry_count"),
    CheckConstraint("timeout_seconds > 0", name="ck_runs_positive_timeout"),
    CheckConstraint(
        "accepted_conversation_version > 0",
        name="ck_runs_positive_conversation_version",
    ),
)
Index(
    "uq_runs_active_conversation",
    runs.c.conversation_id,
    unique=True,
    postgresql_where=runs.c.status.in_(("pending", "running")),
)

messages = Table(
    "messages",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("workspace_id", UUID_ID, nullable=False),
    Column("conversation_id", UUID_ID, nullable=False),
    Column("sequence", Integer, nullable=False),
    Column("role", String(32), nullable=False),
    Column("content", Text, nullable=False),
    Column("content_sha256", String(64), nullable=False),
    Column("run_id", UUID_ID, nullable=True),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_messages"),
    ForeignKeyConstraint(
        ["conversation_id", "workspace_id"],
        [
            f"{SCHEMA_NAME}.conversations.id",
            f"{SCHEMA_NAME}.conversations.workspace_id",
        ],
        name="fk_messages_conversation_workspace",
    ),
    ForeignKeyConstraint(
        ["run_id"], [f"{SCHEMA_NAME}.runs.id"], name="fk_messages_run"
    ),
    UniqueConstraint(
        "conversation_id", "sequence", name="uq_messages_conversation_sequence"
    ),
    CheckConstraint("sequence > 0", name="ck_messages_positive_sequence"),
)

run_attempts = Table(
    "run_attempts",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("run_id", UUID_ID, nullable=False),
    Column("attempt_number", Integer, nullable=False),
    Column("status", String(32), nullable=False),
    Column("timeout_seconds", Numeric(8, 3), nullable=False),
    Column(
        "provider_outcome", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    ),
    Column("started_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("finished_at", TIMESTAMP, nullable=True),
    PrimaryKeyConstraint("id", name="pk_run_attempts"),
    ForeignKeyConstraint(
        ["run_id"], [f"{SCHEMA_NAME}.runs.id"], name="fk_run_attempts_run"
    ),
    UniqueConstraint("run_id", "attempt_number", name="uq_run_attempts_run_number"),
    CheckConstraint("attempt_number > 0", name="ck_run_attempts_positive_number"),
    CheckConstraint("timeout_seconds > 0", name="ck_run_attempts_positive_timeout"),
)

run_events = Table(
    "run_events",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("run_id", UUID_ID, nullable=False),
    Column("sequence", Integer, nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("event_type", String(128), nullable=False),
    Column("attempt", Integer, nullable=True),
    Column("correlation_id", String(128), nullable=False),
    Column("causation_id", String(128), nullable=True),
    Column("visibility", String(32), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("occurred_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_run_events"),
    ForeignKeyConstraint(
        ["run_id"], [f"{SCHEMA_NAME}.runs.id"], name="fk_run_events_run"
    ),
    UniqueConstraint("run_id", "sequence", name="uq_run_events_run_sequence"),
    CheckConstraint("sequence > 0", name="ck_run_events_positive_sequence"),
    CheckConstraint("schema_version > 0", name="ck_run_events_positive_schema_version"),
)

outbox = Table(
    "outbox",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("run_id", UUID_ID, nullable=False),
    Column("run_event_id", UUID_ID, nullable=False),
    Column("topic", String(128), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("published_at", TIMESTAMP, nullable=True),
    PrimaryKeyConstraint("id", name="pk_outbox"),
    ForeignKeyConstraint(["run_id"], [f"{SCHEMA_NAME}.runs.id"], name="fk_outbox_run"),
    ForeignKeyConstraint(
        ["run_event_id"], [f"{SCHEMA_NAME}.run_events.id"], name="fk_outbox_run_event"
    ),
    UniqueConstraint("run_event_id", name="uq_outbox_run_event"),
)

memory_facts = Table(
    "memory_facts",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("workspace_id", UUID_ID, nullable=False),
    Column("subject_id", UUID_ID, nullable=False),
    Column("entity_id", UUID_ID, nullable=False),
    Column("normalized_key", String(300), nullable=False),
    Column("fact_type", String(128), nullable=False),
    Column("qualifier", String(200), nullable=True),
    Column("value", JSONB, nullable=True),
    Column("status", String(32), nullable=False),
    Column("version", Integer, nullable=False),
    Column("current_revision_id", UUID_ID, nullable=True),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("updated_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_memory_facts"),
    ForeignKeyConstraint(
        ["subject_id", "workspace_id"],
        [
            f"{SCHEMA_NAME}.memory_subjects.id",
            f"{SCHEMA_NAME}.memory_subjects.workspace_id",
        ],
        name="fk_memory_facts_subject_workspace",
    ),
    ForeignKeyConstraint(
        ["entity_id", "workspace_id"],
        [
            f"{SCHEMA_NAME}.memory_entities.id",
            f"{SCHEMA_NAME}.memory_entities.workspace_id",
        ],
        name="fk_memory_facts_entity_workspace",
    ),
    ForeignKeyConstraint(
        ["current_revision_id"],
        [f"{SCHEMA_NAME}.memory_revisions.id"],
        name="fk_memory_facts_current_revision",
        use_alter=True,
    ),
    UniqueConstraint("id", "workspace_id", name="uq_memory_facts_id_workspace"),
    CheckConstraint("version > 0", name="ck_memory_facts_positive_version"),
)
Index(
    "uq_memory_facts_active_subject_key",
    memory_facts.c.subject_id,
    memory_facts.c.normalized_key,
    unique=True,
    postgresql_where=memory_facts.c.status == "active",
)

memory_revisions = Table(
    "memory_revisions",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("fact_id", UUID_ID, nullable=False),
    Column("workspace_id", UUID_ID, nullable=False),
    Column("subject_id", UUID_ID, nullable=False),
    Column("operation", String(32), nullable=False),
    Column("fact_version", Integer, nullable=False),
    Column("value", JSONB, nullable=True),
    Column("run_id", UUID_ID, nullable=False),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_memory_revisions"),
    ForeignKeyConstraint(
        ["fact_id", "workspace_id"],
        [f"{SCHEMA_NAME}.memory_facts.id", f"{SCHEMA_NAME}.memory_facts.workspace_id"],
        name="fk_memory_revisions_fact_workspace",
    ),
    ForeignKeyConstraint(
        ["subject_id", "workspace_id"],
        [
            f"{SCHEMA_NAME}.memory_subjects.id",
            f"{SCHEMA_NAME}.memory_subjects.workspace_id",
        ],
        name="fk_memory_revisions_subject_workspace",
    ),
    ForeignKeyConstraint(
        ["run_id"], [f"{SCHEMA_NAME}.runs.id"], name="fk_memory_revisions_run"
    ),
    UniqueConstraint(
        "fact_id", "fact_version", name="uq_memory_revisions_fact_version"
    ),
    CheckConstraint("fact_version > 0", name="ck_memory_revisions_positive_version"),
)

memory_revision_predecessors = Table(
    "memory_revision_predecessors",
    METADATA,
    Column("revision_id", UUID_ID, nullable=False),
    Column("predecessor_revision_id", UUID_ID, nullable=False),
    PrimaryKeyConstraint(
        "revision_id", "predecessor_revision_id", name="pk_memory_revision_predecessors"
    ),
    ForeignKeyConstraint(
        ["revision_id"],
        [f"{SCHEMA_NAME}.memory_revisions.id"],
        name="fk_revision_predecessors_revision",
    ),
    ForeignKeyConstraint(
        ["predecessor_revision_id"],
        [f"{SCHEMA_NAME}.memory_revisions.id"],
        name="fk_revision_predecessors_predecessor",
    ),
)

memory_revision_sources = Table(
    "memory_revision_sources",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("revision_id", UUID_ID, nullable=False),
    Column("message_id", UUID_ID, nullable=False),
    Column("start_char", Integer, nullable=False),
    Column("end_char", Integer, nullable=False),
    Column("quote", Text, nullable=False),
    Column("message_sha256", String(64), nullable=False),
    PrimaryKeyConstraint("id", name="pk_memory_revision_sources"),
    ForeignKeyConstraint(
        ["revision_id"],
        [f"{SCHEMA_NAME}.memory_revisions.id"],
        name="fk_revision_sources_revision",
    ),
    ForeignKeyConstraint(
        ["message_id"],
        [f"{SCHEMA_NAME}.messages.id"],
        name="fk_revision_sources_message",
    ),
    UniqueConstraint(
        "revision_id",
        "message_id",
        "start_char",
        "end_char",
        name="uq_revision_sources_span",
    ),
    CheckConstraint("start_char >= 0", name="ck_revision_sources_nonnegative_start"),
    CheckConstraint("end_char > start_char", name="ck_revision_sources_positive_span"),
)

memory_embeddings = Table(
    "memory_embeddings",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("workspace_id", UUID_ID, nullable=False),
    Column("subject_id", UUID_ID, nullable=False),
    Column("fact_id", UUID_ID, nullable=False),
    Column("revision_id", UUID_ID, nullable=False),
    Column("model_fingerprint", String(512), nullable=False),
    Column("dimensions", Integer, nullable=False),
    Column("normalized", Boolean, nullable=False),
    Column("retrieval_policy_version", String(128), nullable=False),
    Column("embedding", Vector(), nullable=False),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_memory_embeddings"),
    ForeignKeyConstraint(
        ["subject_id", "workspace_id"],
        [
            f"{SCHEMA_NAME}.memory_subjects.id",
            f"{SCHEMA_NAME}.memory_subjects.workspace_id",
        ],
        name="fk_memory_embeddings_subject_workspace",
    ),
    ForeignKeyConstraint(
        ["fact_id", "workspace_id"],
        [f"{SCHEMA_NAME}.memory_facts.id", f"{SCHEMA_NAME}.memory_facts.workspace_id"],
        name="fk_memory_embeddings_fact_workspace",
    ),
    ForeignKeyConstraint(
        ["revision_id"],
        [f"{SCHEMA_NAME}.memory_revisions.id"],
        name="fk_memory_embeddings_revision",
    ),
    UniqueConstraint(
        "fact_id",
        "revision_id",
        "model_fingerprint",
        "retrieval_policy_version",
        name="uq_memory_embeddings_revision_model_policy",
    ),
    CheckConstraint("dimensions > 0", name="ck_memory_embeddings_positive_dimensions"),
)

conversation_summaries = Table(
    "conversation_summaries",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("conversation_id", UUID_ID, nullable=False),
    Column("version", Integer, nullable=False),
    Column("through_sequence", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("run_id", UUID_ID, nullable=False),
    Column("previous_summary_id", UUID_ID, nullable=True),
    Column("model_key", String(300), nullable=False),
    Column("model_fingerprint", String(64), nullable=False),
    Column("provider_request_id", String(512), nullable=True),
    Column("content_sha256", String(64), nullable=False),
    Column("prompt_sha256", String(64), nullable=False),
    Column("input_sha256", String(64), nullable=False),
    Column("policy_sha256", String(64), nullable=False),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_conversation_summaries"),
    ForeignKeyConstraint(
        ["conversation_id"],
        [f"{SCHEMA_NAME}.conversations.id"],
        name="fk_conversation_summaries_conversation",
    ),
    ForeignKeyConstraint(
        ["run_id"], [f"{SCHEMA_NAME}.runs.id"], name="fk_conversation_summaries_run"
    ),
    ForeignKeyConstraint(
        ["previous_summary_id"],
        [f"{SCHEMA_NAME}.conversation_summaries.id"],
        name="fk_conversation_summaries_previous_summary",
    ),
    UniqueConstraint(
        "conversation_id",
        "version",
        name="uq_conversation_summaries_conversation_version",
    ),
    CheckConstraint("version > 0", name="ck_conversation_summaries_positive_version"),
    CheckConstraint(
        "through_sequence > 0",
        name="ck_conversation_summaries_positive_through_sequence",
    ),
)

summary_sources = Table(
    "summary_sources",
    METADATA,
    Column("summary_id", UUID_ID, nullable=False),
    Column("message_id", UUID_ID, nullable=False),
    PrimaryKeyConstraint("summary_id", "message_id", name="pk_summary_sources"),
    ForeignKeyConstraint(
        ["summary_id"],
        [f"{SCHEMA_NAME}.conversation_summaries.id"],
        name="fk_summary_sources_summary",
    ),
    ForeignKeyConstraint(
        ["message_id"],
        [f"{SCHEMA_NAME}.messages.id"],
        name="fk_summary_sources_message",
    ),
)

conversation_leases = Table(
    "conversation_leases",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("conversation_id", UUID_ID, nullable=False),
    Column("run_id", UUID_ID, nullable=False),
    Column("lease_token", UUID_ID, nullable=False),
    Column("holder_id", String(128), nullable=False),
    Column("acquired_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("heartbeat_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("expires_at", TIMESTAMP, nullable=False),
    Column("released_at", TIMESTAMP, nullable=True),
    PrimaryKeyConstraint("id", name="pk_conversation_leases"),
    ForeignKeyConstraint(
        ["conversation_id"],
        [f"{SCHEMA_NAME}.conversations.id"],
        name="fk_conversation_leases_conversation",
    ),
    ForeignKeyConstraint(
        ["run_id"], [f"{SCHEMA_NAME}.runs.id"], name="fk_conversation_leases_run"
    ),
    UniqueConstraint("lease_token", name="uq_conversation_leases_token"),
)
Index(
    "uq_conversation_leases_active_conversation",
    conversation_leases.c.conversation_id,
    unique=True,
    postgresql_where=conversation_leases.c.released_at.is_(None),
)

worker_instances = Table(
    "worker_instances",
    METADATA,
    Column("instance_id", UUID_ID, nullable=False),
    Column("worker_id", String(128), nullable=False),
    Column("state", String(16), nullable=False),
    Column("contract_version", String(128), nullable=False),
    Column("compatibility_fingerprint", String(64), nullable=False),
    Column("runtime_version", String(64), nullable=False),
    Column("source_revision", String(128), nullable=False),
    Column("source_dirty", Boolean, nullable=False),
    Column("source_fingerprint", String(64), nullable=False),
    Column("started_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("heartbeat_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("stopped_at", TIMESTAMP, nullable=True),
    PrimaryKeyConstraint("instance_id", name="pk_worker_instances"),
    CheckConstraint(
        "state IN ('ready', 'draining', 'stopped')",
        name="ck_worker_instances_state",
    ),
    CheckConstraint(
        "char_length(compatibility_fingerprint) = 64",
        name="ck_worker_instances_fingerprint_length",
    ),
    CheckConstraint(
        "source_fingerprint = 'unknown' OR char_length(source_fingerprint) = 64",
        name="ck_worker_instances_source_fingerprint",
    ),
)
Index(
    "ix_worker_instances_health",
    worker_instances.c.compatibility_fingerprint,
    worker_instances.c.state,
    worker_instances.c.heartbeat_at,
)


ALL_TABLES = tuple(METADATA.tables.values())
