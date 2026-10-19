"""Run, committed message, event and worker-lease tables."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB


from .metadata_schema import CREATED_AT, METADATA, SCHEMA_NAME, TIMESTAMP, UUID_ID


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
    Column(
        "accepted_runtime_mode",
        String(32),
        nullable=False,
        server_default=text("'development'"),
    ),
    Column("timeout_seconds", Numeric(8, 3), nullable=False),
    Column("retry_count", Integer, nullable=False),
    Column("accepted_conversation_version", Integer, nullable=False),
    Column(
        "accepted_memory_generation",
        BigInteger,
        nullable=True,
        server_default=text("1"),
    ),
    Column("attempt_count", Integer, nullable=False, server_default=text("0")),
    Column("cancellation_requested_at", TIMESTAMP, nullable=True),
    Column("error_code", String(128), nullable=True),
    Column("error_message", Text, nullable=True),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("started_at", TIMESTAMP, nullable=True),
    Column("finished_at", TIMESTAMP, nullable=True),
    Column("paused_at", TIMESTAMP, nullable=True),
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
        "accepted_runtime_mode IN ('development', 'release')",
        name="ck_runs_accepted_runtime_mode",
    ),
    CheckConstraint(
        "accepted_conversation_version > 0",
        name="ck_runs_positive_conversation_version",
    ),
    CheckConstraint(
        "accepted_memory_generation > 0", name="ck_runs_positive_memory_generation"
    ),
)
Index(
    "uq_runs_active_conversation",
    runs.c.conversation_id,
    unique=True,
    postgresql_where=runs.c.status.in_(("pending", "running", "paused")),
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
    UniqueConstraint("id", "workspace_id", name="uq_messages_id_workspace"),
    UniqueConstraint("run_id", "role", name="uq_messages_run_role"),
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
