"""Retained native schema for historical data; not a learned-memory execution path."""

from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKeyConstraint,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB


from .metadata_schema import CREATED_AT, METADATA, SCHEMA_NAME, TIMESTAMP, UUID_ID


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

memory_actions = Table(
    "memory_actions",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("workspace_id", UUID_ID, nullable=False),
    Column("subject_id", UUID_ID, nullable=False),
    Column("idempotency_key", String(200), nullable=False),
    Column("request_sha256", String(64), nullable=False),
    Column("expected_memory_generation", BigInteger, nullable=False),
    Column("resulting_memory_generation", BigInteger, nullable=False),
    Column("targets", JSONB, nullable=False),
    Column("revision_ids", JSONB, nullable=False),
    Column("outcome", String(32), nullable=False),
    Column("actor_label", String(200), nullable=False),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_memory_actions"),
    ForeignKeyConstraint(
        ["subject_id", "workspace_id"],
        [
            f"{SCHEMA_NAME}.memory_subjects.id",
            f"{SCHEMA_NAME}.memory_subjects.workspace_id",
        ],
        name="fk_memory_actions_subject_workspace",
    ),
    UniqueConstraint(
        "subject_id", "idempotency_key", name="uq_memory_actions_subject_key"
    ),
    CheckConstraint("char_length(request_sha256) = 64", name="ck_memory_actions_hash"),
    CheckConstraint(
        "expected_memory_generation > 0 AND resulting_memory_generation > expected_memory_generation",
        name="ck_memory_actions_generations",
    ),
    CheckConstraint("outcome IN ('committed')", name="ck_memory_actions_outcome"),
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
    Column(
        "assertion_schema_version", Integer, nullable=False, server_default=text("1")
    ),
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
    CheckConstraint(
        "assertion_schema_version IN (1, 2)",
        name="ck_memory_facts_assertion_schema_version",
    ),
    CheckConstraint(
        "status IN ('active', 'inactive', 'forgotten')",
        name="ck_memory_facts_lifecycle_status",
    ),
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
    Column("run_id", UUID_ID, nullable=True),
    Column("action_id", UUID_ID, nullable=True),
    Column("reason", String(32), nullable=True),
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
    ForeignKeyConstraint(
        ["action_id"],
        [f"{SCHEMA_NAME}.memory_actions.id"],
        name="fk_memory_revisions_action",
    ),
    UniqueConstraint(
        "fact_id", "fact_version", name="uq_memory_revisions_fact_version"
    ),
    CheckConstraint("fact_version > 0", name="ck_memory_revisions_positive_version"),
    CheckConstraint(
        "(run_id IS NOT NULL) <> (action_id IS NOT NULL)",
        name="ck_memory_revisions_one_origin",
    ),
    CheckConstraint(
        "reason IS NULL OR reason IN ('enrich', 'supersede', 'correct', 'unspecified', 'ended', 'invalidated', 'reasserted', 'forgotten')",
        name="ck_memory_revisions_reason",
    ),
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
    Column(
        "authority_role",
        String(32),
        nullable=False,
        server_default=text("'user_assertion'"),
    ),
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
    CheckConstraint(
        "authority_role IN ('user_assertion', 'user_endorsement', 'assistant_referent', 'user_resolution', 'user_antecedent')",
        name="ck_memory_revision_sources_authority_role",
    ),
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
