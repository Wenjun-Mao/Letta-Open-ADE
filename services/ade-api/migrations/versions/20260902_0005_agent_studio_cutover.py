"""Add the native Agent Studio lifecycle and reset boundary.

Revision ID: 20260902_0005
Revises: 20260830_0004
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op


revision = "20260902_0005"
down_revision = "20260830_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE ade.workspaces
            ADD COLUMN state_generation INTEGER NOT NULL DEFAULT 1,
            ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ADD CONSTRAINT ck_workspaces_positive_state_generation
                CHECK (state_generation > 0)
        """
    )
    op.execute(
        """
        CREATE TABLE ade.agent_definitions (
            id UUID NOT NULL,
            workspace_id UUID NOT NULL,
            definition_key VARCHAR(64) NOT NULL,
            name VARCHAR(120) NOT NULL,
            purpose VARCHAR(32) NOT NULL DEFAULT 'development',
            current_version_id UUID,
            archived_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_agent_definitions PRIMARY KEY (id),
            CONSTRAINT fk_agent_definitions_workspace FOREIGN KEY (workspace_id)
                REFERENCES ade.workspaces (id),
            CONSTRAINT uq_agent_definitions_id_workspace UNIQUE (id, workspace_id),
            CONSTRAINT uq_agent_definitions_workspace_key
                UNIQUE (workspace_id, definition_key),
            CONSTRAINT ck_agent_definitions_purpose
                CHECK (purpose IN ('development', 'agent_studio', 'evaluation', 'preview'))
        )
        """
    )
    op.execute(
        """
        INSERT INTO ade.agent_definitions (
            id, workspace_id, definition_key, name, purpose, created_at, updated_at
        )
        SELECT
            md5(workspace_id::text || ':' || definition_key)::uuid,
            workspace_id,
            definition_key,
            (array_agg(name ORDER BY version DESC))[1],
            CASE
                WHEN definition_key LIKE 'native_preview_%' THEN 'preview'
                ELSE 'development'
            END,
            min(created_at),
            max(created_at)
        FROM ade.agent_definition_versions
        GROUP BY workspace_id, definition_key
        """
    )
    op.execute(
        """
        ALTER TABLE ade.agent_definition_versions
            ADD COLUMN agent_definition_id UUID,
            ADD COLUMN purpose VARCHAR(32) NOT NULL DEFAULT 'development'
        """
    )
    op.execute(
        """
        UPDATE ade.agent_definition_versions AS version
        SET agent_definition_id = definition.id,
            purpose = definition.purpose
        FROM ade.agent_definitions AS definition
        WHERE definition.workspace_id = version.workspace_id
          AND definition.definition_key = version.definition_key
        """
    )
    op.execute(
        """
        ALTER TABLE ade.agent_definition_versions
            ALTER COLUMN agent_definition_id SET NOT NULL,
            ADD CONSTRAINT fk_definition_versions_definition_workspace
                FOREIGN KEY (agent_definition_id, workspace_id)
                REFERENCES ade.agent_definitions (id, workspace_id),
            ADD CONSTRAINT uq_definition_versions_root_version
                UNIQUE (agent_definition_id, version),
            ADD CONSTRAINT ck_definition_versions_purpose
                CHECK (purpose IN ('development', 'agent_studio', 'evaluation', 'preview'))
        """
    )
    op.execute(
        """
        UPDATE ade.agent_definitions AS definition
        SET current_version_id = latest.id
        FROM (
            SELECT DISTINCT ON (agent_definition_id)
                agent_definition_id, id
            FROM ade.agent_definition_versions
            ORDER BY agent_definition_id, version DESC
        ) AS latest
        WHERE latest.agent_definition_id = definition.id
        """
    )
    op.execute(
        """
        ALTER TABLE ade.agent_definitions
            ADD CONSTRAINT fk_agent_definitions_current_version
                FOREIGN KEY (current_version_id)
                REFERENCES ade.agent_definition_versions (id)
        """
    )
    op.execute(
        """
        ALTER TABLE ade.memory_subjects
            ADD COLUMN purpose VARCHAR(32) NOT NULL DEFAULT 'development',
            ADD COLUMN version INTEGER NOT NULL DEFAULT 1,
            ADD COLUMN archived_at TIMESTAMP WITH TIME ZONE,
            ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ADD CONSTRAINT ck_memory_subjects_purpose
                CHECK (purpose IN ('development', 'agent_studio', 'evaluation', 'preview')),
            ADD CONSTRAINT ck_memory_subjects_positive_version CHECK (version > 0)
        """
    )
    op.execute(
        """
        UPDATE ade.memory_subjects
        SET purpose = 'preview'
        WHERE external_key LIKE 'native-preview:%'
        """
    )
    op.execute(
        """
        ALTER TABLE ade.conversations
            ADD COLUMN title VARCHAR(120) NOT NULL DEFAULT 'Conversation',
            ADD COLUMN purpose VARCHAR(32) NOT NULL DEFAULT 'development',
            ADD CONSTRAINT ck_conversations_purpose
                CHECK (purpose IN ('development', 'agent_studio', 'evaluation', 'preview'))
        """
    )
    op.execute(
        """
        UPDATE ade.conversations AS conversation
        SET purpose = version.purpose
        FROM ade.agent_definition_versions AS version
        WHERE version.id = conversation.agent_definition_version_id
        """
    )
    op.execute(
        """
        CREATE INDEX ix_conversations_workspace_purpose_created
            ON ade.conversations (workspace_id, purpose, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_memory_subjects_workspace_purpose_updated
            ON ade.memory_subjects (workspace_id, purpose, updated_at DESC)
        """
    )
    op.execute(
        """
        CREATE TABLE ade.agent_studio_reset_receipts (
            id UUID NOT NULL,
            workspace_id UUID NOT NULL,
            idempotency_key VARCHAR(200) NOT NULL,
            request_sha256 VARCHAR(64) NOT NULL,
            reset_generation INTEGER NOT NULL,
            deleted_counts JSONB NOT NULL,
            reset_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_agent_studio_reset_receipts PRIMARY KEY (id),
            CONSTRAINT fk_agent_studio_reset_receipts_workspace
                FOREIGN KEY (workspace_id) REFERENCES ade.workspaces (id),
            CONSTRAINT uq_agent_studio_reset_receipts_workspace_key
                UNIQUE (workspace_id, idempotency_key),
            CONSTRAINT ck_agent_studio_reset_receipts_request_sha256
                CHECK (char_length(request_sha256) = 64),
            CONSTRAINT ck_agent_studio_reset_receipts_generation
                CHECK (reset_generation > 1)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE ade.agent_studio_reset_receipts")
    op.execute("DROP INDEX ade.ix_memory_subjects_workspace_purpose_updated")
    op.execute("DROP INDEX ade.ix_conversations_workspace_purpose_created")
    op.execute(
        """
        ALTER TABLE ade.conversations
            DROP CONSTRAINT ck_conversations_purpose,
            DROP COLUMN purpose,
            DROP COLUMN title
        """
    )
    op.execute(
        """
        ALTER TABLE ade.memory_subjects
            DROP CONSTRAINT ck_memory_subjects_positive_version,
            DROP CONSTRAINT ck_memory_subjects_purpose,
            DROP COLUMN updated_at,
            DROP COLUMN archived_at,
            DROP COLUMN version,
            DROP COLUMN purpose
        """
    )
    op.execute(
        """
        ALTER TABLE ade.agent_definitions
            DROP CONSTRAINT fk_agent_definitions_current_version
        """
    )
    op.execute(
        """
        ALTER TABLE ade.agent_definition_versions
            DROP CONSTRAINT ck_definition_versions_purpose,
            DROP CONSTRAINT uq_definition_versions_root_version,
            DROP CONSTRAINT fk_definition_versions_definition_workspace,
            DROP COLUMN purpose,
            DROP COLUMN agent_definition_id
        """
    )
    op.execute("DROP TABLE ade.agent_definitions")
    op.execute(
        """
        ALTER TABLE ade.workspaces
            DROP CONSTRAINT ck_workspaces_positive_state_generation,
            DROP COLUMN updated_at,
            DROP COLUMN state_generation
        """
    )
