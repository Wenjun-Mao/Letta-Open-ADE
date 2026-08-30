"""Bind Agent Runtime worker health to exact source content.

Revision ID: 20260830_0004
Revises: 20260830_0003
Create Date: 2026-08-30
"""

from __future__ import annotations

from alembic import op


revision = "20260830_0004"
down_revision = "20260830_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE ade.worker_instances
            ADD COLUMN source_fingerprint VARCHAR(64) NOT NULL DEFAULT 'unknown',
            ADD CONSTRAINT ck_worker_instances_source_fingerprint
                CHECK (
                    source_fingerprint = 'unknown'
                    OR char_length(source_fingerprint) = 64
                )
        """
    )
    op.execute(
        """
        ALTER TABLE ade.worker_instances
            ALTER COLUMN source_fingerprint DROP DEFAULT
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE ade.worker_instances
            DROP CONSTRAINT ck_worker_instances_source_fingerprint,
            DROP COLUMN source_fingerprint
        """
    )
