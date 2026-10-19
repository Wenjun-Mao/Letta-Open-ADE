"""Versioned narrative summaries and their immutable raw-message provenance."""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKeyConstraint,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
)


from .metadata_schema import CREATED_AT, METADATA, SCHEMA_NAME, TIMESTAMP, UUID_ID


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
