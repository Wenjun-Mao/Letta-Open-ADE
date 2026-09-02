"""Bind every accepted run to one runtime mode.

Revision ID: 20260902_0006
Revises: 20260902_0005
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op


revision = "20260902_0006"
down_revision = "20260902_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE ade.runs
            ADD COLUMN accepted_runtime_mode VARCHAR(32)
                NOT NULL DEFAULT 'development',
            ADD CONSTRAINT ck_runs_accepted_runtime_mode
                CHECK (accepted_runtime_mode IN ('development', 'release'))
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE ade.runs
            DROP CONSTRAINT ck_runs_accepted_runtime_mode,
            DROP COLUMN accepted_runtime_mode
        """
    )
