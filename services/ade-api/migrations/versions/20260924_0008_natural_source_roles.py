"""Extend natural-memory source roles without relabeling historical evidence.

Revision ID: 20260924_0008
Revises: 20260924_0007
Create Date: 2026-09-24
"""

from __future__ import annotations

from alembic import op

revision = "20260924_0008"
down_revision = "20260924_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE ade.memory_revision_sources
            DROP CONSTRAINT ck_memory_revision_sources_authority_role,
            ADD CONSTRAINT ck_memory_revision_sources_authority_role
                CHECK (authority_role IN
                    ('user_assertion', 'user_endorsement', 'assistant_referent',
                     'user_resolution', 'user_antecedent'))
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM ade.memory_revision_sources
                WHERE authority_role IN ('user_resolution', 'user_antecedent')
            ) THEN RAISE EXCEPTION 'new natural source roles cannot be downgraded';
            END IF;
        END $$
        """
    )
    op.execute(
        """
        ALTER TABLE ade.memory_revision_sources
            DROP CONSTRAINT ck_memory_revision_sources_authority_role,
            ADD CONSTRAINT ck_memory_revision_sources_authority_role
                CHECK (authority_role IN
                    ('user_assertion', 'user_endorsement', 'assistant_referent'))
        """
    )
