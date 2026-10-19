"""Add concrete Hindsight delivery without rewriting retained native data.

Revision ID: 20261019_0009
Revises: 20260924_0008
"""

from alembic import op

revision = "20261019_0009"
down_revision = "20260924_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
ALTER TABLE ade.workspaces ADD COLUMN memory_backend VARCHAR(32) NOT NULL DEFAULT 'incumbent';
ALTER TABLE ade.workspaces ADD CONSTRAINT ck_workspaces_memory_backend CHECK (memory_backend IN ('incumbent','hindsight'));
ALTER TABLE ade.agent_definition_versions ADD COLUMN compaction_model_key VARCHAR(300);
ALTER TABLE ade.agent_definition_versions ALTER COLUMN reviewer_model_key DROP NOT NULL;
ALTER TABLE ade.agent_definition_versions ALTER COLUMN embedding_model_key DROP NOT NULL;
ALTER TABLE ade.runs ALTER COLUMN accepted_memory_generation DROP NOT NULL;
ALTER TABLE ade.runs ADD COLUMN paused_at TIMESTAMPTZ;
DROP INDEX ade.uq_runs_active_conversation;
CREATE UNIQUE INDEX uq_runs_active_conversation ON ade.runs(conversation_id) WHERE status IN ('pending','running','paused');
ALTER TABLE ade.messages ADD CONSTRAINT uq_messages_id_workspace UNIQUE(id,workspace_id);
ALTER TABLE ade.messages ADD CONSTRAINT uq_messages_run_role UNIQUE(run_id,role);
""")
    op.execute(r"""
CREATE TABLE ade.memory_relationships (
	bank_id VARCHAR(128) NOT NULL, 
	workspace_id UUID NOT NULL, 
	subject_id UUID NOT NULL, 
	character_root_id UUID NOT NULL, 
	configuration_sha256 VARCHAR(64) NOT NULL, 
	configuration JSONB NOT NULL, 
	state VARCHAR(32) DEFAULT 'new' NOT NULL, 
	next_sequence BIGINT DEFAULT 1 NOT NULL, 
	initialization_token UUID, 
	initialization_expires_at TIMESTAMP WITH TIME ZONE, 
	initialized_at TIMESTAMP WITH TIME ZONE, 
	last_error_code VARCHAR(128), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_memory_relationships PRIMARY KEY (bank_id), 
	CONSTRAINT uq_memory_relationships_scope UNIQUE (workspace_id, subject_id, character_root_id), 
	CONSTRAINT uq_memory_relationships_bank_workspace UNIQUE (bank_id, workspace_id), 
	CONSTRAINT uq_memory_relationships_bank_configuration UNIQUE (bank_id, configuration_sha256), 
	CONSTRAINT fk_memory_relationships_subject_workspace FOREIGN KEY(subject_id, workspace_id) REFERENCES ade.memory_subjects (id, workspace_id), 
	CONSTRAINT fk_memory_relationships_character_workspace FOREIGN KEY(character_root_id, workspace_id) REFERENCES ade.agent_definitions (id, workspace_id), 
	CONSTRAINT ck_memory_relationships_state CHECK (state IN ('new','initializing','ready','failed','missing')), 
	CONSTRAINT ck_memory_relationships_sequence CHECK (next_sequence > 0), 
	CONSTRAINT ck_memory_relationships_configuration_hash CHECK (length(configuration_sha256) = 64), 
	CONSTRAINT ck_memory_relationships_initialization_lease CHECK ((state = 'initializing') = (initialization_token IS NOT NULL AND initialization_expires_at IS NOT NULL)), 
	CONSTRAINT ck_memory_relationships_lease_pair CHECK ((initialization_token IS NULL) = (initialization_expires_at IS NULL)), 
	CONSTRAINT ck_memory_relationships_ready CHECK (state <> 'ready' OR initialized_at IS NOT NULL)
)
""")
    op.execute(r"""
CREATE TABLE ade.memory_deliveries (
	operation_id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	bank_id VARCHAR(128) NOT NULL, 
	configuration_sha256 VARCHAR(64) NOT NULL, 
	message_id UUID NOT NULL, 
	relationship_sequence BIGINT NOT NULL, 
	document_id VARCHAR(200) NOT NULL, 
	payload BYTEA NOT NULL, 
	payload_sha256 VARCHAR(64) NOT NULL, 
	status VARCHAR(32) DEFAULT 'queued' NOT NULL, 
	attempt_count INTEGER DEFAULT 0 NOT NULL, 
    check_count INTEGER DEFAULT 0 NOT NULL,
    retry_requested BOOLEAN DEFAULT false NOT NULL,
	consecutive_errors INTEGER DEFAULT 0 NOT NULL, 
	last_error_code VARCHAR(128), 
	native_status VARCHAR(32), 
	native_progress JSONB DEFAULT '{}'::jsonb NOT NULL, 
	accepted_at TIMESTAMP WITH TIME ZONE, 
	accepted_via VARCHAR(32), 
	retained_at TIMESTAMP WITH TIME ZONE, 
	first_dispatch_at TIMESTAMP WITH TIME ZONE, 
	last_checked_at TIMESTAMP WITH TIME ZONE, 
	lease_token UUID, 
	lease_expires_at TIMESTAMP WITH TIME ZONE, 
	next_attempt_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_memory_deliveries PRIMARY KEY (operation_id), 
	CONSTRAINT uq_memory_deliveries_message UNIQUE (message_id), 
	CONSTRAINT uq_memory_deliveries_order UNIQUE (bank_id, relationship_sequence), 
	CONSTRAINT uq_memory_deliveries_document UNIQUE (bank_id, document_id), 
	CONSTRAINT fk_memory_deliveries_bank_workspace FOREIGN KEY(bank_id, workspace_id) REFERENCES ade.memory_relationships (bank_id, workspace_id), 
	CONSTRAINT fk_memory_deliveries_bank_configuration FOREIGN KEY(bank_id, configuration_sha256) REFERENCES ade.memory_relationships (bank_id, configuration_sha256), 
	CONSTRAINT fk_memory_deliveries_message_workspace FOREIGN KEY(message_id, workspace_id) REFERENCES ade.messages (id, workspace_id), 
	CONSTRAINT ck_memory_deliveries_status CHECK (status IN ('queued','submitting','processing','retained','failed','uncertain')), 
	CONSTRAINT ck_memory_deliveries_sequence CHECK (relationship_sequence > 0), 
	CONSTRAINT ck_memory_deliveries_attempts CHECK (attempt_count >= 0 AND check_count >= 0 AND consecutive_errors >= 0),
	CONSTRAINT ck_memory_deliveries_payload_hash CHECK (payload_sha256 = encode(sha256(payload),'hex')), 
	CONSTRAINT ck_memory_deliveries_lease CHECK ((lease_token IS NULL) = (lease_expires_at IS NULL)), 
	CONSTRAINT ck_memory_deliveries_acknowledgement CHECK ((accepted_at IS NULL) = (accepted_via IS NULL) AND (accepted_via IS NULL OR accepted_via IN ('response','reconciliation'))), 
	CONSTRAINT ck_memory_deliveries_retained CHECK (status <> 'retained' OR (retained_at IS NOT NULL AND accepted_at IS NOT NULL)), 
	CONSTRAINT ck_memory_deliveries_terminal_lease CHECK (status NOT IN ('retained','failed','uncertain') OR lease_token IS NULL)
)
""")
    op.execute(r"""
CREATE INDEX ix_memory_deliveries_dispatch ON ade.memory_deliveries (workspace_id, next_attempt_at, relationship_sequence)
""")
    op.execute(r"""
CREATE TABLE ade.run_retry_requests (
	run_id UUID NOT NULL, 
	idempotency_key VARCHAR(200) NOT NULL, 
	request_sha256 VARCHAR(64) NOT NULL, 
	expected_attempt_count INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_run_retry_requests PRIMARY KEY (run_id, idempotency_key), 
	CONSTRAINT uq_run_retry_requests_attempt UNIQUE (run_id, expected_attempt_count), 
	CONSTRAINT fk_run_retry_requests_run FOREIGN KEY(run_id) REFERENCES ade.runs (id), 
	CONSTRAINT ck_run_retry_requests_attempt CHECK (expected_attempt_count > 0)
)
""")
    op.execute(r"""
CREATE FUNCTION ade.guard_hindsight_delivery() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE original RECORD; relationship RECORD; envelope JSONB; item JSONB; source JSONB; context JSONB;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF ROW(NEW.operation_id,NEW.workspace_id,NEW.bank_id,NEW.configuration_sha256,
               NEW.message_id,NEW.relationship_sequence,NEW.document_id,NEW.payload,NEW.payload_sha256,NEW.created_at)
           IS DISTINCT FROM
           ROW(OLD.operation_id,OLD.workspace_id,OLD.bank_id,OLD.configuration_sha256,
               OLD.message_id,OLD.relationship_sequence,OLD.document_id,OLD.payload,OLD.payload_sha256,OLD.created_at)
        THEN RAISE EXCEPTION 'immutable Hindsight delivery changed' USING ERRCODE='23514'; END IF;
        RETURN NEW;
    END IF;
    SELECT m.id,m.content,m.content_sha256,m.role,m.sequence,m.created_at,m.conversation_id,
           c.memory_subject_id,c.agent_definition_version_id,v.agent_definition_id
      INTO original
      FROM ade.messages m JOIN ade.conversations c ON c.id=m.conversation_id
      JOIN ade.agent_definition_versions v ON v.id=c.agent_definition_version_id
     WHERE m.id=NEW.message_id AND m.workspace_id=NEW.workspace_id;
    SELECT * INTO relationship FROM ade.memory_relationships
     WHERE bank_id=NEW.bank_id AND workspace_id=NEW.workspace_id;
    IF original.id IS NULL OR relationship.bank_id IS NULL
       OR original.memory_subject_id<>relationship.subject_id
       OR original.agent_definition_id<>relationship.character_root_id
    THEN RAISE EXCEPTION 'Hindsight delivery source ownership mismatch' USING ERRCODE='23514'; END IF;
    envelope := convert_from(NEW.payload,'UTF8')::jsonb;
    item := envelope->'items'->0;
    source := (item->>'content')::jsonb;
    context := (item->>'context')::jsonb;
    IF envelope->>'operation_id' IS DISTINCT FROM NEW.operation_id::text
       OR envelope->'async' IS DISTINCT FROM 'true'::jsonb
       OR jsonb_array_length(envelope->'items')<>1
       OR item->>'document_id' IS DISTINCT FROM NEW.document_id
       OR NEW.document_id IS DISTINCT FROM 'ade-message-'||NEW.message_id::text
       OR original.role NOT IN ('user','assistant')
       OR original.content_sha256<>encode(sha256(convert_to(original.content,'UTF8')),'hex')
       OR source->>'message_id' IS DISTINCT FROM NEW.message_id::text
       OR source->>'conversation_id' IS DISTINCT FROM original.conversation_id::text
       OR source->>'definition_version_id' IS DISTINCT FROM original.agent_definition_version_id::text
       OR source->>'speaker' IS DISTINCT FROM original.role
       OR source->>'content' IS DISTINCT FROM original.content
       OR (source->>'sequence')::integer IS DISTINCT FROM original.sequence
       OR (source->>'occurred_at')::timestamptz IS DISTINCT FROM original.created_at
       OR (item->>'timestamp')::timestamptz IS DISTINCT FROM original.created_at
       OR source->>'status' IS DISTINCT FROM (CASE WHEN original.role='user' THEN 'accepted' ELSE 'committed' END)
       OR item->'metadata'->>'message_id' IS DISTINCT FROM NEW.message_id::text
       OR item->'metadata'->>'conversation_id' IS DISTINCT FROM original.conversation_id::text
       OR item->'metadata'->>'definition_version_id' IS DISTINCT FROM original.agent_definition_version_id::text
       OR item->'metadata'->>'speaker' IS DISTINCT FROM original.role
       OR item->'metadata'->>'delivery_contract' IS DISTINCT FROM 'ade-hindsight-message-v1'
       OR item->'metadata'->>'workspace_id' IS DISTINCT FROM NEW.workspace_id::text
       OR item->'metadata'->>'subject_id' IS DISTINCT FROM relationship.subject_id::text
       OR item->'metadata'->>'character_root_id' IS DISTINCT FROM relationship.character_root_id::text
       OR context->'relationship'->>'workspace_id' IS DISTINCT FROM NEW.workspace_id::text
       OR context->'relationship'->>'subject_id' IS DISTINCT FROM relationship.subject_id::text
       OR context->'relationship'->>'character_root_id' IS DISTINCT FROM relationship.character_root_id::text
       OR context->>'delivery_contract' IS DISTINCT FROM 'ade-hindsight-message-v1'
    THEN RAISE EXCEPTION 'Hindsight payload does not match immutable ADE source' USING ERRCODE='23514'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_hindsight_delivery BEFORE INSERT OR UPDATE ON ade.memory_deliveries
FOR EACH ROW EXECUTE FUNCTION ade.guard_hindsight_delivery();

CREATE FUNCTION ade.guard_hindsight_relationship() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NOT EXISTS (SELECT 1 FROM ade.workspaces WHERE id=NEW.workspace_id AND memory_backend='hindsight')
        THEN RAISE EXCEPTION 'Hindsight requires an explicitly fresh workspace' USING ERRCODE='23514'; END IF;
        RETURN NEW;
    END IF;
    IF ROW(NEW.bank_id,NEW.workspace_id,NEW.subject_id,NEW.character_root_id,
           NEW.configuration_sha256,NEW.configuration,NEW.created_at)
       IS DISTINCT FROM ROW(OLD.bank_id,OLD.workspace_id,OLD.subject_id,OLD.character_root_id,
           OLD.configuration_sha256,OLD.configuration,OLD.created_at)
    THEN RAISE EXCEPTION 'immutable Hindsight relationship changed' USING ERRCODE='23514'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_hindsight_relationship BEFORE INSERT OR UPDATE ON ade.memory_relationships
FOR EACH ROW EXECUTE FUNCTION ade.guard_hindsight_relationship();

CREATE FUNCTION ade.guard_immutable_product_source() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW IS DISTINCT FROM OLD
    THEN RAISE EXCEPTION 'immutable ADE product source changed' USING ERRCODE='23514'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_immutable_message BEFORE UPDATE ON ade.messages
FOR EACH ROW EXECUTE FUNCTION ade.guard_immutable_product_source();
CREATE TRIGGER guard_immutable_definition_version BEFORE UPDATE ON ade.agent_definition_versions
FOR EACH ROW EXECUTE FUNCTION ade.guard_immutable_product_source();

CREATE FUNCTION ade.guard_conversation_binding() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF ROW(NEW.id,NEW.workspace_id,NEW.memory_subject_id,NEW.agent_definition_version_id,NEW.created_at)
       IS DISTINCT FROM ROW(OLD.id,OLD.workspace_id,OLD.memory_subject_id,OLD.agent_definition_version_id,OLD.created_at)
    THEN RAISE EXCEPTION 'immutable ADE conversation binding changed' USING ERRCODE='23514'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_conversation_binding BEFORE UPDATE ON ade.conversations
FOR EACH ROW EXECUTE FUNCTION ade.guard_conversation_binding();
""")


def downgrade() -> None:
    op.execute(r"""
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM ade.workspaces WHERE memory_backend='hindsight')
       OR EXISTS (SELECT 1 FROM ade.memory_relationships)
       OR EXISTS (SELECT 1 FROM ade.memory_deliveries)
       OR EXISTS (SELECT 1 FROM ade.run_retry_requests)
       OR EXISTS (SELECT 1 FROM ade.runs WHERE accepted_memory_generation IS NULL OR status='paused')
       OR EXISTS (SELECT 1 FROM ade.agent_definition_versions WHERE reviewer_model_key IS NULL OR embedding_model_key IS NULL)
    THEN RAISE EXCEPTION 'Hindsight state requires a proven paired recovery point, not native downgrade'; END IF;
END $$;
DROP TRIGGER guard_conversation_binding ON ade.conversations;
DROP FUNCTION ade.guard_conversation_binding();
DROP TRIGGER guard_immutable_definition_version ON ade.agent_definition_versions;
DROP TRIGGER guard_immutable_message ON ade.messages;
DROP FUNCTION ade.guard_immutable_product_source();
DROP TRIGGER guard_hindsight_relationship ON ade.memory_relationships;
DROP FUNCTION ade.guard_hindsight_relationship();
DROP TRIGGER guard_hindsight_delivery ON ade.memory_deliveries;
DROP FUNCTION ade.guard_hindsight_delivery();
DROP TABLE ade.run_retry_requests;
DROP TABLE ade.memory_deliveries;
DROP TABLE ade.memory_relationships;
ALTER TABLE ade.messages DROP CONSTRAINT uq_messages_run_role;
ALTER TABLE ade.messages DROP CONSTRAINT uq_messages_id_workspace;
DROP INDEX ade.uq_runs_active_conversation;
CREATE UNIQUE INDEX uq_runs_active_conversation ON ade.runs(conversation_id) WHERE status IN ('pending','running');
ALTER TABLE ade.runs DROP COLUMN paused_at;
ALTER TABLE ade.runs ALTER COLUMN accepted_memory_generation SET NOT NULL;
ALTER TABLE ade.agent_definition_versions ALTER COLUMN reviewer_model_key SET NOT NULL;
ALTER TABLE ade.agent_definition_versions ALTER COLUMN embedding_model_key SET NOT NULL;
ALTER TABLE ade.agent_definition_versions DROP COLUMN compaction_model_key;
ALTER TABLE ade.workspaces DROP COLUMN memory_backend;
""")
