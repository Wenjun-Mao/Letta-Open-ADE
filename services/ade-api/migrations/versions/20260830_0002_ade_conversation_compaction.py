"""Add auditable model-generated conversation compaction.

Revision ID: 20260830_0002
Revises: 20260829_0001
Create Date: 2026-08-30
"""

from __future__ import annotations

from alembic import op


revision = "20260830_0002"
down_revision = "20260829_0001"
branch_labels = None
depends_on = None

_LEGACY_SHA256 = "0" * 64


def upgrade() -> None:
    # Existing preview databases have summary rows without generated-model
    # provenance. Mark only those retained rows as legacy before enforcing the
    # complete provenance contract for every newly generated summary.
    op.execute(
        "ALTER TABLE ade.conversation_summaries "
        "ADD COLUMN previous_summary_id UUID"
    )
    op.execute(
        "ALTER TABLE ade.conversation_summaries "
        "ADD COLUMN model_key VARCHAR(300)"
    )
    op.execute(
        "ALTER TABLE ade.conversation_summaries "
        "ADD COLUMN provider_request_id VARCHAR(512)"
    )
    op.execute(
        "ALTER TABLE ade.conversation_summaries "
        "ADD COLUMN prompt_sha256 VARCHAR(64)"
    )
    op.execute(
        "ALTER TABLE ade.conversation_summaries "
        "ADD COLUMN input_sha256 VARCHAR(64)"
    )
    op.execute(
        "UPDATE ade.conversation_summaries "
        f"SET model_key = 'legacy-unattributed', prompt_sha256 = '{_LEGACY_SHA256}', "
        f"input_sha256 = '{_LEGACY_SHA256}' "
        "WHERE model_key IS NULL"
    )
    op.execute(
        "ALTER TABLE ade.conversation_summaries "
        "ALTER COLUMN model_key SET NOT NULL"
    )
    op.execute(
        "ALTER TABLE ade.conversation_summaries "
        "ALTER COLUMN prompt_sha256 SET NOT NULL"
    )
    op.execute(
        "ALTER TABLE ade.conversation_summaries "
        "ALTER COLUMN input_sha256 SET NOT NULL"
    )
    op.execute(
        "ALTER TABLE ade.conversation_summaries "
        "ADD CONSTRAINT fk_conversation_summaries_previous_summary "
        "FOREIGN KEY (previous_summary_id) "
        "REFERENCES ade.conversation_summaries (id)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE ade.conversation_summaries "
        "DROP CONSTRAINT fk_conversation_summaries_previous_summary"
    )
    op.execute(
        "ALTER TABLE ade.conversation_summaries "
        "DROP COLUMN input_sha256, "
        "DROP COLUMN prompt_sha256, "
        "DROP COLUMN provider_request_id, "
        "DROP COLUMN model_key, "
        "DROP COLUMN previous_summary_id"
    )
