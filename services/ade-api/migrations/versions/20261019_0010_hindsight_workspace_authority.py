"""Keep fresh workspace identity and Memory authority immutable.

Revision ID: 20261019_0010
Revises: 20261019_0009
"""

from alembic import op


revision = "20261019_0010"
down_revision = "20261019_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE FUNCTION ade.guard_workspace_authority() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF ROW(NEW.id, NEW.workspace_key, NEW.memory_backend)
       IS DISTINCT FROM ROW(OLD.id, OLD.workspace_key, OLD.memory_backend) THEN
        RAISE EXCEPTION 'Workspace identity and Memory authority are immutable'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_workspace_authority BEFORE UPDATE ON ade.workspaces
FOR EACH ROW EXECUTE FUNCTION ade.guard_workspace_authority();
""")


def downgrade() -> None:
    op.execute("""
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM ade.workspaces WHERE memory_backend = 'hindsight') THEN
        RAISE EXCEPTION 'Cannot remove Hindsight workspace authority after fresh workspace creation'
            USING ERRCODE = '23514';
    END IF;
END $$;
DROP TRIGGER guard_workspace_authority ON ade.workspaces;
DROP FUNCTION ade.guard_workspace_authority();
""")
