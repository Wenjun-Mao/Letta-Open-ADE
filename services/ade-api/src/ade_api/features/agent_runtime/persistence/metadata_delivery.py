"""Concrete Hindsight ownership, immutable delivery intent and retry receipts."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from .metadata_schema import CREATED_AT, METADATA, TIMESTAMP, UUID_ID


memory_relationships = Table(
    "memory_relationships",
    METADATA,
    Column("bank_id", String(128), nullable=False),
    Column("workspace_id", UUID_ID, nullable=False),
    Column("subject_id", UUID_ID, nullable=False),
    Column("character_root_id", UUID_ID, nullable=False),
    Column("configuration_sha256", String(64), nullable=False),
    Column("configuration", JSONB, nullable=False),
    Column("state", String(32), nullable=False, server_default=text("'new'")),
    Column("next_sequence", BigInteger, nullable=False, server_default=text("1")),
    Column("initialization_token", UUID_ID, nullable=True),
    Column("initialization_expires_at", TIMESTAMP, nullable=True),
    Column("initialized_at", TIMESTAMP, nullable=True),
    Column("last_error_code", String(128), nullable=True),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("bank_id", name="pk_memory_relationships"),
    UniqueConstraint(
        "workspace_id",
        "subject_id",
        "character_root_id",
        name="uq_memory_relationships_scope",
    ),
    UniqueConstraint(
        "bank_id", "workspace_id", name="uq_memory_relationships_bank_workspace"
    ),
    UniqueConstraint(
        "bank_id",
        "configuration_sha256",
        name="uq_memory_relationships_bank_configuration",
    ),
    ForeignKeyConstraint(
        ["subject_id", "workspace_id"],
        ["ade.memory_subjects.id", "ade.memory_subjects.workspace_id"],
        name="fk_memory_relationships_subject_workspace",
    ),
    ForeignKeyConstraint(
        ["character_root_id", "workspace_id"],
        ["ade.agent_definitions.id", "ade.agent_definitions.workspace_id"],
        name="fk_memory_relationships_character_workspace",
    ),
    CheckConstraint(
        "state IN ('new','initializing','ready','failed','missing')",
        name="ck_memory_relationships_state",
    ),
    CheckConstraint("next_sequence > 0", name="ck_memory_relationships_sequence"),
    CheckConstraint(
        "length(configuration_sha256) = 64",
        name="ck_memory_relationships_configuration_hash",
    ),
    CheckConstraint(
        "(state = 'initializing') = (initialization_token IS NOT NULL AND initialization_expires_at IS NOT NULL)",
        name="ck_memory_relationships_initialization_lease",
    ),
    CheckConstraint(
        "(initialization_token IS NULL) = (initialization_expires_at IS NULL)",
        name="ck_memory_relationships_lease_pair",
    ),
    CheckConstraint(
        "state <> 'ready' OR initialized_at IS NOT NULL",
        name="ck_memory_relationships_ready",
    ),
)

memory_deliveries = Table(
    "memory_deliveries",
    METADATA,
    Column("operation_id", UUID_ID, nullable=False),
    Column("workspace_id", UUID_ID, nullable=False),
    Column("bank_id", String(128), nullable=False),
    Column("configuration_sha256", String(64), nullable=False),
    Column("message_id", UUID_ID, nullable=False),
    Column("relationship_sequence", BigInteger, nullable=False),
    Column("document_id", String(200), nullable=False),
    Column("payload", LargeBinary, nullable=False),
    Column("payload_sha256", String(64), nullable=False),
    Column("status", String(32), nullable=False, server_default=text("'queued'")),
    Column("attempt_count", Integer, nullable=False, server_default=text("0")),
    Column("check_count", Integer, nullable=False, server_default=text("0")),
    Column("retry_requested", Boolean, nullable=False, server_default=text("false")),
    Column("consecutive_errors", Integer, nullable=False, server_default=text("0")),
    Column("last_error_code", String(128), nullable=True),
    Column("native_status", String(32), nullable=True),
    Column(
        "native_progress", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    ),
    Column("accepted_at", TIMESTAMP, nullable=True),
    Column("accepted_via", String(32), nullable=True),
    Column("retained_at", TIMESTAMP, nullable=True),
    Column("first_dispatch_at", TIMESTAMP, nullable=True),
    Column("last_checked_at", TIMESTAMP, nullable=True),
    Column("lease_token", UUID_ID, nullable=True),
    Column("lease_expires_at", TIMESTAMP, nullable=True),
    Column("next_attempt_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("updated_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("operation_id", name="pk_memory_deliveries"),
    UniqueConstraint("message_id", name="uq_memory_deliveries_message"),
    UniqueConstraint(
        "bank_id", "relationship_sequence", name="uq_memory_deliveries_order"
    ),
    UniqueConstraint("bank_id", "document_id", name="uq_memory_deliveries_document"),
    ForeignKeyConstraint(
        ["bank_id", "workspace_id"],
        ["ade.memory_relationships.bank_id", "ade.memory_relationships.workspace_id"],
        name="fk_memory_deliveries_bank_workspace",
    ),
    ForeignKeyConstraint(
        ["bank_id", "configuration_sha256"],
        [
            "ade.memory_relationships.bank_id",
            "ade.memory_relationships.configuration_sha256",
        ],
        name="fk_memory_deliveries_bank_configuration",
    ),
    ForeignKeyConstraint(
        ["message_id", "workspace_id"],
        ["ade.messages.id", "ade.messages.workspace_id"],
        name="fk_memory_deliveries_message_workspace",
    ),
    CheckConstraint(
        "status IN ('queued','submitting','processing','retained','failed','uncertain')",
        name="ck_memory_deliveries_status",
    ),
    CheckConstraint("relationship_sequence > 0", name="ck_memory_deliveries_sequence"),
    CheckConstraint(
        "attempt_count >= 0 AND check_count >= 0 AND consecutive_errors >= 0",
        name="ck_memory_deliveries_attempts",
    ),
    CheckConstraint(
        "payload_sha256 = encode(sha256(payload),'hex')",
        name="ck_memory_deliveries_payload_hash",
    ),
    CheckConstraint(
        "(lease_token IS NULL) = (lease_expires_at IS NULL)",
        name="ck_memory_deliveries_lease",
    ),
    CheckConstraint(
        "(accepted_at IS NULL) = (accepted_via IS NULL) AND (accepted_via IS NULL OR accepted_via IN ('response','reconciliation'))",
        name="ck_memory_deliveries_acknowledgement",
    ),
    CheckConstraint(
        "status <> 'retained' OR (retained_at IS NOT NULL AND accepted_at IS NOT NULL)",
        name="ck_memory_deliveries_retained",
    ),
    CheckConstraint(
        "status NOT IN ('retained','failed','uncertain') OR lease_token IS NULL",
        name="ck_memory_deliveries_terminal_lease",
    ),
)
Index(
    "ix_memory_deliveries_dispatch",
    memory_deliveries.c.workspace_id,
    memory_deliveries.c.next_attempt_at,
    memory_deliveries.c.relationship_sequence,
)

run_retry_requests = Table(
    "run_retry_requests",
    METADATA,
    Column("run_id", UUID_ID, nullable=False),
    Column("idempotency_key", String(200), nullable=False),
    Column("request_sha256", String(64), nullable=False),
    Column("expected_attempt_count", Integer, nullable=False),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("run_id", "idempotency_key", name="pk_run_retry_requests"),
    UniqueConstraint(
        "run_id", "expected_attempt_count", name="uq_run_retry_requests_attempt"
    ),
    ForeignKeyConstraint(["run_id"], ["ade.runs.id"], name="fk_run_retry_requests_run"),
    CheckConstraint("expected_attempt_count > 0", name="ck_run_retry_requests_attempt"),
)
