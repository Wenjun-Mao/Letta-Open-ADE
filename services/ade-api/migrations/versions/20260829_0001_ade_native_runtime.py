"""Create the ADE-native runtime persistence foundation.

Revision ID: 20260829_0001
Revises:
Create Date: 2026-08-29
"""

from __future__ import annotations

from alembic import op


revision = "20260829_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE SCHEMA IF NOT EXISTS ade")
    statements = (
        """
        CREATE TABLE ade.workspaces (
            id UUID NOT NULL,
            workspace_key VARCHAR(120) NOT NULL,
            name VARCHAR(200) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_workspaces PRIMARY KEY (id),
            CONSTRAINT uq_workspaces_workspace_key UNIQUE (workspace_key)
        )
        """,
        """
        CREATE TABLE ade.agent_definition_versions (
            id UUID NOT NULL,
            workspace_id UUID NOT NULL,
            definition_key VARCHAR(64) NOT NULL,
            version INTEGER NOT NULL,
            name VARCHAR(120) NOT NULL,
            model_key VARCHAR(300) NOT NULL,
            reviewer_model_key VARCHAR(300) NOT NULL,
            embedding_model_key VARCHAR(300) NOT NULL,
            prompt_key VARCHAR(128) NOT NULL,
            prompt_sha256 VARCHAR(64) NOT NULL,
            prompt_content TEXT NOT NULL,
            persona_key VARCHAR(128) NOT NULL,
            persona_sha256 VARCHAR(64) NOT NULL,
            persona_content TEXT NOT NULL,
            tool_names JSONB NOT NULL,
            memory_policy_version VARCHAR(128) NOT NULL,
            qualification_state VARCHAR(32) NOT NULL,
            deployment_snapshot JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_agent_definition_versions PRIMARY KEY (id),
            CONSTRAINT fk_definition_versions_workspace FOREIGN KEY (workspace_id)
                REFERENCES ade.workspaces (id),
            CONSTRAINT uq_definition_versions_id_workspace UNIQUE (id, workspace_id),
            CONSTRAINT uq_definition_versions_workspace_key_version
                UNIQUE (workspace_id, definition_key, version),
            CONSTRAINT ck_definition_versions_positive_version CHECK (version > 0)
        )
        """,
        """
        CREATE TABLE ade.memory_subjects (
            id UUID NOT NULL,
            workspace_id UUID NOT NULL,
            external_key VARCHAR(200) NOT NULL,
            display_name VARCHAR(200) NOT NULL DEFAULT '',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_memory_subjects PRIMARY KEY (id),
            CONSTRAINT fk_memory_subjects_workspace FOREIGN KEY (workspace_id)
                REFERENCES ade.workspaces (id),
            CONSTRAINT uq_memory_subjects_id_workspace UNIQUE (id, workspace_id),
            CONSTRAINT uq_memory_subjects_workspace_external_key UNIQUE (workspace_id, external_key)
        )
        """,
        """
        CREATE TABLE ade.memory_entities (
            id UUID NOT NULL,
            workspace_id UUID NOT NULL,
            subject_id UUID NOT NULL,
            kind VARCHAR(64) NOT NULL,
            label VARCHAR(200) NOT NULL DEFAULT '',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_memory_entities PRIMARY KEY (id),
            CONSTRAINT fk_memory_entities_subject_workspace
                FOREIGN KEY (subject_id, workspace_id)
                REFERENCES ade.memory_subjects (id, workspace_id),
            CONSTRAINT uq_memory_entities_id_workspace UNIQUE (id, workspace_id)
        )
        """,
        """
        CREATE TABLE ade.conversations (
            id UUID NOT NULL,
            workspace_id UUID NOT NULL,
            agent_definition_version_id UUID NOT NULL,
            memory_subject_id UUID NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            archived_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_conversations PRIMARY KEY (id),
            CONSTRAINT fk_conversations_definition_workspace
                FOREIGN KEY (agent_definition_version_id, workspace_id)
                REFERENCES ade.agent_definition_versions (id, workspace_id),
            CONSTRAINT fk_conversations_subject_workspace
                FOREIGN KEY (memory_subject_id, workspace_id)
                REFERENCES ade.memory_subjects (id, workspace_id),
            CONSTRAINT uq_conversations_id_workspace UNIQUE (id, workspace_id),
            CONSTRAINT ck_conversations_positive_version CHECK (version > 0)
        )
        """,
        """
        CREATE TABLE ade.runs (
            id UUID NOT NULL,
            workspace_id UUID NOT NULL,
            conversation_id UUID NOT NULL,
            idempotency_key VARCHAR(200) NOT NULL,
            request_hash VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL,
            qualification_state VARCHAR(32) NOT NULL,
            timeout_seconds NUMERIC(8, 3) NOT NULL,
            retry_count INTEGER NOT NULL,
            accepted_conversation_version INTEGER NOT NULL,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            cancellation_requested_at TIMESTAMP WITH TIME ZONE,
            error_code VARCHAR(128),
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP WITH TIME ZONE,
            finished_at TIMESTAMP WITH TIME ZONE,
            CONSTRAINT pk_runs PRIMARY KEY (id),
            CONSTRAINT fk_runs_conversation_workspace
                FOREIGN KEY (conversation_id, workspace_id)
                REFERENCES ade.conversations (id, workspace_id),
            CONSTRAINT uq_runs_conversation_idempotency UNIQUE (conversation_id, idempotency_key),
            CONSTRAINT ck_runs_nonnegative_attempt_count CHECK (attempt_count >= 0),
            CONSTRAINT ck_runs_retry_count CHECK (retry_count BETWEEN 0 AND 5),
            CONSTRAINT ck_runs_positive_timeout CHECK (timeout_seconds > 0),
            CONSTRAINT ck_runs_positive_conversation_version
                CHECK (accepted_conversation_version > 0)
        )
        """,
        """
        CREATE TABLE ade.messages (
            id UUID NOT NULL,
            workspace_id UUID NOT NULL,
            conversation_id UUID NOT NULL,
            sequence INTEGER NOT NULL,
            role VARCHAR(32) NOT NULL,
            content TEXT NOT NULL,
            content_sha256 VARCHAR(64) NOT NULL,
            run_id UUID,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_messages PRIMARY KEY (id),
            CONSTRAINT fk_messages_conversation_workspace
                FOREIGN KEY (conversation_id, workspace_id)
                REFERENCES ade.conversations (id, workspace_id),
            CONSTRAINT fk_messages_run FOREIGN KEY (run_id) REFERENCES ade.runs (id),
            CONSTRAINT uq_messages_conversation_sequence UNIQUE (conversation_id, sequence),
            CONSTRAINT ck_messages_positive_sequence CHECK (sequence > 0)
        )
        """,
        """
        CREATE TABLE ade.run_attempts (
            id UUID NOT NULL,
            run_id UUID NOT NULL,
            attempt_number INTEGER NOT NULL,
            status VARCHAR(32) NOT NULL,
            timeout_seconds NUMERIC(8, 3) NOT NULL,
            provider_outcome JSONB NOT NULL DEFAULT '{}'::jsonb,
            started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP WITH TIME ZONE,
            CONSTRAINT pk_run_attempts PRIMARY KEY (id),
            CONSTRAINT fk_run_attempts_run FOREIGN KEY (run_id) REFERENCES ade.runs (id),
            CONSTRAINT uq_run_attempts_run_number UNIQUE (run_id, attempt_number),
            CONSTRAINT ck_run_attempts_positive_number CHECK (attempt_number > 0),
            CONSTRAINT ck_run_attempts_positive_timeout CHECK (timeout_seconds > 0)
        )
        """,
        """
        CREATE TABLE ade.run_events (
            id UUID NOT NULL,
            run_id UUID NOT NULL,
            sequence INTEGER NOT NULL,
            schema_version INTEGER NOT NULL,
            event_type VARCHAR(128) NOT NULL,
            attempt INTEGER,
            correlation_id VARCHAR(128) NOT NULL,
            causation_id VARCHAR(128),
            visibility VARCHAR(32) NOT NULL,
            payload JSONB NOT NULL,
            occurred_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_run_events PRIMARY KEY (id),
            CONSTRAINT fk_run_events_run FOREIGN KEY (run_id) REFERENCES ade.runs (id),
            CONSTRAINT uq_run_events_run_sequence UNIQUE (run_id, sequence),
            CONSTRAINT ck_run_events_positive_sequence CHECK (sequence > 0),
            CONSTRAINT ck_run_events_positive_schema_version CHECK (schema_version > 0)
        )
        """,
        """
        CREATE TABLE ade.outbox (
            id UUID NOT NULL,
            run_id UUID NOT NULL,
            run_event_id UUID NOT NULL,
            topic VARCHAR(128) NOT NULL,
            payload JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            published_at TIMESTAMP WITH TIME ZONE,
            CONSTRAINT pk_outbox PRIMARY KEY (id),
            CONSTRAINT fk_outbox_run FOREIGN KEY (run_id) REFERENCES ade.runs (id),
            CONSTRAINT fk_outbox_run_event FOREIGN KEY (run_event_id) REFERENCES ade.run_events (id),
            CONSTRAINT uq_outbox_run_event UNIQUE (run_event_id)
        )
        """,
        """
        CREATE TABLE ade.memory_facts (
            id UUID NOT NULL,
            workspace_id UUID NOT NULL,
            subject_id UUID NOT NULL,
            entity_id UUID NOT NULL,
            normalized_key VARCHAR(300) NOT NULL,
            fact_type VARCHAR(128) NOT NULL,
            qualifier VARCHAR(200),
            value JSONB,
            status VARCHAR(32) NOT NULL,
            version INTEGER NOT NULL,
            current_revision_id UUID,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_memory_facts PRIMARY KEY (id),
            CONSTRAINT fk_memory_facts_subject_workspace
                FOREIGN KEY (subject_id, workspace_id)
                REFERENCES ade.memory_subjects (id, workspace_id),
            CONSTRAINT fk_memory_facts_entity_workspace
                FOREIGN KEY (entity_id, workspace_id)
                REFERENCES ade.memory_entities (id, workspace_id),
            CONSTRAINT uq_memory_facts_id_workspace UNIQUE (id, workspace_id),
            CONSTRAINT ck_memory_facts_positive_version CHECK (version > 0)
        )
        """,
        """
        CREATE TABLE ade.memory_revisions (
            id UUID NOT NULL,
            fact_id UUID NOT NULL,
            workspace_id UUID NOT NULL,
            subject_id UUID NOT NULL,
            operation VARCHAR(32) NOT NULL,
            fact_version INTEGER NOT NULL,
            value JSONB,
            run_id UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_memory_revisions PRIMARY KEY (id),
            CONSTRAINT fk_memory_revisions_fact_workspace
                FOREIGN KEY (fact_id, workspace_id)
                REFERENCES ade.memory_facts (id, workspace_id),
            CONSTRAINT fk_memory_revisions_subject_workspace
                FOREIGN KEY (subject_id, workspace_id)
                REFERENCES ade.memory_subjects (id, workspace_id),
            CONSTRAINT fk_memory_revisions_run FOREIGN KEY (run_id) REFERENCES ade.runs (id),
            CONSTRAINT uq_memory_revisions_fact_version UNIQUE (fact_id, fact_version),
            CONSTRAINT ck_memory_revisions_positive_version CHECK (fact_version > 0)
        )
        """,
        """
        ALTER TABLE ade.memory_facts
            ADD CONSTRAINT fk_memory_facts_current_revision
            FOREIGN KEY (current_revision_id) REFERENCES ade.memory_revisions (id)
        """,
        """
        CREATE TABLE ade.memory_revision_predecessors (
            revision_id UUID NOT NULL,
            predecessor_revision_id UUID NOT NULL,
            CONSTRAINT pk_memory_revision_predecessors PRIMARY KEY (revision_id, predecessor_revision_id),
            CONSTRAINT fk_revision_predecessors_revision
                FOREIGN KEY (revision_id) REFERENCES ade.memory_revisions (id),
            CONSTRAINT fk_revision_predecessors_predecessor
                FOREIGN KEY (predecessor_revision_id) REFERENCES ade.memory_revisions (id)
        )
        """,
        """
        CREATE TABLE ade.memory_revision_sources (
            id UUID NOT NULL,
            revision_id UUID NOT NULL,
            message_id UUID NOT NULL,
            start_char INTEGER NOT NULL,
            end_char INTEGER NOT NULL,
            quote TEXT NOT NULL,
            message_sha256 VARCHAR(64) NOT NULL,
            CONSTRAINT pk_memory_revision_sources PRIMARY KEY (id),
            CONSTRAINT fk_revision_sources_revision
                FOREIGN KEY (revision_id) REFERENCES ade.memory_revisions (id),
            CONSTRAINT fk_revision_sources_message FOREIGN KEY (message_id) REFERENCES ade.messages (id),
            CONSTRAINT uq_revision_sources_span UNIQUE (revision_id, message_id, start_char, end_char),
            CONSTRAINT ck_revision_sources_nonnegative_start CHECK (start_char >= 0),
            CONSTRAINT ck_revision_sources_positive_span CHECK (end_char > start_char)
        )
        """,
        """
        CREATE TABLE ade.memory_embeddings (
            id UUID NOT NULL,
            workspace_id UUID NOT NULL,
            subject_id UUID NOT NULL,
            fact_id UUID NOT NULL,
            revision_id UUID NOT NULL,
            model_fingerprint VARCHAR(512) NOT NULL,
            dimensions INTEGER NOT NULL,
            normalized BOOLEAN NOT NULL,
            retrieval_policy_version VARCHAR(128) NOT NULL,
            embedding vector NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_memory_embeddings PRIMARY KEY (id),
            CONSTRAINT fk_memory_embeddings_subject_workspace
                FOREIGN KEY (subject_id, workspace_id)
                REFERENCES ade.memory_subjects (id, workspace_id),
            CONSTRAINT fk_memory_embeddings_fact_workspace
                FOREIGN KEY (fact_id, workspace_id)
                REFERENCES ade.memory_facts (id, workspace_id),
            CONSTRAINT fk_memory_embeddings_revision
                FOREIGN KEY (revision_id) REFERENCES ade.memory_revisions (id),
            CONSTRAINT uq_memory_embeddings_revision_model_policy
                UNIQUE (fact_id, revision_id, model_fingerprint, retrieval_policy_version),
            CONSTRAINT ck_memory_embeddings_positive_dimensions CHECK (dimensions > 0)
        )
        """,
        """
        CREATE TABLE ade.conversation_summaries (
            id UUID NOT NULL,
            conversation_id UUID NOT NULL,
            version INTEGER NOT NULL,
            through_sequence INTEGER NOT NULL,
            content TEXT NOT NULL,
            run_id UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_conversation_summaries PRIMARY KEY (id),
            CONSTRAINT fk_conversation_summaries_conversation
                FOREIGN KEY (conversation_id) REFERENCES ade.conversations (id),
            CONSTRAINT fk_conversation_summaries_run FOREIGN KEY (run_id) REFERENCES ade.runs (id),
            CONSTRAINT uq_conversation_summaries_conversation_version UNIQUE (conversation_id, version),
            CONSTRAINT ck_conversation_summaries_positive_version CHECK (version > 0),
            CONSTRAINT ck_conversation_summaries_positive_through_sequence CHECK (through_sequence > 0)
        )
        """,
        """
        CREATE TABLE ade.summary_sources (
            summary_id UUID NOT NULL,
            message_id UUID NOT NULL,
            CONSTRAINT pk_summary_sources PRIMARY KEY (summary_id, message_id),
            CONSTRAINT fk_summary_sources_summary
                FOREIGN KEY (summary_id) REFERENCES ade.conversation_summaries (id),
            CONSTRAINT fk_summary_sources_message FOREIGN KEY (message_id) REFERENCES ade.messages (id)
        )
        """,
        """
        CREATE TABLE ade.conversation_leases (
            id UUID NOT NULL,
            conversation_id UUID NOT NULL,
            run_id UUID NOT NULL,
            lease_token UUID NOT NULL,
            holder_id VARCHAR(128) NOT NULL,
            acquired_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            heartbeat_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            released_at TIMESTAMP WITH TIME ZONE,
            CONSTRAINT pk_conversation_leases PRIMARY KEY (id),
            CONSTRAINT fk_conversation_leases_conversation
                FOREIGN KEY (conversation_id) REFERENCES ade.conversations (id),
            CONSTRAINT fk_conversation_leases_run FOREIGN KEY (run_id) REFERENCES ade.runs (id),
            CONSTRAINT uq_conversation_leases_token UNIQUE (lease_token)
        )
        """,
        """
        CREATE UNIQUE INDEX uq_runs_active_conversation
            ON ade.runs (conversation_id) WHERE status IN ('pending', 'running')
        """,
        """
        CREATE UNIQUE INDEX uq_memory_facts_active_subject_key
            ON ade.memory_facts (subject_id, normalized_key) WHERE status = 'active'
        """,
        """
        CREATE UNIQUE INDEX uq_conversation_leases_active_conversation
            ON ade.conversation_leases (conversation_id) WHERE released_at IS NULL
        """,
    )
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    # pgvector may serve other ADE schemas, so this migration never drops the extension.
    op.execute("DROP SCHEMA ade CASCADE")
