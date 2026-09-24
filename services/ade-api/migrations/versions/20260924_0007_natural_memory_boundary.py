"""Add natural-memory lifecycle, subject generation, and operator causation.

Revision ID: 20260924_0007
Revises: 20260902_0006
Create Date: 2026-09-24

Existing subjects and accepted runs start at generation 1. This is a fence
baseline, not a reconstruction of historical mutation counts. Existing
preference/category records remain schema 1 and are not decomposed.
"""

from __future__ import annotations

from alembic import op


revision = "20260924_0007"
down_revision = "20260902_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE ade.memory_subjects
            ADD COLUMN memory_generation BIGINT NOT NULL DEFAULT 1,
            ADD CONSTRAINT ck_memory_subjects_positive_memory_generation
                CHECK (memory_generation > 0)
        """
    )
    op.execute(
        """
        ALTER TABLE ade.runs
            ADD COLUMN accepted_memory_generation BIGINT NOT NULL DEFAULT 1,
            ADD CONSTRAINT ck_runs_positive_memory_generation
                CHECK (accepted_memory_generation > 0)
        """
    )
    op.execute(
        """
        ALTER TABLE ade.memory_facts
            ADD COLUMN assertion_schema_version INTEGER NOT NULL DEFAULT 1,
            ADD CONSTRAINT ck_memory_facts_assertion_schema_version
                CHECK (assertion_schema_version IN (1, 2)),
            ADD CONSTRAINT ck_memory_facts_lifecycle_status
                CHECK (status IN ('active', 'inactive', 'forgotten'))
        """
    )
    op.execute(
        """
        CREATE TABLE ade.memory_actions (
            id UUID NOT NULL,
            workspace_id UUID NOT NULL,
            subject_id UUID NOT NULL,
            idempotency_key VARCHAR(200) NOT NULL,
            request_sha256 VARCHAR(64) NOT NULL,
            expected_memory_generation BIGINT NOT NULL,
            resulting_memory_generation BIGINT NOT NULL,
            targets JSONB NOT NULL,
            revision_ids JSONB NOT NULL,
            outcome VARCHAR(32) NOT NULL,
            actor_label VARCHAR(200) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_memory_actions PRIMARY KEY (id),
            CONSTRAINT fk_memory_actions_subject_workspace
                FOREIGN KEY (subject_id, workspace_id)
                REFERENCES ade.memory_subjects (id, workspace_id),
            CONSTRAINT uq_memory_actions_subject_key
                UNIQUE (subject_id, idempotency_key),
            CONSTRAINT ck_memory_actions_hash
                CHECK (char_length(request_sha256) = 64),
            CONSTRAINT ck_memory_actions_generations
                CHECK (expected_memory_generation > 0
                    AND resulting_memory_generation > expected_memory_generation),
            CONSTRAINT ck_memory_actions_outcome
                CHECK (outcome IN ('committed'))
        )
        """
    )
    op.execute(
        """
        ALTER TABLE ade.memory_revisions
            ALTER COLUMN run_id DROP NOT NULL,
            ADD COLUMN action_id UUID,
            ADD COLUMN reason VARCHAR(32),
            ADD CONSTRAINT fk_memory_revisions_action
                FOREIGN KEY (action_id) REFERENCES ade.memory_actions (id),
            ADD CONSTRAINT ck_memory_revisions_one_origin
                CHECK ((run_id IS NOT NULL) <> (action_id IS NOT NULL)),
            ADD CONSTRAINT ck_memory_revisions_reason
                CHECK (reason IS NULL OR reason IN
                    ('enrich', 'supersede', 'correct', 'unspecified',
                     'ended', 'invalidated', 'reasserted', 'forgotten'))
        """
    )
    op.execute(
        """
        UPDATE ade.memory_revisions
        SET reason = CASE operation
            WHEN 'correct' THEN 'unspecified'
            WHEN 'forget' THEN 'forgotten'
            ELSE NULL
        END
        """
    )
    op.execute(
        """
        ALTER TABLE ade.memory_revision_sources
            ADD COLUMN authority_role VARCHAR(32) NOT NULL DEFAULT 'user_assertion',
            ADD CONSTRAINT ck_memory_revision_sources_authority_role
                CHECK (authority_role IN
                    ('user_assertion', 'user_endorsement', 'assistant_referent'))
        """
    )


def downgrade() -> None:
    # A downgrade cannot represent action-origin revisions or inactive records.
    # A recovery plan must restore a compatible backup rather than discard them.
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM ade.memory_revisions WHERE action_id IS NOT NULL)
               OR EXISTS (SELECT 1 FROM ade.memory_facts WHERE status = 'inactive')
            THEN RAISE EXCEPTION 'natural-memory data cannot be downgraded';
            END IF;
        END $$
        """
    )
    op.execute(
        """
        ALTER TABLE ade.memory_revision_sources
            DROP CONSTRAINT ck_memory_revision_sources_authority_role,
            DROP COLUMN authority_role
        """
    )
    op.execute(
        """
        ALTER TABLE ade.memory_revisions
            DROP CONSTRAINT ck_memory_revisions_reason,
            DROP CONSTRAINT ck_memory_revisions_one_origin,
            DROP CONSTRAINT fk_memory_revisions_action,
            DROP COLUMN reason,
            DROP COLUMN action_id,
            ALTER COLUMN run_id SET NOT NULL
        """
    )
    op.execute("DROP TABLE ade.memory_actions")
    op.execute(
        """
        ALTER TABLE ade.memory_facts
            DROP CONSTRAINT ck_memory_facts_lifecycle_status,
            DROP CONSTRAINT ck_memory_facts_assertion_schema_version,
            DROP COLUMN assertion_schema_version
        """
    )
    op.execute(
        """
        ALTER TABLE ade.runs
            DROP CONSTRAINT ck_runs_positive_memory_generation,
            DROP COLUMN accepted_memory_generation
        """
    )
    op.execute(
        """
        ALTER TABLE ade.memory_subjects
            DROP CONSTRAINT ck_memory_subjects_positive_memory_generation,
            DROP COLUMN memory_generation
        """
    )
