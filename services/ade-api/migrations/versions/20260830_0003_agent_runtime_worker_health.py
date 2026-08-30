"""Add process-level Agent Runtime v3 worker health.

Revision ID: 20260830_0003
Revises: 20260830_0002
Create Date: 2026-08-30
"""

from __future__ import annotations

from alembic import op


revision = "20260830_0003"
down_revision = "20260830_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE ade.worker_instances (
            instance_id UUID NOT NULL,
            worker_id VARCHAR(128) NOT NULL,
            state VARCHAR(16) NOT NULL,
            contract_version VARCHAR(128) NOT NULL,
            compatibility_fingerprint VARCHAR(64) NOT NULL,
            runtime_version VARCHAR(64) NOT NULL,
            source_revision VARCHAR(128) NOT NULL,
            source_dirty BOOLEAN NOT NULL,
            started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            heartbeat_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            stopped_at TIMESTAMP WITH TIME ZONE,
            CONSTRAINT pk_worker_instances PRIMARY KEY (instance_id),
            CONSTRAINT ck_worker_instances_state
                CHECK (state IN ('ready', 'draining', 'stopped')),
            CONSTRAINT ck_worker_instances_fingerprint_length
                CHECK (char_length(compatibility_fingerprint) = 64)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_worker_instances_health
            ON ade.worker_instances (
                compatibility_fingerprint,
                state,
                heartbeat_at
            )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE ade.worker_instances")
