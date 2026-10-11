"""Whitelist and SQL contract for canonical PostgreSQL table snapshots."""

from __future__ import annotations

SNAPSHOT_TABLES = (
    "banks", "documents", "chunks", "memory_units", "invalidated_memory_units",
    "observation_history", "entities", "unit_entities",
    "entity_cooccurrences", "memory_links",
)

# PostgreSQL creates these schemas for backend-local temporary objects. Their
# numeric suffixes change between database lifetimes, so they are not durable
# restore state. Keep this predicate narrow: stable system, extension, and
# application schemas remain part of the exact snapshot.
SCHEMA_QUERY = (
    "SELECT jsonb_build_object("
    "'schemas',(SELECT COALESCE(jsonb_agg(jsonb_build_object('name',nspname,'owner',r.rolname) "
    "ORDER BY nspname),'[]'::jsonb) FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner "
    "WHERE n.nspname !~ '^pg_(temp|toast_temp)_[0-9]+$'),"
    "'extensions',(SELECT COALESCE(jsonb_agg(jsonb_build_object('name',extname,'version',extversion) "
    "ORDER BY extname),'[]'::jsonb) FROM pg_extension),"
    "'alembic',(SELECT COALESCE(jsonb_agg(to_jsonb(a) ORDER BY to_jsonb(a)::text),'[]'::jsonb) "
    "FROM public.alembic_version a))::text"
)


def table_query(table: str) -> str:
    """Return ordered JSON rows, with no output row for an empty table."""
    if table not in SNAPSHOT_TABLES:
        raise RuntimeError("canonical_snapshot_table_not_allowed")
    return (f"SELECT to_jsonb(t)::text FROM public.{table} AS t "
            "ORDER BY to_jsonb(t)::text")
