"""Workspace, immutable characterization and conversation ownership tables."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
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


workspaces = Table(
    "workspaces",
    METADATA,
    Column("id", UUID_ID, nullable=False),
    Column("workspace_key", String(120), nullable=False),
    Column("name", String(200), nullable=False),
    Column(
        "memory_backend", String(32), nullable=False, server_default=text("'incumbent'")
    ),
    Column("state_generation", Integer, nullable=False, server_default=text("1")),
    Column("created_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    Column("updated_at", TIMESTAMP, nullable=False, server_default=CREATED_AT),
    PrimaryKeyConstraint("id", name="pk_workspaces"),
    UniqueConstraint("workspace_key", name="uq_workspaces_workspace_key"),
    CheckConstraint(
        "state_generation > 0", name="ck_workspaces_positive_state_generation"
    ),
    CheckConstraint(
        "memory_backend IN ('incumbent','hindsight')",
        name="ck_workspaces_memory_backend",
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
    Column("reviewer_model_key", String(300), nullable=True),
    Column("embedding_model_key", String(300), nullable=True),
    Column("compaction_model_key", String(300), nullable=True),
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
    Column("memory_generation", BigInteger, nullable=False, server_default=text("1")),
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
    CheckConstraint(
        "memory_generation > 0", name="ck_memory_subjects_positive_memory_generation"
    ),
)
Index(
    "ix_memory_subjects_workspace_purpose_updated",
    memory_subjects.c.workspace_id,
    memory_subjects.c.purpose,
    memory_subjects.c.updated_at.desc(),
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
